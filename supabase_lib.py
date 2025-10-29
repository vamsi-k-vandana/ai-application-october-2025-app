from supabase import create_client, Client
import os
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)
def query_rag_content(query_embedding, match_content, document_type):
  rag_results = supabase.rpc(
            'match_documents_by_document_type',
            {
                'query_embedding': query_embedding,
                'match_count': match_content,
                'query_document_type': document_type
            }
        ).execute()
  return rag_results