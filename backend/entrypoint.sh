#!/bin/sh
# Bring the schema up to date, then hand control to the server.
#
# Compose gates the api service on the database healthcheck, but a bare
# `docker run` does not, so retry instead of crash-looping on a database that
# is still initialising.
set -e

attempts=30
i=1
while [ "$i" -le "$attempts" ]; do
    if alembic upgrade head; then
        echo "entrypoint: migrations applied"
        break
    fi
    if [ "$i" -eq "$attempts" ]; then
        echo "entrypoint: database unreachable after $attempts attempts, giving up" >&2
        exit 1
    fi
    echo "entrypoint: database not ready (attempt $i/$attempts), retrying in 2s"
    i=$((i + 1))
    sleep 2
done

exec "$@"
