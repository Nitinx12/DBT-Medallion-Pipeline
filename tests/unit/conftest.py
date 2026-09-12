import os
import sys
from pathlib import Path

# Ensure project root is on sys.path (mirrors scripts/python/extract.py behaviour)
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Guarantee required env vars for utils.engine import — CI sets these explicitly,
# local runs rely on .env (already present). Redundantly set here so tests
# never fail due to missing .env in a clean runner.
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DATABASE", "walmart_db")
os.environ.setdefault("POSTGRES_USERNAME", "walmart")
os.environ.setdefault("POSTGRES_PASSWORD", "walmart")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "unused_in_ci")
