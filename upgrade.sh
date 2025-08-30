#!/bin/bash

# EquipeMed Production Upgrade Script
# This script automates the deployment update process

set -e  # Exit on any error

echo "🚀 Starting EquipeMed production upgrade..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_prompt() {
    echo -e "${YELLOW}?${NC} $1"
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

# Source environment variables to get image name
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    
    # Generate unique static files directory based on container prefix and image name
    CONTAINER_PREFIX=${CONTAINER_PREFIX:-eqmd}
    INSTANCE_ID="${EQMD_IMAGE//[^a-zA-Z0-9]/_}"
    STATIC_FILES_PATH="/var/www/${CONTAINER_PREFIX}_static_${INSTANCE_ID}"
    print_status "Static files will be updated in: $STATIC_FILES_PATH"
else
    print_error ".env file not found - cannot determine static files path"
    exit 1
fi

# Create deployment backup
print_info "Creating deployment backup..."
BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"

# Find the eqmd service container dynamically
print_info "Finding eqmd service container..."

# List actual running containers for debugging
print_info "Currently running containers:"
docker compose ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null || docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

# Get the container ID/name for the eqmd service
ACTUAL_CONTAINER=$(docker compose ps -q eqmd 2>/dev/null | head -1)
if [ -n "$ACTUAL_CONTAINER" ]; then
    # Get the actual container name
    CONTAINER_NAME=$(docker inspect "$ACTUAL_CONTAINER" --format='{{.Name}}' | sed 's/^//' 2>/dev/null || echo "")
    CURRENT_IMAGE=$(docker inspect "$ACTUAL_CONTAINER" --format='{{.Config.Image}}' 2>/dev/null | tr -d '\n' || echo "")
    print_status "Found eqmd container: $CONTAINER_NAME"
    print_status "Current image: $CURRENT_IMAGE"
else
    print_warning "No eqmd service container found"
    CONTAINER_NAME=""
    CURRENT_IMAGE=""
fi

if [ -n "$CURRENT_IMAGE" ] && [ "$CURRENT_IMAGE" != "unknown" ]; then
    if docker tag "$CURRENT_IMAGE" "eqmd:$BACKUP_TAG" 2>/dev/null; then
        print_status "Current image backed up as eqmd:$BACKUP_TAG"
    else
        print_warning "Failed to create backup of current image"
    fi
else
    print_warning "No existing container found to backup"
fi

# Pull new image instead of building
print_info "Pulling updated Docker image..."
NEW_IMAGE="${EQMD_IMAGE:-${REGISTRY:-ghcr.io/carlosapgomes/eqmd}:${TAG:-latest}}"
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

# Update static files by copying from container to unique directory
print_info "Collecting static files in container..."
docker compose run --rm --user root eqmd python manage.py collectstatic --noinput

print_info "Copying updated static files to nginx directory..."
TEMP_CONTAINER_ID=$(docker compose run --rm -d eqmd sleep 30)
docker cp "${TEMP_CONTAINER_ID}:/app/staticfiles/." "$STATIC_FILES_PATH/"
docker stop "$TEMP_CONTAINER_ID" >/dev/null 2>&1 || true
docker rm "$TEMP_CONTAINER_ID" >/dev/null 2>&1 || true

# Fix permissions for nginx
chown -R www-data:www-data "$STATIC_FILES_PATH"
chmod -R 755 "$STATIC_FILES_PATH"
print_status "Static files updated and permissions set"

# Fix app directory permissions after update
print_info "Fixing app directory permissions after update..."
docker compose exec --user root eqmd chown -R $EQMD_UID:$EQMD_GID /app
print_status "App permissions fixed"

# Run database migrations
print_info "Running database migrations..."
docker compose exec -T eqmd python manage.py migrate --noinput
print_status "Database migrations completed"

# Configure Django Site Framework (in case environment variables changed)
print_info "Updating Django Site Framework configuration..."
docker compose exec -T eqmd python manage.py configure_django_site
print_status "Django Site Framework configuration updated"

# Check for missing infrastructure and set it up if needed
print_info "Checking for missing infrastructure setup..."

# Check and setup log directory for cronjob output
if [ ! -d "/var/log/eqmd" ]; then
    print_info "Creating missing log directory..."
    mkdir -p /var/log/eqmd
    chown eqmd:eqmd /var/log/eqmd
    chmod 755 /var/log/eqmd
    print_status "Log directory created: /var/log/eqmd"
else
    print_status "Log directory exists: /var/log/eqmd"
fi

