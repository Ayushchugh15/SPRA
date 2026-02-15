"""
SPRA Configuration - Production & Development
"""
import os
from pathlib import Path

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Environment
ENV = os.environ.get('FLASK_ENV', 'development')
DEBUG = ENV == 'development'
TESTING = False

# Secret key for sessions (change in production!)
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database - use DATA_DIR for persistent storage
DATA_DIR = Path(os.environ.get('SPRA_DATA_DIR', BASE_DIR / 'data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# SQLite path in data directory (default)
# For PostgreSQL: postgresql://user:pass@localhost/spra
DB_PATH = (DATA_DIR / "spra.db").resolve()
DATABASE_URI = os.environ.get(
    'DATABASE_URL',
    f'sqlite:///{DB_PATH.as_posix()}'
)

# Fix PostgreSQL URL format (Render uses postgres://, but SQLAlchemy needs postgresql://)
if DATABASE_URI and DATABASE_URI.startswith('postgres://'):
    DATABASE_URI = DATABASE_URI.replace('postgres://', 'postgresql://', 1)

# Production overrides
if ENV == 'production':
    DEBUG = False
    # Ensure we don't use in-memory or dev paths
    if 'sqlite' in DATABASE_URI and 'spra.db' not in DATABASE_URI:
        DATABASE_URI = f'sqlite:///{DATA_DIR / "spra.db"}'
