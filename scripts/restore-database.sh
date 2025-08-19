#!/bin/bash
# EquipeMed Database Restore Script
# Restores database volume from backup archive

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <backup-file.tar.gz>"
  echo "Example: $0 backups/20250819/database-20250819_143052.tar.gz"
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file '$BACKUP_FILE' not found!"
  exit 1
fi

echo "⚠️  WARNING: This will replace ALL data in the database volume!"
echo "Backup file: $BACKUP_FILE"
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Restore cancelled."
  exit 0
fi

echo "Stopping EquipeMed containers..."
docker-compose down || true

echo "Restoring database from backup..."
docker run --rm \
  -v eqmd_database:/data \
  -v $(pwd):/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/$BACKUP_FILE -C /data"

echo "✓ Database restored from $BACKUP_FILE"
echo "You can now start the containers with: docker-compose up -d"