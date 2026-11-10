#!/usr/bin/env bash
set -e

ROLE="${1:-api}"

wait_for_db() {
  echo "Waiting for database..."
  python - <<'PY'
import time, sys
from sqlalchemy import create_engine, text
from app.core.config import settings
for i in range(30):
    try:
        e = create_engine(settings.database_url)
        with e.connect() as c:
            c.execute(text("SELECT 1"))
        print("Database is ready.")
        sys.exit(0)
    except Exception as exc:
        print(f"  db not ready ({exc}); retrying...")
        time.sleep(2)
print("Database did not become ready in time.", file=sys.stderr)
sys.exit(1)
PY
}

case "$ROLE" in
  api)
    wait_for_db
    echo "Running migrations..."
    alembic upgrade head || echo "alembic failed; relying on create_all"
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
    ;;
  worker)
    wait_for_db
    exec celery -A app.core.celery_app.celery_app worker --loglevel=info -Q reelvault
    ;;
  *)
    exec "$@"
    ;;
esac
