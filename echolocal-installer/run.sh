#!/bin/sh
set -e

# A single long-lived process; unbuffered so the container log stays live.
export PYTHONUNBUFFERED=1

exec python3 /app/server.py