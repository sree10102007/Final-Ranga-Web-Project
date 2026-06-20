#!/usr/bin/env bash

# Hardened Restore Script for Goat Farm Management System
# Decrypts and restores DB dumps and user uploads.
# Usage: ./restore.sh /var/backups/ranga_farm/backup_YYYYMMDDHHMMSS.tar.gz.gpg

set -euo pipefail

BACKUP_FILE="${1:-}"
UPLOADS_DIR="/app/static/uploads"
TEMP_RESTORE_PATH="/tmp/ranga_restore_$(date +%s)"
LOG_FILE="/var/log/ranga_restore.log"

# Load passphrase from env
PASSPHRASE="${BACKUP_ENCRYPTION_PASSPHRASE:-}"

echo "[$(date)] Starting Restore Process..." | tee -a "$LOG_FILE"

if [ -z "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file path argument is required!" | tee -a "$LOG_FILE"
    echo "Usage: $0 <path_to_encrypted_backup>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file $BACKUP_FILE does not exist!" | tee -a "$LOG_FILE"
    exit 1
fi

if [ -z "$PASSPHRASE" ]; then
    echo "ERROR: BACKUP_ENCRYPTION_PASSPHRASE environment variable is not defined!" | tee -a "$LOG_FILE"
    exit 1
fi

mkdir -p "$TEMP_RESTORE_PATH"

# 1. Decrypt Backup using GPG
echo "[$(date)] Decrypting backup file..." | tee -a "$LOG_FILE"
gpg --batch --yes --passphrase "$PASSPHRASE" --decrypt -o "${TEMP_RESTORE_PATH}/decrypted.tar.gz" "$BACKUP_FILE" 2>> "$LOG_FILE"

# 2. Extract Archive
echo "[$(date)] Extracting archive..." | tee -a "$LOG_FILE"
tar -xzf "${TEMP_RESTORE_PATH}/decrypted.tar.gz" -C "$TEMP_RESTORE_PATH"

# 3. Restore PostgreSQL Database
echo "[$(date)] Restoring database..." | tee -a "$LOG_FILE"
export PGPASSWORD="${DB_PASSWORD:-postgres}"
# Terminate existing connections first to avoid locked database errors
psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d postgres -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '${DB_NAME:-postgres}' AND pid <> pg_backend_pid();" 2>> "$LOG_FILE" || true

# Drop and recreate database to ensure clean state
psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME:-postgres};" 2>> "$LOG_FILE"
psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d postgres -c "CREATE DATABASE ${DB_NAME:-postgres};" 2>> "$LOG_FILE"

# Restore database schema and data
pg_restore -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d "${DB_NAME:-postgres}" -v "${TEMP_RESTORE_PATH}/db_dump.sql" 2>> "$LOG_FILE"

# 4. Restore uploads
if [ -f "${TEMP_RESTORE_PATH}/uploads.tar.gz" ]; then
    echo "[$(date)] Restoring media uploads..." | tee -a "$LOG_FILE"
    mkdir -p "$UPLOADS_DIR"
    tar -xzf "${TEMP_RESTORE_PATH}/uploads.tar.gz" -C "$UPLOADS_DIR"
fi

# Clean up
rm -rf "$TEMP_RESTORE_PATH"
echo "[$(date)] Restore completed successfully!" | tee -a "$LOG_FILE"
