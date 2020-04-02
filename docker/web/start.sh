#!/usr/bin/env bash

python manage.py collectstatic --no-input
python manage.py migrate

./docker/web/wait-for-it.sh "db:3306" -- gunicorn "tennis.wsgi:application" --bind "0.0.0.0:8000"