"""Supabase client configuration and utilities."""
import logging
import os
from functools import lru_cache

from dotenv import load_dotenv

from supabase import Client, create_client

load_dotenv()

logger = logging.getLogger(__name__)

# Environment variables
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')


class SupabaseClientError(Exception):
    """Custom exception for Supabase client errors."""
    pass


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get Supabase client instance (cached).

    Uses the anon key. RLS policies control data access per user.
    """
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise SupabaseClientError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables"
        )

    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def is_supabase_configured() -> bool:
    """Check if Supabase is properly configured."""
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


# Session management for authenticated requests
_current_session = None


def set_user_session(access_token: str, refresh_token: str):
    """Set the current user session for authenticated requests."""
    global _current_session
    _current_session = {
        'access_token': access_token,
        'refresh_token': refresh_token
    }

    # Set session on the Supabase client
    client = get_supabase_client()
    client.auth.set_session(access_token, refresh_token)


def get_current_user() -> dict | None:
    """Get the current authenticated user."""
    try:
        client = get_supabase_client()
        response = client.auth.get_user()
        if response and response.user:
            return {
                'id': response.user.id,
                'email': response.user.email,
                'name': response.user.user_metadata.get('full_name', ''),
                'picture': response.user.user_metadata.get('avatar_url', ''),
            }
    except Exception as e:
        logger.debug(f"No authenticated user: {e}")
    return None


def get_current_user_id() -> str | None:
    """Get the current authenticated user's ID."""
    user = get_current_user()
    return user['id'] if user else None


def sign_out():
    """Sign out the current user."""
    global _current_session
    _current_session = None

    try:
        client = get_supabase_client()
        client.auth.sign_out()
    except Exception as e:
        logger.warning(f"Error during sign out: {e}")


def ensure_session_from_auth_data(auth_session: dict | None) -> bool:
    """Set user session from Dash auth session data if available.

    This helper function extracts access_token and refresh_token from the
    auth_session dict (from dcc.Store) and sets the Supabase session.

    Args:
        auth_session: Dict containing 'access_token' and 'refresh_token' keys,
                      or None if not authenticated.

    Returns:
        True if session was set successfully, False otherwise.
    """
    if not auth_session:
        return False

    access_token = auth_session.get('access_token')
    refresh_token = auth_session.get('refresh_token')

    if access_token and refresh_token:
        set_user_session(access_token, refresh_token)
        return True

    return False
