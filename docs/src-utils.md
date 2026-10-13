# Src Utils

Shared infra (`src/utils/`) for `scripts/python/*` — config, connections, logging.

- **engine.py**: `load_dotenv()` at import, validates `POSTGRES_*`/`MONGO_*` (fails loud, lists missing), casts `PORT` to `int`, warns for optional schemas/Databricks.
- **connection.py**: `get_mongo_db()` / `get_postgres_engine()` / `get_databricks_connection()` — lazy, cached, `ping`/`SELECT 1` checked. `URL.create` avoids password-encoding bugs.
- **logger.py**: `get_logger(name)` — console + `logs/<name>_YYYY-MM-DD.log` (RotatingFileHandler 5MB), idempotent.

```python
from src.utils.connection import get_postgres_engine
from src.utils.logger import get_logger

log = get_logger("extract")
```

Config from `.env` via `engine.py`; downstream correction for containers happens in callers.

See `architecture.md` §9.
