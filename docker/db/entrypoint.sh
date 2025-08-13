#!/bin/sh

# env variables for cron
printenv | sed 's/^\(.*\)$/export \1/g' > /root/.env.sh
chmod +x /root/.env.sh

# start crond (Oracle Linux uses crond, not cron)
crond

# continue with mysql
exec docker-entrypoint.sh "$@"