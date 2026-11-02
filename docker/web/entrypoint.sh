#!/bin/sh
set -e

# Export all current env vars to a file cron can source
printenv | sed -E "s/^(.*)=(.*)$/export \1='\2'/" > /root/.env.sh
chmod +x /root/.env.sh

# Start cron in background
cron

if [ $# -eq 0 ]; then
    exec ./docker/web/start.sh
else
    exec "$@"
fi
