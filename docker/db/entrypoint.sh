#!/bin/sh

# env variables for cron
printenv | sed 's/^\(.*\)$/export \1/g' > /root/.env.sh
chmod +x /root/.env.sh

# start crond
cron

# continue with mariadb
exec docker-entrypoint.sh "$@"