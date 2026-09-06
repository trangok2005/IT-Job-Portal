#!/bin/sh
set -eu

python -m pip install --upgrade pip
pip install -r requirements/production.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput