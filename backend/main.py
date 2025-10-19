from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import os

from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)


@app.get("/")
async def root():
    return {"message": "Hello World from FastAPI!"}


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/data")
async def get_data():
    """Example endpoint that queries Supabase"""
    try:
        # Example: Query a table called 'items'
        # Make sure to create this table in your Supabase database
        response = supabase.table('items').select("*").execute()
        return {"data": response.data}
    except Exception as e:
        return {"error": str(e), "data": []}
