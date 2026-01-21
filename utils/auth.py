"""Supabase authentication utilities."""
import os
import logging
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Environment variables
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
AUTH_ENABLED = os.environ.get('AUTH_ENABLED', 'false').lower() == 'true'


def is_auth_enabled() -> bool:
    """Check if authentication is enabled and properly configured."""
    return AUTH_ENABLED and bool(SUPABASE_URL and SUPABASE_ANON_KEY)


def get_supabase_config() -> dict:
    """Get Supabase configuration for client-side initialization."""
    return {
        'url': SUPABASE_URL,
        'anonKey': SUPABASE_ANON_KEY,
    }


def verify_session(access_token: str) -> Optional[dict]:
    """Verify a Supabase session token and return user info.

    Args:
        access_token: JWT access token from Supabase Auth

    Returns:
        User dictionary if valid, None otherwise
    """
    if not access_token:
        return None

    try:
        from utils.supabase_client import get_supabase_client, set_user_session

        client = get_supabase_client()

        # Set the session to validate it
        # Note: This also refreshes the token if needed
        response = client.auth.get_user(access_token)

        if response and response.user:
            return {
                'id': response.user.id,
                'email': response.user.email,
                'name': response.user.user_metadata.get('full_name', ''),
                'picture': response.user.user_metadata.get('avatar_url', ''),
            }
    except Exception as e:
        logger.debug(f"Token verification failed: {e}")

    return None
