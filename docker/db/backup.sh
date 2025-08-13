#!/usr/bin/env bash
set -euo pipefail
source /root/.env.sh

DB_NAME="${MYSQL_DATABASE:-${SQL_DATABASE:-}}"
if [ -z "$DB_NAME" ]; then
  echo "ERROR: No DB name set"
  exit 1
fi

cd /backup
filename="${DB_NAME}_$(date +%F_%T).sql"
echo "export started $filename"
mysqldump --user=root --password="${MYSQL_ROOT_PASSWORD}" "${DB_NAME}" > "$filename"
echo "export finished: $filename"

# clean old
ls -t | awk 'NR>30' | xargs -r -d '\n' rm
