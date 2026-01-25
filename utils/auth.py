"""Supabase authentication utilities.

Note: Most auth functionality is handled client-side via supabase-auth.js.
This module provides constants used by app.py.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# Environment variables (used by app.py)
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
AUTH_ENABLED = os.environ.get('AUTH_ENABLED', 'false').lower() == 'true'
