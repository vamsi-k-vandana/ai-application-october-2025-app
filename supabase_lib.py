from dotenv import load_dotenv
import os
from supabase import create_client, Client

load_dotenv()
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
