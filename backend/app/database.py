from supabase import create_client, Client
from app.config import settings

_supabase_client: Client = None


def init_supabase():
    """Initialize Supabase client."""
    global _supabase_client
    _supabase_client = create_client(
        settings.supabase_url,
        settings.supabase_secret_key
    )
    return _supabase_client


def get_supabase_client() -> Client:
    """Get Supabase client instance."""
    global _supabase_client
    if _supabase_client is None:
        init_supabase()
    return _supabase_client
