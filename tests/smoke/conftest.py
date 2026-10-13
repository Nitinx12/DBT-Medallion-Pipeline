import os
import sys
from pathlib import Path

# Ensure project root is on sys.path (mirrors tests/unit/conftest.py).
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load .env first (override=False, so CI-injected env always wins), then
# dummy defaults only fill keys still missing so importing
# src.utils.engine never fails on a clean runner. On machines with live
# services + .env, the real credentials above win and tests truly connect.
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DATABASE", "walmart_db")
os.environ.setdefault("POSTGRES_USERNAME", "walmart")
os.environ.setdefault("POSTGRES_PASSWORD", "walmart")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "unused_in_ci")
