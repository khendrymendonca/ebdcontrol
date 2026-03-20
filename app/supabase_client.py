import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_supabase_client: Client = None

def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL e SUPABASE_ANON_KEY devem estar configurados.")
        _supabase_client = create_client(url, key)
    return _supabase_client

def get_supabase_admin() -> Client:
    """Cliente com service key para operações administrativas (professor)."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar configurados.")
    return create_client(url, key)