# Check for cache management cronjobs
print_info "Checking cache management automation..."
CACHE_CRON_EXISTS=false
if crontab -u eqmd -l 2>/dev/null | grep -q "update_dashboard_stats"; then
    CACHE_CRON_EXISTS=true
    print_status "Cache management cronjobs found"
else
    print_warning "Cache management cronjobs missing"
    print_prompt "Do you want to set up automated cache management? (Y/n): "
    read -r SETUP_CACHE_CRON
    
    if [[ ! $SETUP_CACHE_CRON =~ ^[Nn]$ ]]; then
        print_info "Setting up cache management cronjobs..."
        
        # Ensure eqmd user has Docker access
        usermod -aG docker eqmd || print_warning "Could not add eqmd to docker group (may already exist)"
        
        # Create temporary cron file
        TEMP_CRON="/tmp/eqmd_cache_cron_$$"
        crontab -u eqmd -l 2>/dev/null > "$TEMP_CRON" || echo "" > "$TEMP_CRON"
        
        # Add cache management jobs
        cat >> "$TEMP_CRON" << EOF

# EquipeMed Dashboard Cache Management (added by upgrade.sh)
# Improves dashboard performance by pre-computing statistics every 5 minutes

# Dashboard stats - runs every 5 minutes
*/5 * * * * cd $(pwd) && docker compose exec -T eqmd python manage.py update_dashboard_stats >> /var/log/eqmd/dashboard_cache.log 2>&1

# Ward mapping - runs every 5 minutes (offset by 2 minutes)
2-59/5 * * * * cd $(pwd) && docker compose exec -T eqmd python manage.py update_ward_mapping_cache >> /var/log/eqmd/ward_cache.log 2>&1
EOF
        
        if crontab -u eqmd "$TEMP_CRON"; then
            print_status "Cache management cronjobs installed"
            CACHE_CRON_EXISTS=true
        else
            print_error "Failed to install cache cronjobs"
        fi
        
        rm -f "$TEMP_CRON"
    fi
fi

# Check for user lifecycle management cronjobs  
print_info "Checking user lifecycle management automation..."
LIFECYCLE_CRON_EXISTS=false
if crontab -u eqmd -l 2>/dev/null | grep -q "check_user_expiration"; then
    LIFECYCLE_CRON_EXISTS=true
    print_status "User lifecycle cronjobs found"
else
    print_warning "User lifecycle cronjobs missing"
    
    # Check if lifecycle commands are available
    if docker compose exec -T eqmd python manage.py help | grep -q "check_user_expiration"; then
        print_prompt "Do you want to set up automated user lifecycle management? (Y/n): "
        read -r SETUP_LIFECYCLE_CRON
        
        if [[ ! $SETUP_LIFECYCLE_CRON =~ ^[Nn]$ ]]; then
            print_info "Setting up user lifecycle management cronjobs..."
            
            # Create temporary cron file
            TEMP_CRON="/tmp/eqmd_lifecycle_cron_$$"
            crontab -u eqmd -l 2>/dev/null > "$TEMP_CRON" || echo "" > "$TEMP_CRON"
            
            # Add lifecycle management jobs
            cat >> "$TEMP_CRON" << EOF

# EquipeMed User Lifecycle Management (added by upgrade.sh)
# Automated expiration checking and notifications

# Daily expiration check (6:00 AM)
0 6 * * * cd $(pwd) && /usr/bin/flock -n /tmp/check_expiration.lock docker compose exec -T eqmd python manage.py check_user_expiration >> /var/log/eqmd/expiration_check.log 2>&1

# Daily notifications (8:00 AM)
0 8 * * * cd $(pwd) && /usr/bin/flock -n /tmp/send_notifications.lock docker compose exec -T eqmd python manage.py send_expiration_notifications >> /var/log/eqmd/notifications.log 2>&1

# Weekly reports (Sundays 7:00 AM)
0 7 * * 0 cd $(pwd) && docker compose exec -T eqmd python manage.py lifecycle_report --output-file /tmp/lifecycle_report_\$(date +%Y%m%d).csv >> /var/log/eqmd/reports.log 2>&1
EOF
            
            if crontab -u eqmd "$TEMP_CRON"; then
                print_status "User lifecycle cronjobs installed"
                LIFECYCLE_CRON_EXISTS=true
            else
                print_error "Failed to install lifecycle cronjobs"
            fi
            
            rm -f "$TEMP_CRON"
            
            # Test lifecycle system
            print_info "Testing lifecycle system..."
            if docker compose exec -T eqmd python manage.py check_user_expiration --dry-run >/dev/null 2>&1; then
                print_status "Lifecycle system test passed"
            else
                print_warning "Lifecycle system test failed - check manually"
            fi
        fi
    else
        print_info "User lifecycle commands not available in this version"
    fi
