#!/bin/sh
set -eu

python -m pip install --upgrade pip
pip install -r requirements/production.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Khởi tạo demo một lần cho deployment Render miễn phí. Xóa hoặc tắt cờ môi trường
# sau lần deploy thành công đầu tiên để các lần build sau bỏ qua bước này.
if [ "${RUN_RENDER_SEED:-false}" = "true" ]; then
    python manage.py seed_render_demo
fi

if [ "${RUN_REBUILD_EMBEDDINGS:-false}" = "true" ]; then
    python manage.py rebuild_embeddings --stagger-seconds 5
fi
