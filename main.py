from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
import os
import json

from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Setup templates
templates = Jinja2Templates(directory="templates")

# Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# PubNub configuration
pubnub_publish_key = os.environ.get("PUBNUB_PUBLISH_KEY", "demo")
pubnub_subscribe_key = os.environ.get("PUBNUB_SUBSCRIBE_KEY", "demo")

pnconfig = PNConfiguration()
pnconfig.publish_key = pubnub_publish_key
pnconfig.subscribe_key = pubnub_subscribe_key
pnconfig.user_id = "server-instance"
pubnub_client = PubNub(pnconfig)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/message")
async def get_message():
    """Returns backend message as HTML fragment"""
    return HTMLResponse("<p>Hello World from FastAPI!</p>")


@app.get("/api/data")
async def get_data():
    """Returns Supabase data as HTML fragment"""
    try:
        # Query 'items' table from Supabase
        response = supabase.table('items').select("*").execute()
        if response.data and len(response.data) > 0:
            data_html = f"<pre>{json.dumps(response.data, indent=2)}</pre>"
        else:
            data_html = "<p>No data from Supabase (make sure to create an 'items' table)</p>"
        return HTMLResponse(data_html)
    except Exception as e:
        return HTMLResponse(f"<p>Error: {str(e)}</p>")


@app.get("/pingpong", response_class=HTMLResponse)
async def pingpong(request: Request):
    """Render the PubNub ping pong page"""
    return templates.TemplateResponse("pingpong.html", {
        "request": request,
        "pubnub_publish_key": pubnub_publish_key,
        "pubnub_subscribe_key": pubnub_subscribe_key
    })


@app.get("/api/pubnub/config")
async def get_pubnub_config():
    """Returns PubNub configuration"""
    return {
        "publish_key": pubnub_publish_key,
        "subscribe_key": pubnub_subscribe_key
    }


@app.post("/api/pubnub/publish/{channel}")
async def publish_message(channel: str, message: dict):
    """Publish a message to a PubNub channel"""
    try:
        envelope = pubnub_client.publish()\
            .channel(channel)\
            .message(message)\
            .sync()

        return {
            "status": "success",
            "timetoken": envelope.result.timetoken
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
