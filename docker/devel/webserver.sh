#!/bin/sh

set -e

# Wait for DB
appdeps.py --wait-secs 60 --port-wait $POSTGRES_HOST:$POSTGRES_PORT

./manage.py makemigrations

# Initialize DB (if required)
if ! ./manage.py migrate --check; then
    ./manage.py migrate
    ./manage.py createsuperuser --noinput
fi

# Run webserver
gunicorn -b 0.0.0.0:8000 standalone_coord.wsgi
