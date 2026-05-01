#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-${HOME}/ledgrio-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
DUMP_FILE="${BACKUP_DIR}/ledgrio-${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

docker compose exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-ledgrio}" \
  "${POSTGRES_DB:-ledgrio}" | gzip > "${DUMP_FILE}"

echo "Backup written to ${DUMP_FILE}"

find "${BACKUP_DIR}" -name 'ledgrio-*.sql.gz' -mtime +"${RETENTION_DAYS}" -delete
echo "Pruned backups older than ${RETENTION_DAYS} days"

# Off-site copy (optional, env-gated):
# [[ -n "${BACKUP_RCLONE_REMOTE:-}" ]] && rclone copy "${DUMP_FILE}" "${BACKUP_RCLONE_REMOTE}/ledgrio/"
