#!/bin/sh
set -e

echo "Waiting for Postgres at ${DB_HOST:-db}:${DB_PORT:-5432}..."
until python - <<'PY' >/dev/null 2>&1
import os

import psycopg2

psycopg2.connect(
    host=os.environ.get("DB_HOST", "db"),
    port=os.environ.get("DB_PORT", "5432"),
    dbname=os.environ.get("DB_NAME", "job_portal"),
    user=os.environ.get("DB_USER", "job_portal"),
    password=os.environ.get("DB_PASSWORD", "job_portal"),
).close()
PY
do
  sleep 1
done

echo "Running migrations..."
python manage.py migrate --noinput

case "$1" in
  worker)
    echo "Starting Django-Q cluster..."
    exec python manage.py qcluster
    ;;
  *)
    echo "Starting Django dev server..."
    exec python manage.py runserver 0.0.0.0:8000
    ;;
esac
