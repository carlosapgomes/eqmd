#!/bin/bash
# Setup Matrix directory permissions following EquipeMed patterns
# Similar to create_eqmd_user.sh but for development Matrix setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info "Setting up Matrix directory permissions for development..."

# Get current user info
CURRENT_USER=$(whoami)
CURRENT_UID=$(id -u)
CURRENT_GID=$(id -g)

print_info "Current user: $CURRENT_USER (UID:$CURRENT_UID GID:$CURRENT_GID)"

# Check if we have sudo access
if ! sudo -n true 2>/dev/null; then
    print_error "This script requires sudo access to fix permissions"
    echo "Please run: sudo ./scripts/setup_matrix_permissions.sh"
    exit 1
fi

# Stop matrix services if running
print_info "Stopping Matrix services..."
sudo docker compose stop matrix-synapse element-web 2>/dev/null || true

# Remove problematic files and directories
print_info "Cleaning up auto-generated files..."
sudo rm -rf matrix/signing.key matrix/*.log.config matrix/media_store

# Fix ownership of matrix directory to current user
print_info "Fixing matrix directory ownership..."
sudo chown -R $CURRENT_UID:$CURRENT_GID matrix/

# Create required directories with correct ownership
print_info "Creating required directories..."
mkdir -p matrix/logs
chmod 755 matrix matrix/logs

print_status "Matrix directory permissions fixed"
print_info "Matrix directory is now owned by: $CURRENT_USER (UID:$CURRENT_UID GID:$CURRENT_GID)"
print_info "Synapse container will run as the same user via docker-compose.yml user directive"

echo ""
print_info "Next steps:"
echo "1. Generate signing key: docker run --rm -v \$(pwd)/matrix:/data -u $CURRENT_UID:$CURRENT_GID -e SYNAPSE_SERVER_NAME=matrix.sispep.com -e SYNAPSE_REPORT_STATS=no matrixdotorg/synapse:v1.99.0 generate"
echo "2. Start services: docker compose up -d matrix-synapse element-web"