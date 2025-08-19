#!/bin/bash
# EquipeMed Volume Information Script
# Shows status and usage information for all Docker volumes

set -e

echo "=== EQMD Docker Volumes Status ==="
echo

# Check if volumes exist
VOLUMES_EXIST=true

for volume in eqmd_database eqmd_media_files eqmd_static_files; do
  if ! docker volume inspect $volume >/dev/null 2>&1; then
    echo "❌ Volume $volume does not exist"
    VOLUMES_EXIST=false
  fi
done

if [ "$VOLUMES_EXIST" = false ]; then
  echo
  echo "To create volumes, run: docker-compose up -d"
  exit 1
fi

echo "📁 Database Volume:"
MOUNT_PATH=$(docker volume inspect eqmd_database | jq -r '.[0].Mountpoint')
echo "   Path: $MOUNT_PATH"
SIZE=$(docker run --rm -v eqmd_database:/data alpine du -sh /data 2>/dev/null | cut -f1)
echo "   Size: $SIZE"

echo
echo "🖼️  Media Files Volume:"
MOUNT_PATH=$(docker volume inspect eqmd_media_files | jq -r '.[0].Mountpoint')
echo "   Path: $MOUNT_PATH"
SIZE=$(docker run --rm -v eqmd_media_files:/data alpine du -sh /data 2>/dev/null | cut -f1)
echo "   Size: $SIZE"

echo
echo "⚡ Static Files Volume:"
MOUNT_PATH=$(docker volume inspect eqmd_static_files | jq -r '.[0].Mountpoint')
echo "   Path: $MOUNT_PATH"
SIZE=$(docker run --rm -v eqmd_static_files:/data alpine du -sh /data 2>/dev/null | cut -f1)
echo "   Size: $SIZE"

echo
echo "=== Volume Health Check ==="
echo "✓ All volumes are accessible"
echo
echo "To backup volumes:"
echo "  ./scripts/backup-database.sh"
echo "  ./scripts/backup-media.sh"