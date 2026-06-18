#!/usr/bin/env bash

# Hardened Incremental/Full Backup Script
# Automatically dumps DB, tarball uploads, encrypts using GPG symmetric cryptography, and rotates.
# Setup as daily cron job: 0 2 * * * /app/backup.sh

set -euo pipefail

BACKUP_DIR="/var/backups/ranga_farm"
UPLOADS_DIR="/app/static/uploads"
TIMESTAMP=$(date +"%Y%m%d%H%M%S")
TEMP_BACKUP_PATH="/tmp/ranga_backup_${TIMESTAMP}"
LOG_FILE="/var/log/ranga_backup.log"

# Load passphrase from env
PASSPHRASE="${BACKUP_ENCRYPTION_PASSPHRASE:-}"

echo "[$(date)] Starting Backup Process..." >> "$LOG_FILE"

if [ -z "$PASSPHRASE" ]; then
    echo "[$(date)] ERROR: BACKUP_ENCRYPTION_PASSPHRASE environment variable is not defined!" >> "$LOG_FILE"
    exit 1
fi

mkdir -p "$BACKUP_DIR"
mkdir -p "$TEMP_BACKUP_PATH"

# 1. Perform Postgres Database Dump
echo "[$(date)] Dumping PostgreSQL database..." >> "$LOG_FILE"
export PGPASSWORD="${DB_PASSWORD:-postgres}"
pg_dump -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d "${DB_NAME:-postgres}" -F c -b -v -f "${TEMP_BACKUP_PATH}/db_dump.sql" 2>> "$LOG_FILE"

# 2. Package uploaded documents & bills
if [ -d "$UPLOADS_DIR" ]; then
    echo "[$(date)] Packaging media uploads..." >> "$LOG_FILE"
    tar -czf "${TEMP_BACKUP_PATH}/uploads.tar.gz" -C "$UPLOADS_DIR" .
fi

# 3. Compile and compress archive
echo "[$(date)] Compressing archive..." >> "$LOG_FILE"
tar -czf "${TEMP_BACKUP_PATH}.tar.gz" -C "$TEMP_BACKUP_PATH" .

# 4. Symmetrically Encrypt archive using GPG (ASVS 6.2 / 6.4)
echo "[$(date)] Encrypting archive..." >> "$LOG_FILE"
gpg --batch --yes --passphrase "$PASSPHRASE" --symmetric --cipher-algo AES256 -o "${BACKUP_DIR}/backup_${TIMESTAMP}.tar.gz.gpg" "${TEMP_BACKUP_PATH}.tar.gz"

# 5. Clean up temporary directories
rm -rf "$TEMP_BACKUP_PATH" "${TEMP_BACKUP_PATH}.tar.gz"

# 6. Rotate Backups (Retain last 7 archives, remove older)
echo "[$(date)] Rotating older backups..." >> "$LOG_FILE"
find "$BACKUP_DIR" -name "backup_*.tar.gz.gpg" -type f -mtime +7 -delete

echo "[$(date)] Backup completed successfully. Encrypted file: ${BACKUP_DIR}/backup_${TIMESTAMP}.tar.gz.gpg" >> "$LOG_FILE"
