#!/bin/bash
# Matrix media store backup script

set -e

BACKUP_DIR="backups/$(date +%Y%m%d)"
BACKUP_FILE="matrix_media-$(date +%Y%m%d_%H%M%S).tar.gz"

echo "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

VOLUME=$(docker volume ls --format "{{.Name}}" | grep -E "matrix_media_store$" | head -1)
if [ -z "$VOLUME" ]; then
  echo "Error: matrix media store volume not found"
  exit 1
fi

echo "Backing up Matrix media store volume: $VOLUME"
docker run --rm \
  -v "$VOLUME":/data \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine tar czf "/backup/$BACKUP_FILE" -C /data .

echo "Matrix media store backed up to $BACKUP_DIR/$BACKUP_FILE"
echo "Backup size: $(ls -lh "$BACKUP_DIR/$BACKUP_FILE" | awk '{print $5}')"
