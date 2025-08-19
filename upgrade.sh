#!/bin/bash

# EquipeMed Production Upgrade Script
# This script automates the deployment update process

set -e  # Exit on any error

echo "🚀 Starting EquipeMed production upgrade..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

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

# Check if eqmd user exists
if ! id eqmd &> /dev/null; then
    print_error "eqmd user does not exist. Please create it first:"
    echo "sudo useradd --system --no-create-home --shell /usr/sbin/nologin eqmd"
    exit 1
fi

# Get eqmd user ID and group ID
EQMD_UID=$(id -u eqmd)
EQMD_GID=$(id -g eqmd)
print_status "Found eqmd user with UID:$EQMD_UID GID:$EQMD_GID"

# Create deployment backup
print_info "Creating deployment backup..."
BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"
CURRENT_IMAGE=$(docker inspect eqmd-eqmd-1 --format='{{.Config.Image}}' 2>/dev/null || echo "unknown")
if [ "$CURRENT_IMAGE" != "unknown" ]; then
    docker tag "$CURRENT_IMAGE" "eqmd:$BACKUP_TAG"
    print_status "Current image backed up as eqmd:$BACKUP_TAG"
fi

# Pull new image instead of building
print_info "Pulling updated Docker image..."
NEW_IMAGE="${REGISTRY:-ghcr.io/yourorg/eqmd}:${TAG:-latest}"
if docker pull "$NEW_IMAGE"; then
    export EQMD_IMAGE="$NEW_IMAGE"
    print_status "Docker image pulled: $NEW_IMAGE"
else
    print_warning "Failed to pull from registry, building locally..."
    docker compose build eqmd
    print_status "Docker image built locally"
fi

print_status "Performing graceful update..."
docker compose up -d eqmd

print_status "Waiting for container to start..."
sleep 10

print_status "Getting container ID..."
CONTAINER_ID=$(docker compose ps -q eqmd)

if [ -z "$CONTAINER_ID" ]; then
    print_error "Container failed to start!"
    echo "Check logs with: docker compose logs eqmd"
    exit 1
fi

print_status "Container ID: $CONTAINER_ID"

# Update static files using init container
print_status "Updating static files..."
if docker compose --profile init run --rm static-init; then
    print_status "Static files updated successfully"
else
    print_warning "Static files update had some issues, but continuing..."
fi

# Wait and verify health with rollback capability
print_info "Waiting for health check..."
for i in {1..30}; do
    if curl -f -s http://localhost:8778/health/ >/dev/null; then
        print_status "Health check passed"
        HEALTH_CHECK_PASSED=true
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Health check failed - rolling back"
        if [ "$CURRENT_IMAGE" != "unknown" ]; then
            docker tag "eqmd:$BACKUP_TAG" eqmd:latest
            docker compose up -d eqmd
            print_warning "Rolled back to previous version"
        fi
        exit 1
    fi
    sleep 2
done

print_status "Checking if PWA files are accessible..."
STATIC_VOLUME_PATH="/var/lib/docker/volumes/eqmd_static_files/_data"
if [ -f "$STATIC_VOLUME_PATH/manifest.json" ]; then
    print_status "manifest.json found in volume"
else
    print_warning "manifest.json not found in volume"
fi

if [ -f "$STATIC_VOLUME_PATH/sw.js" ]; then
    print_status "sw.js found in volume"
else
    print_warning "sw.js not found in volume"
fi

echo ""
echo -e "${GREEN}🎉 Upgrade completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Test your application at your domain"
echo "2. Check PWA functionality (install button)"
echo "3. Monitor logs: docker compose logs -f eqmd"
echo ""
echo "If there are issues:"
echo "- Check container logs: docker compose logs eqmd"
echo "- Check nginx logs: journalctl -u nginx"
echo "- Verify static files: ls -la $STATIC_VOLUME_PATH"
echo "- Rollback if needed: docker tag eqmd:$BACKUP_TAG eqmd:latest && docker compose up -d eqmd"
echo ""
echo "Backup information:"
echo "- Backup tag: $BACKUP_TAG"
echo "- New image: ${EQMD_IMAGE:-built-locally}"
echo "- Static files volume: eqmd_static_files"