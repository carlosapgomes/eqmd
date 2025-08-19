#!/bin/bash
# EquipeMed Volume Cleanup Script
# Removes all EQMD Docker volumes (DESTRUCTIVE OPERATION)

set -e

echo "⚠️  DANGER: This will permanently delete ALL EQMD data!"
echo "This includes:"
echo "  - Database (all patients, events, users)"
echo "  - Media files (all photos, videos)"  
echo "  - Static files"
echo
echo "This action CANNOT be undone!"
echo

read -p "Are you absolutely sure you want to delete ALL EQMD volumes? (type 'DELETE ALL DATA' to confirm): " confirm

if [ "$confirm" != "DELETE ALL DATA" ]; then
  echo "Operation cancelled - confirmation text did not match"
  exit 0
fi

echo
echo "Last chance - stopping containers and removing volumes in 5 seconds..."
sleep 5

echo "Stopping containers..."
docker-compose down || true

echo "Removing volumes..."
for volume in eqmd_database eqmd_media_files eqmd_static_files; do
  if docker volume inspect $volume >/dev/null 2>&1; then
    docker volume rm $volume
    echo "✓ Removed volume: $volume"
  else
    echo "⚠️  Volume $volume was already deleted"
  fi
done

echo
echo "✓ All EQMD volumes have been deleted"
echo "To recreate fresh volumes, run: docker-compose up -d"