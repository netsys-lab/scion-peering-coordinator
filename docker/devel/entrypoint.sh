#!/bin/sh

set -e
root=$1

# Wait for DB
appdeps.py --wait-secs 60 --port-wait $POSTGRES_HOST:$POSTGRES_PORT

# Initialize DB (if reqired)
$root/manage.py makemigrations
$root/manage.py migrate
$root/manage.py createsuperuser --noinput

# Run webserver
$root/manage.py runserver 0.0.0.0:8000
