from functools import lru_cache

from supabase import Client, create_client

from .config import get_settings


@lru_cache
def service_client() -> Client:
    s = get_settings()
    return create_client(s.SUPABASE_URL, s.SUPABASE_SERVICE_ROLE_KEY)


def user_client(access_token: str) -> Client:
    s = get_settings()
    client = create_client(s.SUPABASE_URL, s.SUPABASE_ANON_KEY)
    client.postgrest.auth(access_token)
    return client
