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

print_status "Building new Docker image..."
docker compose build eqmd

print_status "Stopping current container..."
docker compose stop eqmd

print_status "Fixing permissions before starting container (setting to eqmd user)..."
mkdir -p /var/www/equipemed/static
chown -R $EQMD_UID:$EQMD_GID /var/www/equipemed/

print_status "Starting updated container..."
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

print_status "Manually copying static files..."
if docker exec $CONTAINER_ID sh -c "cp -rv /app/staticfiles/* /var/www/equipemed/static/"; then
    print_status "Static files copied successfully"
else
    print_warning "Static files copy had some issues, but continuing..."
fi

print_status "Fixing static files permissions for nginx..."
chown -R www-data:www-data /var/www/equipemed/
chmod -R 755 /var/www/equipemed/

print_status "Verifying deployment..."
if curl -f -s http://localhost:8778/health/ > /dev/null; then
    print_status "Health check passed"
else
    print_warning "Health check failed - check application logs"
fi

print_status "Checking if PWA files are accessible..."
if [ -f "/var/www/equipemed/static/manifest.json" ]; then
    print_status "manifest.json found"
else
    print_warning "manifest.json not found"
fi

if [ -f "/var/www/equipemed/static/sw.js" ]; then
    print_status "sw.js found"
else
    print_warning "sw.js not found"
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
echo "- Verify static files: ls -la /var/www/equipemed/static/"