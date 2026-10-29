
#!/usr/bin/env bash
set -Eeuo pipefail

python manage.py migrate --noinput
python manage.py collectstatic --noinput

celery -A config worker --loglevel=info &
WORKER_PID=$!

celery -A config beat --loglevel=info &
BEAT_PID=$!

gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-10000} &
GUNICORN_PID=$!

cleanup() {
    kill "$WORKER_PID" "$BEAT_PID" "$GUNICORN_PID" 2>/dev/null || true
    wait || true
}

trap cleanup EXIT TERM INT

wait -n "$WORKER_PID" "$BEAT_PID" "$GUNICORN_PID"
