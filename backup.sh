#!/bin/bash

# EquipeMed Production Backup Script
# Creates comprehensive backup before upgrades

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

echo "🛡️ Starting EquipeMed production backup..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root"
   exit 1
fi

# Check if docker compose exists
if ! command -v docker &> /dev/null; then
    print_error "docker is not installed or not in PATH"
    exit 1
fi

# Generate timestamp for backup files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

print_info "Backup timestamp: $TIMESTAMP"
print_info "Backup directory: $BACKUP_DIR"

# 1. Database backup
print_info "Creating database backup..."
if docker compose exec postgres pg_dump -U eqmd_user eqmd_db | gzip > "$BACKUP_DIR/database_backup_${TIMESTAMP}.sql.gz"; then
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/database_backup_${TIMESTAMP}.sql.gz" | cut -f1)
    print_status "Database backup created: database_backup_${TIMESTAMP}.sql.gz ($BACKUP_SIZE)"
else
    print_error "Database backup failed!"
    exit 1
fi

# 2. Media files backup (if directory exists and has content)
if [ -d "./media" ] && [ "$(ls -A ./media 2>/dev/null)" ]; then
    print_info "Creating media files backup..."
    if tar -czf "$BACKUP_DIR/media_backup_${TIMESTAMP}.tar.gz" ./media/; then
        MEDIA_SIZE=$(du -h "$BACKUP_DIR/media_backup_${TIMESTAMP}.tar.gz" | cut -f1)
        print_status "Media files backup created: media_backup_${TIMESTAMP}.tar.gz ($MEDIA_SIZE)"
    else
        print_error "Media files backup failed!"
        exit 1
    fi
else
    print_info "No media files found to backup (./media/ empty or missing)"
fi

# 3. PostgreSQL volume backup
print_info "Creating PostgreSQL volume backup..."
POSTGRES_VOLUME=$(docker volume ls --format "{{.Name}}" | grep postgres_data | head -1)
if [ -n "$POSTGRES_VOLUME" ]; then
    if docker run --rm -v "$POSTGRES_VOLUME":/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf "/backup/postgres_volume_${TIMESTAMP}.tar.gz" -C /data .; then
        VOLUME_SIZE=$(du -h "$BACKUP_DIR/postgres_volume_${TIMESTAMP}.tar.gz" | cut -f1)
        print_status "PostgreSQL volume backup created: postgres_volume_${TIMESTAMP}.tar.gz ($VOLUME_SIZE)"
    else
        print_error "PostgreSQL volume backup failed!"
        exit 1
    fi
else
    print_error "PostgreSQL volume not found!"
    exit 1
fi

# Summary
echo ""
echo -e "${GREEN}🎉 Backup completed successfully!${NC}"
echo ""
echo "📋 Backup files created:"
echo "- Database: $BACKUP_DIR/database_backup_${TIMESTAMP}.sql.gz"
if [ -f "$BACKUP_DIR/media_backup_${TIMESTAMP}.tar.gz" ]; then
    echo "- Media files: $BACKUP_DIR/media_backup_${TIMESTAMP}.tar.gz"
fi
echo "- PostgreSQL volume: $BACKUP_DIR/postgres_volume_${TIMESTAMP}.tar.gz"
echo ""
echo "💾 Total backup size: $(du -sh $BACKUP_DIR | cut -f1)"
echo ""
echo "🚀 You can now safely run: sudo ./upgrade.sh"
echo ""
echo "🔄 To restore from backup (if needed):"
echo "1. Database: gunzip -c $BACKUP_DIR/database_backup_${TIMESTAMP}.sql.gz | docker compose exec -T postgres psql -U eqmd_user -d eqmd_db"
echo "2. Media: tar -xzf $BACKUP_DIR/media_backup_${TIMESTAMP}.tar.gz"
echo "3. Volume: docker run --rm -v $POSTGRES_VOLUME:/data -v $(pwd)/$BACKUP_DIR:/backup alpine tar xzf /backup/postgres_volume_${TIMESTAMP}.tar.gz -C /data"