#!/usr/bin/env bash
source /root/.env.sh

cd /backup/ || exit

filename="${SQL_DATABASE}"_"$(date +%F_%T)".sql

echo "export started $filename"
mysqldump --user=root --password="${MYSQL_ROOT_PASSWORD}" "${SQL_DATABASE}" > $filename
echo "export finished: $filename"

# clean up old exports, does not support filename spaces
old=$(ls -t | awk 'NR>30')
echo "$old" | xargs -d '\n' rm
echo "export deleted: $old"
