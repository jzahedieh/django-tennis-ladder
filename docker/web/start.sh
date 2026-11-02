#!/usr/bin/env bash

./docker/web/wait-for-it.sh "db:3306" -- echo "Database is ready"

python manage.py collectstatic --no-input
python manage.py migrate

exec gunicorn "tennis.wsgi:application" --bind "0.0.0.0:8000"