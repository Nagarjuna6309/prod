#!/usr/bin/env bash
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

celery -A config worker --loglevel=info &
WORKER_PID=$!

celery -A config beat --loglevel=info &
BEAT_PID=$!

gunicorn config.wsgi:application &
GUNICORN_PID=$!

cleanup() {
    kill "$WORKER_PID" "$BEAT_PID" "$GUNICORN_PID" 2>/dev/null || true
    wait
}

trap cleanup SIGTERM SIGINT
wait -n