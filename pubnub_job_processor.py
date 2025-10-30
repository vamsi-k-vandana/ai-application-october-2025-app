"""
PubNub Job Processor

This script listens on a PubNub queue for job requests, queries job context from Supabase,
submits the request to OpenAI for processing, stores the response in Supabase,
and publishes the response reference back to PubNub.
"""

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory
from openai import OpenAI
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PUBNUB_PUBLISH_KEY = os.environ.get("PUBNUB_PUBLISH_KEY")
PUBNUB_SUBSCRIBE_KEY = os.environ.get("PUBNUB_SUBSCRIBE_KEY")
PUBNUB_JOB_CHANNEL = os.environ.get("PUBNUB_JOB_CHANNEL", "job-requests")
PUBNUB_RESPONSE_CHANNEL = os.environ.get("PUBNUB_RESPONSE_CHANNEL", "job-responses")

# Initialize clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)


class JobProcessor:
    """Processes job requests from PubNub queue"""

    def __init__(self):
        self.supabase = supabase
        self.openai_client = openai_client

    def query_job_context(self, job_id: str, job_description: str = None) -> dict:
        """
        Query job context from Supabase using embeddings

        Args:
            job_id: The ID of the job
            job_description: Optional job description for semantic search

        Returns:
            dict containing job context
        """
        try:
            # If we have a job_id, query directly
            if job_id:
                response = self.supabase.table('rag_content').select("*").eq('document_id', job_id).eq('document_type', 'job').execute()
                if response.data and len(response.data) > 0:
                    return {
                        'job_id': job_id,
                        'context': response.data[0].get('context', ''),
                        'metadata': response.data[0]
                    }

            # If we have a job description, use embeddings for semantic search
            if job_description:
                embedding_response = self.openai_client.embeddings.create(
                    input=job_description,
                    model='text-embedding-3-small'
                )
                query_embedding = embedding_response.data[0].embedding

                # Query using the RPC function
                rag_results = self.supabase.rpc(
                    'match_documents_by_document_type',
                    {
                        'query_embedding': query_embedding,
                        'match_count': 1,
                        'query_document_type': 'job'
                    }
                ).execute()

                if rag_results.data and len(rag_results.data) > 0:
                    return {
                        'job_id': rag_results.data[0].get('document_id', ''),
                        'context': rag_results.data[0].get('context', ''),
                        'similarity': rag_results.data[0].get('similarity', 0),
                        'metadata': rag_results.data[0]
                    }

            return {'error': 'No job context found'}

        except Exception as e:
            logger.error(f"Error querying job context: {e}")
            return {'error': str(e)}

    def process_with_openai(self, job_context: dict, user_query: str) -> str:
        """
        Process the job context and user query with OpenAI

        Args:
            job_context: Dictionary containing job information
            user_query: The user's question or request

        Returns:
            OpenAI response text
        """
        try:
            context_text = job_context.get('context', '')

            system_prompt = f"""You are an expert job matching assistant. Use the following job context to answer questions:

{context_text}

Provide helpful, accurate information about the job based on the context provided."""

            completion = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                max_tokens=500,
                temperature=0
            )

            return completion.choices[0].message.content

        except Exception as e:
            logger.error(f"Error processing with OpenAI: {e}")
            raise

    def store_response(self, job_id: str, user_query: str, response: str, metadata: dict = None) -> dict:
        """
        Store the AI response in Supabase

        Args:
            job_id: The job ID
            user_query: The original user query
            response: The AI response
            metadata: Additional metadata

        Returns:
            Dictionary with the inserted record
        """
        try:
            record = {
                'job_id': job_id,
                'user_query': user_query,
                'ai_response': response,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }

            result = self.supabase.table('job_responses').insert(record).execute()

            if result.data:
                logger.info(f"Response stored successfully with ID: {result.data[0].get('id')}")
                return result.data[0]
            else:
                raise Exception("Failed to store response in Supabase")

        except Exception as e:
            logger.error(f"Error storing response: {e}")
            raise

    def process_job_request(self, message: dict) -> dict:
        """
        Main processing function for job requests

        Args:
            message: The message received from PubNub

        Returns:
            Dictionary containing the response reference
        """
        try:
            job_id = message.get('job_id')
            job_description = message.get('job_description')
            user_query = message.get('query', 'Tell me about this job')

            logger.info(f"Processing job request - job_id: {job_id}, query: {user_query}")

            # Step 1: Query job context
            job_context = self.query_job_context(job_id, job_description)
            if 'error' in job_context:
                return {'error': job_context['error'], 'request_id': message.get('request_id')}

            # Step 2: Process with OpenAI
            ai_response = self.process_with_openai(job_context, user_query)

            # Step 3: Store in Supabase
            stored_record = self.store_response(
                job_id=job_context.get('job_id', job_id),
                user_query=user_query,
                response=ai_response,
                metadata={
                    'similarity': job_context.get('similarity'),
                    'request_id': message.get('request_id'),
                    'original_job_id': job_id
                }
            )

            # Step 4: Return reference
            return {
                'status': 'success',
                'response_id': stored_record.get('id'),
                'job_id': job_context.get('job_id'),
                'request_id': message.get('request_id'),
                'response': ai_response,
                'timestamp': stored_record.get('created_at')
            }

        except Exception as e:
            logger.error(f"Error processing job request: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'request_id': message.get('request_id')
            }


