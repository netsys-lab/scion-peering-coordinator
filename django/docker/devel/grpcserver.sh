#!/bin/sh

set -e

# Wait for DB
appdeps.py --wait-secs 60 --port-wait $POSTGRES_HOST:$POSTGRES_PORT

./manage.py makemigrations

# Run gRPC server
./manage.py grpcrunserver
