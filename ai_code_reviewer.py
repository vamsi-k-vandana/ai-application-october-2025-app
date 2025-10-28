#!/usr/bin/env python3
"""
AI Code Reviewer - Automated code review using OpenAI GPT models
Analyzes PR changes and posts review comments directly to GitHub
"""

import os
import sys
import json
from typing import List, Dict, Optional
import requests
from openai import OpenAI


class GitHubPRReviewer:
    def __init__(
        self,
        github_token: str,
        openai_api_key: str,
        model: str = "gpt-4o-mini",
        repository: Optional[str] = None,
        pr_number: Optional[int] = None,
    ):
        self.github_token = github_token
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.model = model
        self.repository = repository or os.getenv("GITHUB_REPOSITORY")
        self.pr_number = pr_number or self._get_pr_number()
        self.api_base = "https://api.github.com"

        if not self.repository:
            raise ValueError("Repository not specified and GITHUB_REPOSITORY env var not set")
        if not self.pr_number:
            raise ValueError("PR number not specified and could not be determined from environment")

    def _get_pr_number(self) -> Optional[int]:
        """Extract PR number from GITHUB_REF environment variable"""
        github_ref = os.getenv("GITHUB_REF", "")
        # Format: refs/pull/:prNumber/merge
        if "/pull/" in github_ref:
            try:
                return int(github_ref.split("/")[2])
            except (IndexError, ValueError):
                pass
        return None

    def _make_github_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict:
        """Make authenticated request to GitHub API"""
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        url = f"{self.api_base}{endpoint}"

        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json() if response.content else {}

    def get_pr_files(self) -> List[Dict]:
        """Get list of changed files in the PR"""
        endpoint = f"/repos/{self.repository}/pulls/{self.pr_number}/files"
        return self._make_github_request("GET", endpoint)

    def get_file_diff(self, file_info: Dict) -> str:
        """Extract the patch/diff for a file"""
        return file_info.get("patch", "")

    def review_code_with_ai(self, filename: str, diff: str, file_content: Optional[str] = None) -> Optional[str]:
        """Send code to OpenAI for review"""
        if not diff.strip():
            return None

        prompt = f"""You are an expert code reviewer. Review the following code changes and provide constructive feedback.

File: {filename}
Diff:
```
{diff}
```

Please provide:
1. Any bugs or potential issues
2. Code quality improvements
3. Security concerns
4. Best practice suggestions

Be concise and actionable. If the code looks good, say so briefly. Focus on meaningful improvements."""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert code reviewer providing constructive feedback on code changes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error calling OpenAI API: {e}", file=sys.stderr)
            return None

    def post_review_comment(self, body: str) -> None:
        """Post a review comment on the PR"""
        endpoint = f"/repos/{self.repository}/issues/{self.pr_number}/comments"
        data = {"body": body}
        self._make_github_request("POST", endpoint, data)

    def post_review(self, comments: List[Dict], review_body: str) -> None:
        """Post a complete review with inline comments"""
        endpoint = f"/repos/{self.repository}/pulls/{self.pr_number}/reviews"
        data = {
            "body": review_body,
            "event": "COMMENT",
            "comments": comments
        }
        self._make_github_request("POST", endpoint, data)

    def should_review_file(self, filename: str, exclude_patterns: List[str]) -> bool:
        """Check if file should be reviewed based on exclude patterns"""
        for pattern in exclude_patterns:
            # Simple glob pattern matching
            if pattern.startswith("**/"):
                # Match anywhere in path
                if filename.endswith(pattern[3:]) or pattern[3:] in filename:
                    return False
            elif pattern.startswith("*."):
                # Match extension
                if filename.endswith(pattern[1:]):
                    return False
            elif pattern in filename:
                return False
        return True

    def run_review(self, exclude_patterns: Optional[List[str]] = None) -> None:
        """Main review process"""
        exclude_patterns = exclude_patterns or []

        print(f"Starting AI code review for PR #{self.pr_number} in {self.repository}")

        # Get changed files
        files = self.get_pr_files()
        print(f"Found {len(files)} changed files")

        reviewed_files = []
        review_summary = []

        for file_info in files:
            filename = file_info["filename"]

            # Check if file should be reviewed
            if not self.should_review_file(filename, exclude_patterns):
                print(f"Skipping {filename} (excluded)")
                continue

            # Skip deleted files
            if file_info["status"] == "removed":
                print(f"Skipping {filename} (deleted)")
                continue

            # Get diff
            diff = self.get_file_diff(file_info)
            if not diff:
                print(f"Skipping {filename} (no diff)")
                continue

            print(f"Reviewing {filename}...")

            # Get AI review
            review = self.review_code_with_ai(filename, diff)

            if review:
                reviewed_files.append(filename)
                review_summary.append(f"### {filename}\n\n{review}")

        # Post summary comment
        if review_summary:
            summary = "## AI Code Review\n\n" + "\n\n---\n\n".join(review_summary)
            summary += f"\n\n---\n*Reviewed by {self.model}*"
            self.post_review_comment(summary)
            print(f"Review posted successfully for {len(reviewed_files)} files")
        else:
            print("No files to review")


def main():
    """Main entry point"""
    # Get configuration from environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_API_MODEL", "gpt-4o-mini")
    exclude = os.getenv("EXCLUDE", "")

    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)

    if not openai_api_key:
        print("Error: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Parse exclude patterns
    exclude_patterns = [p.strip() for p in exclude.split(",") if p.strip()]

    try:
        reviewer = GitHubPRReviewer(
            github_token=github_token,
            openai_api_key=openai_api_key,
            model=model,
        )
        reviewer.run_review(exclude_patterns=exclude_patterns)
        print("Code review completed successfully")
    except Exception as e:
        print(f"Error during code review: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
