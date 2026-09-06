#!/bin/sh
set -eu

python -m pip install --upgrade pip
pip install -r requirements/production.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# One-time demo bootstrap for free Render deployments. Remove/disable the
# environment flag after the first successful deploy so later builds skip it.
if [ "${RUN_RENDER_SEED:-false}" = "true" ]; then
    python manage.py seed_render_demo
fi

if [ "${RUN_REBUILD_EMBEDDINGS:-false}" = "true" ]; then
    python manage.py rebuild_embeddings --stagger-seconds 5
fi
