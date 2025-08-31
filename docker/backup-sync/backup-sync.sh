#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="/backups"
: "${S3_BUCKET:?S3_BUCKET env missing}"
S3_PREFIX="${S3_PREFIX:-db-backup}"

# find newest .sql file
LATEST="$(ls -1t ${SRC_DIR}/*.sql 2>/dev/null | head -n1 || true)"
if [ -z "${LATEST}" ]; then
  echo "No backup file found in ${SRC_DIR}"
  exit 1
fi

BASENAME="$(basename "$LATEST")"

echo "Uploading ${BASENAME} to s3://${S3_BUCKET}/${S3_PREFIX}/"

# keep filename (dated)
aws s3 cp "${LATEST}" "s3://${S3_BUCKET}/${S3_PREFIX}/${BASENAME}"

# also maintain a moving pointer
aws s3 cp "${LATEST}" "s3://${S3_BUCKET}/${S3_PREFIX}/latest.sql"
