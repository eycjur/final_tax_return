"""Application-wide constants and paths."""
from pathlib import Path

# Project root directory
BASE_DIR = Path(__file__).parent.parent

# File storage directories
ATTACHMENTS_DIR = BASE_DIR / 'attachments'
DATA_DIR = BASE_DIR / 'data'

# Database path (for legacy SQLite)
SQLITE_DB_PATH = DATA_DIR / 'tax_records.db'
