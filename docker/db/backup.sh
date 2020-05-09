#!/usr/bin/env bash
source /root/.env.sh

cd /backup/ || exit

filename="${SQL_DATABASE}"_"$(date +%F_%T)".sql

echo "export started $filename"
mysqldump -u"$SQL_USER" -p"$SQL_PASSWORD" "$SQL_DATABASE" > "$filename"
echo "export finished: $filename"

# clean up old exports, does not support filename spaces
old=$(ls -t | awk 'NR>14')
echo "$old" | xargs -d '\n' rm
echo "export deleted: $old"