class PubNubJobListener(SubscribeCallback):
    """PubNub callback handler for job requests"""

    def __init__(self, pubnub_client, response_channel: str):
        self.pubnub = pubnub_client
        self.response_channel = response_channel
        self.processor = JobProcessor()

    def status(self, pubnub, status):
        if status.category == PNStatusCategory.PNConnectedCategory:
            logger.info("Connected to PubNub")
        elif status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            logger.warning("Disconnected from PubNub")
        elif status.category == PNStatusCategory.PNReconnectedCategory:
            logger.info("Reconnected to PubNub")

    def message(self, pubnub, message):
        """Handle incoming messages from PubNub"""
        try:
            logger.info(f"Received message: {message.message}")

            # Process the job request
            response = self.processor.process_job_request(message.message)

            # Publish response to response channel
            self.publish_response(response)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            error_response = {
                'status': 'error',
                'error': str(e),
                'request_id': message.message.get('request_id')
            }
            self.publish_response(error_response)

    def publish_response(self, response: dict):
        """Publish response to PubNub response channel"""
        try:
            envelope = self.pubnub.publish()\
                .channel(self.response_channel)\
                .message(response)\
                .sync()

            logger.info(f"Response published to {self.response_channel}: {response.get('status')}")

        except Exception as e:
            logger.error(f"Error publishing response: {e}")


def main():
    """Main function to start the PubNub listener"""

    # Validate environment variables
    if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY,
                PUBNUB_PUBLISH_KEY, PUBNUB_SUBSCRIBE_KEY]):
        logger.error("Missing required environment variables")
        return

    # Configure PubNub
    pnconfig = PNConfiguration()
    pnconfig.publish_key = PUBNUB_PUBLISH_KEY
    pnconfig.subscribe_key = PUBNUB_SUBSCRIBE_KEY
    pnconfig.user_id = "job-processor-worker"

    pubnub_client = PubNub(pnconfig)

    # Set up listener
    listener = PubNubJobListener(pubnub_client, PUBNUB_RESPONSE_CHANNEL)
    pubnub_client.add_listener(listener)

    # Subscribe to job channel
    pubnub_client.subscribe().channels(PUBNUB_JOB_CHANNEL).execute()

    logger.info(f"Listening on channel: {PUBNUB_JOB_CHANNEL}")
    logger.info(f"Publishing responses to: {PUBNUB_RESPONSE_CHANNEL}")
    logger.info("Press Ctrl+C to stop")

    try:
        # Keep the script running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        pubnub_client.unsubscribe_all()
        pubnub_client.stop()


if __name__ == "__main__":
    main()
