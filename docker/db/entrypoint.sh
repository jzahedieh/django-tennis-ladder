#!/bin/sh
set -e

# export env for cron with safe quoting
printenv | sed -E "s/^(.*)=(.*)$/export \1='\2'/" > /root/.env.sh
chmod +x /root/.env.sh

# start cron
crond

# hand off to mysql entrypoint
exec docker-entrypoint.sh "$@"
