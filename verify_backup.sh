#!/usr/bin/env bash

# Hardened Backup Verification Script
# Decrypts the latest backup and validates database restore integrity on a test database.

set -euo pipefail

BACKUP_DIR="/var/backups/ranga_farm"
TEMP_VERIFY_PATH="/tmp/ranga_verify_$(date +%s)"
VERIFY_DB="ranga_farm_verify"
LOG_FILE="/var/log/ranga_backup_verify.log"

PASSPHRASE="${BACKUP_ENCRYPTION_PASSPHRASE:-}"

echo "[$(date)] Starting Backup Verification..." | tee -a "$LOG_FILE"

if [ -z "$PASSPHRASE" ]; then
    echo "ERROR: BACKUP_ENCRYPTION_PASSPHRASE environment variable is not defined!" | tee -a "$LOG_FILE"
    exit 1
fi

# Find latest backup file
LATEST_BACKUP=$(find "$BACKUP_DIR" -name "backup_*.tar.gz.gpg" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" ")

if [ -z "$LATEST_BACKUP" ]; then
    echo "ERROR: No backup files found in $BACKUP_DIR" | tee -a "$LOG_FILE"
    exit 1
fi

echo "[$(date)] Verifying latest backup: $LATEST_BACKUP" | tee -a "$LOG_FILE"
mkdir -p "$TEMP_VERIFY_PATH"

# 1. Decrypt Backup using GPG
echo "[$(date)] Decrypting backup file..." | tee -a "$LOG_FILE"
gpg --batch --yes --passphrase "$PASSPHRASE" --decrypt -o "${TEMP_VERIFY_PATH}/decrypted.tar.gz" "$LATEST_BACKUP" 2>> "$LOG_FILE"

# 2. Extract Archive
tar -xzf "${TEMP_VERIFY_PATH}/decrypted.tar.gz" -C "$TEMP_VERIFY_PATH"

# 3. Restore to test database
echo "[$(date)] Creating verification database '$VERIFY_DB'..." | tee -a "$LOG_FILE"
export PGPASSWORD="${DB_PASSWORD:-postgres}"
psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d postgres -c "DROP DATABASE IF EXISTS ${VERIFY_DB};" 2>> "$LOG_FILE"
psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d postgres -c "CREATE DATABASE ${VERIFY_DB};" 2>> "$LOG_FILE"

echo "[$(date)] Restoring backup into '$VERIFY_DB'..." | tee -a "$LOG_FILE"
pg_restore -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d "$VERIFY_DB" "${TEMP_VERIFY_PATH}/db_dump.sql" 2>> "$LOG_FILE"

# 4. Perform integrity check
echo "[$(date)] Running database structure checks..." | tee -a "$LOG_FILE"
TABLE_COUNT=$(psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d "$VERIFY_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
TABLE_COUNT_TRIM=$(echo "$TABLE_COUNT" | tr -d '[:space:]')

echo "[$(date)] Found $TABLE_COUNT_TRIM tables in restored public schema." | tee -a "$LOG_FILE"

if [ "$TABLE_COUNT_TRIM" -gt 0 ]; then
    echo "[$(date)] INTEGRITY CHECK PASSED: Restored schema contains tables." | tee -a "$LOG_FILE"
else
    echo "[$(date)] INTEGRITY CHECK FAILED: Restored schema is empty!" | tee -a "$LOG_FILE"
    exit 1
fi

# Clean up verify database and temp folder
echo "[$(date)] Cleaning up..." | tee -a "$LOG_FILE"
psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-postgres}" -d postgres -c "DROP DATABASE IF EXISTS ${VERIFY_DB};" 2>> "$LOG_FILE"
rm -rf "$TEMP_VERIFY_PATH"

echo "[$(date)] Backup Verification successfully completed!" | tee -a "$LOG_FILE"
