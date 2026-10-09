#!/bin/sh
set -eu
cd /opt/trading-control-room
if ! grep -q '^TWELVE_DATA_API_KEY=.' .env; then exit 0; fi
id=$(docker compose -f compose.oracle.yml ps -q control-room)
[ -n "$id" ] || exit 1
state=$(docker inspect --format '{{.State.Health.Status}}' "$id")
if [ "$state" = unhealthy ]; then
    docker compose -f compose.oracle.yml restart control-room
fi