fi

# Initialize caches if cronjobs were just set up
if [[ $CACHE_CRON_EXISTS == true ]]; then
    print_info "Initializing cache data..."
    docker compose exec -T eqmd python manage.py update_dashboard_stats >/dev/null 2>&1 || print_warning "Dashboard cache init failed"
    docker compose exec -T eqmd python manage.py update_ward_mapping_cache >/dev/null 2>&1 || print_warning "Ward cache init failed"
fi

print_status "Infrastructure check completed"

# Wait and verify health with rollback capability
print_info "Waiting for health check..."
HOST_PORT=${HOST_PORT:-8778}
for i in {1..30}; do
    if curl -f -s http://localhost:$HOST_PORT/health/ >/dev/null; then
        print_status "Health check passed"
        HEALTH_CHECK_PASSED=true
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Health check failed - rolling back"
        if [ -n "$CURRENT_IMAGE" ] && [ "$CURRENT_IMAGE" != "unknown" ]; then
            if docker tag "eqmd:$BACKUP_TAG" eqmd:latest 2>/dev/null && docker compose up -d eqmd; then
                print_warning "Rolled back to previous version"
            else
                print_error "Rollback failed - manual intervention required"
            fi
        else
            print_error "No backup available - manual intervention required"
        fi
        exit 1
    fi
    sleep 2
done

print_status "Checking if PWA files are accessible..."
if [ -f "$STATIC_FILES_PATH/manifest.json" ]; then
    print_status "manifest.json found in static directory"
else
    print_warning "manifest.json not found in static directory"
fi

if [ -f "$STATIC_FILES_PATH/sw.js" ]; then
    print_status "sw.js found in static directory"
else
    print_warning "sw.js not found in static directory"
fi

echo ""
echo -e "${GREEN}🎉 Upgrade completed!${NC}"
echo ""

# Show what infrastructure was set up
if [[ $CACHE_CRON_EXISTS == true ]] || [[ $LIFECYCLE_CRON_EXISTS == true ]]; then
    echo -e "${BLUE}📋 Infrastructure configured during upgrade:${NC}"
    if [[ $CACHE_CRON_EXISTS == true ]]; then
        echo "✓ Dashboard cache management (performance optimization)"
    fi
    if [[ $LIFECYCLE_CRON_EXISTS == true ]]; then
        echo "✓ User lifecycle management (automated expiration checking)"
    fi
    echo "- Log directory: /var/log/eqmd/"
    echo "- Cronjobs installed for user: eqmd"
    echo ""
fi

echo "Next steps:"
echo "1. Test your application at your domain"
echo "2. Check PWA functionality (install button)"
echo "3. Monitor logs: docker compose logs -f eqmd"
if [[ $CACHE_CRON_EXISTS == true ]] || [[ $LIFECYCLE_CRON_EXISTS == true ]]; then
    echo "4. Check automation logs: ls -la /var/log/eqmd/"
fi
echo ""
echo "If there are issues:"
echo "- Check container logs: docker compose logs eqmd"
echo "- Check nginx logs: journalctl -u nginx"
echo "- Verify static files: ls -la $STATIC_FILES_PATH"
if [[ $CACHE_CRON_EXISTS == true ]] || [[ $LIFECYCLE_CRON_EXISTS == true ]]; then
    echo "- Check cronjobs: crontab -u eqmd -l"
fi
echo "- Rollback if needed: docker tag eqmd:$BACKUP_TAG eqmd:latest && docker compose up -d eqmd"
echo ""

echo "Useful commands:"
echo "- Application logs: docker compose logs -f eqmd"
if [[ $CACHE_CRON_EXISTS == true ]]; then
    echo "- Cache status: docker compose exec eqmd python manage.py check_cache_health"
fi
if [[ $LIFECYCLE_CRON_EXISTS == true ]]; then
    echo "- Lifecycle status: docker compose exec eqmd python manage.py check_user_expiration --dry-run"
fi
echo ""

echo "Backup information:"
if [ -n "$CURRENT_IMAGE" ] && [ "$CURRENT_IMAGE" != "unknown" ]; then
    echo "- Backup tag: $BACKUP_TAG (from: $CURRENT_IMAGE)"
else
    echo "- Backup tag: $BACKUP_TAG (no backup created - fresh install)"
fi
echo "- New image: ${EQMD_IMAGE:-built-locally}"
echo "- Static files directory: $STATIC_FILES_PATH"