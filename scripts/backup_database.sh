#!/bin/bash
# Database backup script for RouteX
# Usage: ./scripts/backup_database.sh [backup_directory]

set -e  # Exit on error

# Configuration
BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME="${DB_NAME:-routex}"
DB_USER="${DB_USER:-routex_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Backup filename
BACKUP_FILE="$BACKUP_DIR/routex_backup_$TIMESTAMP.sql"

echo "Starting database backup..."
echo "Database: $DB_NAME"
echo "Backup file: $BACKUP_FILE"

# Perform backup using pg_dump
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    -f "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"
BACKUP_FILE="${BACKUP_FILE}.gz"

echo "✅ Backup completed successfully: $BACKUP_FILE"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "routex_backup_*.sql.gz" -mtime +30 -delete

echo "✅ Old backups (older than 30 days) cleaned up"

