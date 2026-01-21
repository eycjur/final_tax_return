"""Tax Return Record Application - App initialization"""
import os

import dash
import dash_bootstrap_components as dbc
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title='確定申告収支記録',
    meta_tags=[
        {"charset": "utf-8"},
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ]
)

# Flask server reference (for deployment)
server = app.server

# Check if authentication is enabled
AUTH_ENABLED = os.environ.get('AUTH_ENABLED', 'false').lower() == 'true'

# Supabase configuration for client-side
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
