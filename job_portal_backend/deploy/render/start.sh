#!/bin/sh
set -eu

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT}" --workers "${GUNICORN_WORKERS:-2}" --timeout "${GUNICORN_TIMEOUT:-120}" --access-logfile - --error-logfile -
