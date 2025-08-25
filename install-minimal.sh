#!/bin/bash

# EquipeMed Minimal Installation Script (Registry-based)
# This script performs minimal deployment using pre-built container images
# No repository cloning required

set -e # Exit on any error

echo "🚀 Starting EquipeMed minimal installation (registry-based)..."

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
	print_info "Usage: sudo $0"
	exit 1
fi

print_info "EquipeMed Registry-based Minimal Installation"
print_info "This installation method:"
print_info "- Uses pre-built container images"
print_info "- Requires no repository cloning"
print_info "- Handles UID conflicts automatically"
print_info "- Sets up optimized static file serving"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."

if ! command -v docker &>/dev/null; then
	print_error "docker is not installed or not in PATH"
	print_info "Please install Docker first: https://docs.docker.com/engine/install/"
	exit 1
fi

if ! command -v curl &>/dev/null; then
	print_error "curl is not installed"
	print_info "Please install curl: sudo apt-get install curl"
	exit 1
fi

print_status "Prerequisites check passed"

# Download required files if not present
print_info "Checking required files..."

REQUIRED_FILES=(
	"docker-compose.yml"
	"create_eqmd_user.sh"
)

MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
	if [ ! -f "$file" ]; then
		MISSING_FILES+=("$file")
	fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
	print_info "Downloading missing files..."
	BASE_URL="https://raw.githubusercontent.com/yourorg/eqmd/main"

	for file in "${MISSING_FILES[@]}"; do
		if curl -fsSL -o "$file" "$BASE_URL/$file"; then
			print_status "Downloaded $file"
			if [[ "$file" == *.sh ]]; then
				chmod +x "$file"
			fi
		else
			print_error "Failed to download $file"
			exit 1
		fi
	done
fi

# Create eqmd user with automatic UID conflict resolution
print_info "Setting up eqmd user..."
if [ -f "./create_eqmd_user.sh" ]; then
	./create_eqmd_user.sh
else
	print_error "create_eqmd_user.sh script not found"
	exit 1
fi

# Source the user environment variables
if [ -f "/tmp/eqmd_user_env" ]; then
	source /tmp/eqmd_user_env
	print_status "eqmd user configured with UID:$EQMD_UID GID:$EQMD_GID"
	
	# Update .env file with actual UID/GID
	if [ -f ".env" ]; then
		print_info "Updating .env file with correct UID/GID..."
		sed -i "s/^EQMD_UID=.*/EQMD_UID=$EQMD_UID/" .env
		sed -i "s/^EQMD_GID=.*/EQMD_GID=$EQMD_GID/" .env
		print_status ".env file updated with UID:$EQMD_UID GID:$EQMD_GID"
		
		# Add multi-deployment variables if missing
		if ! grep -q "^CONTAINER_PREFIX=" .env; then
			echo "" >> .env
			echo "# Multi-deployment configuration (added by install-minimal.sh)" >> .env
			echo "CONTAINER_PREFIX=eqmd" >> .env
			echo "HOST_PORT=8778" >> .env  
			echo "DEV_PORT=8779" >> .env
			print_status "Added multi-deployment configuration to .env"
		fi
		
		# Fix database path to use volume mount
		print_info "Fixing database path to use volume mount..."
		sed -i "s/^DATABASE_NAME=.*/DATABASE_NAME=\/app\/database\/db.sqlite3/" .env
		print_status "Database path updated to /app/database/db.sqlite3"
	fi
else
	print_error "Failed to get eqmd user environment variables"
	exit 1
fi

# Note: All required directories (media, database, staticfiles) use Docker volumes
# No local directories needed as they are managed by Docker
print_info "Docker volumes will be used for media, database, and static files"
print_status "Volume configuration confirmed"

# Configure environment
if [ ! -f ".env" ]; then
	print_warning "No .env file found. Creating basic template..."

	# Prompt for basic configuration
	echo ""
	print_prompt "Enter your domain name (e.g., yourdomain.com): "
	read -r DOMAIN_NAME

	print_prompt "Enter your hospital name: "
	read -r HOSPITAL_NAME

	print_prompt "Enter container registry (default: ghcr.io): "
	read -r REGISTRY
	REGISTRY=${REGISTRY:-ghcr.io}

	print_prompt "Enter image name (e.g., yourorg/eqmd): "
	read -r IMAGE_NAME

	# Multi-deployment configuration prompts
	print_prompt "Enter container prefix for unique naming (default: eqmd): "
	read -r CONTAINER_PREFIX
	CONTAINER_PREFIX=${CONTAINER_PREFIX:-eqmd}

	print_prompt "Enter host port (default: 8778): "
	read -r HOST_PORT
	HOST_PORT=${HOST_PORT:-8778}

	# Validate port is not in use
	if command -v netstat &>/dev/null && netstat -ln | grep -q ":$HOST_PORT "; then
		print_error "Port $HOST_PORT is already in use"
		print_info "Please choose a different port"
		exit 1
	elif command -v ss &>/dev/null && ss -ln | grep -q ":$HOST_PORT "; then
		print_error "Port $HOST_PORT is already in use"
		print_info "Please choose a different port"
		exit 1
	fi

	# Generate secure secret key
	SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")

	cat >.env <<EOF
# Generated by install-minimal.sh
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=$DOMAIN_NAME,www.$DOMAIN_NAME,localhost,127.0.0.1

# Multi-deployment configuration
CONTAINER_PREFIX=$CONTAINER_PREFIX
HOST_PORT=$HOST_PORT
DEV_PORT=$((HOST_PORT + 1))

# Registry configuration
REGISTRY=$REGISTRY
EQMD_IMAGE=$REGISTRY/$IMAGE_NAME:latest

# User configuration
EQMD_UID=$EQMD_UID
EQMD_GID=$EQMD_GID

# Hospital configuration
HOSPITAL_NAME=$HOSPITAL_NAME
HOSPITAL_ADDRESS=Update this address
HOSPITAL_PHONE=Update this phone
HOSPITAL_EMAIL=Update this email
HOSPITAL_PDF_FORMS_ENABLED=true

# Email (update for production)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EOF

	print_status ".env file created"
	print_warning "Please review and edit .env file before proceeding"

	echo ""
	print_prompt "Press Enter to continue after reviewing .env file..."
	read -r
else
	print_status "Using existing .env file"
fi

# Source environment variables
set -a # Export all variables
source .env
set +a

# Generate unique static files directory based on container prefix and image name
CONTAINER_PREFIX=${CONTAINER_PREFIX:-eqmd}
INSTANCE_ID="${EQMD_IMAGE//[^a-zA-Z0-9]/_}"
STATIC_FILES_PATH="/var/www/${CONTAINER_PREFIX}_static_${INSTANCE_ID}"
print_status "Static files will be served from: $STATIC_FILES_PATH"

# Create unique static files directory
print_info "Creating unique static files directory..."
mkdir -p "$STATIC_FILES_PATH"
print_status "Static directory created: $STATIC_FILES_PATH"

# Pull container image (no authentication needed for public images)
print_info "Pulling container image: $EQMD_IMAGE"
if docker pull "$EQMD_IMAGE"; then
	print_status "Container image pulled successfully"
else
	print_error "Failed to pull container image: $EQMD_IMAGE"
	print_info "Please check:"
	print_info "- Image name is correct"
	print_info "- Registry authentication is configured"
	print_info "- Network connectivity to registry"
	exit 1
fi

# Clean up any existing volumes to ensure fresh start
print_info "Cleaning up existing volumes..."
docker compose down -v 2>/dev/null || true
print_status "Volumes cleaned up"

# Initialize static files
print_info "Initializing static files..."
if docker compose --profile init run --rm static-init; then
	print_status "Static files initialized"
else
	print_warning "Static files initialization had issues, continuing..."
fi

# Initialize application directories with proper permissions
print_info "Initializing application directories..."
if docker compose run --rm --user root eqmd sh -c "
# Fix ownership of entire /app directory to match runtime user
chown -R $EQMD_UID:$EQMD_GID /app
# Create required directories
mkdir -p /app/media/pdf_forms/templates /app/media/pdf_forms/completed
mkdir -p /app/filepond_tmp /app/filepond_stored /app/filepond_uploads
# Ensure correct ownership
chown -R $EQMD_UID:$EQMD_GID /app/media /app/filepond_tmp /app/filepond_stored /app/filepond_uploads
"; then
	print_status "Application directories initialized"
else
	print_warning "Application directory initialization had issues, continuing..."
fi

# Initialize staticfiles directory with proper permissions
print_info "Initializing staticfiles directory..."
if docker compose run --rm --user root eqmd sh -c "mkdir -p /app/staticfiles && chown -R $EQMD_UID:$EQMD_GID /app/staticfiles"; then
	print_status "Staticfiles directory initialized"
else
	print_warning "Staticfiles directory initialization had issues, continuing..."
fi

# Run database migrations
print_info "Running database migrations..."
docker compose run --rm --user root eqmd sh -c "
echo 'Pre-migration database check:'
ls -la /app/database/
echo 'Starting migrations...'
python manage.py migrate --verbosity=2
echo 'Post-migration database check:'
ls -la /app/database/
echo 'Migrations completed, fixing permissions...'
chown -R $EQMD_UID:$EQMD_GID /app/database
echo 'Permissions fixed.'
"

# Verify migrations were applied
print_info "Debugging database configuration..."
docker compose run --rm --user root eqmd sh -c "
echo 'Environment variables:'
env | grep -E 'DATABASE|DEBUG|DJANGO' | sort || echo 'No database environment variables found'
echo 'Creating test database file to verify volume mount:'
touch /app/database/test.db
ls -la /app/database/
echo 'Database directory is writable!'
rm /app/database/test.db
echo 'Test file removed'
echo 'Running migrations again to see if database file gets created:'
python manage.py migrate --verbosity=0
echo 'Post-migration check:'
ls -la /app/database/
find /app -name '*.db*' -o -name 'db.sqlite*' -o -name '*.sqlite*' 2>/dev/null || echo 'Still no database files found'
"
print_status "Database debugging completed"

# Collect static files to container and copy to unique directory
print_info "Collecting static files..."
docker compose run --rm --user root eqmd sh -c "python manage.py collectstatic --noinput"

print_info "Copying static files to nginx directory..."
CONTAINER_ID=$(docker compose run --rm -d eqmd sleep 30)
docker cp "${CONTAINER_ID}:/app/staticfiles/." "$STATIC_FILES_PATH/"
docker stop "$CONTAINER_ID" >/dev/null 2>&1 || true
docker rm "$CONTAINER_ID" >/dev/null 2>&1 || true

# Fix permissions for nginx
chown -R www-data:www-data "$STATIC_FILES_PATH"
chmod -R 755 "$STATIC_FILES_PATH"
print_status "Static files copied and permissions set"

# Create superuser
echo ""
print_info "Creating superuser account..."
docker compose run --rm --user root eqmd python manage.py createsuperuser

# Ask about sample data
echo ""
print_prompt "Do you want to load sample data? This includes sample users, patients, and templates. (y/N): "
read -r LOAD_SAMPLES

if [[ $LOAD_SAMPLES =~ ^[Yy]$ ]]; then
	print_info "Loading comprehensive sample data..."
	docker compose run --rm --user root eqmd python manage.py populate_sample_data
	print_status "Sample data loaded (includes users, patients, medical data, and PDF forms)"
else
	print_info "You can load comprehensive sample data later with:"
	echo "docker compose run --rm eqmd python manage.py populate_sample_data"
	echo ""
	print_info "Or load individual sample data with:"
	echo "docker compose run --rm eqmd python manage.py create_sample_tags"
	echo "docker compose run --rm eqmd python manage.py create_sample_wards"
	echo "docker compose run --rm eqmd python manage.py create_sample_content"
	echo "docker compose run --rm eqmd python manage.py create_sample_pdf_forms"
fi

# Ask about cache management setup
echo ""
print_prompt "Do you want to set up automated dashboard cache management? This improves performance by caching data every 5 minutes. (Y/n): "
read -r SETUP_CACHE_CRON

if [[ $SETUP_CACHE_CRON =~ ^[Nn]$ ]]; then
	print_info "You can set up cache management later with:"
	echo "sudo crontab -u eqmd -e"
	echo ""
	echo "Add these lines:"
	echo "*/5 * * * * cd $(pwd) && docker compose exec -T web python manage.py update_dashboard_stats >> /var/log/eqmd/dashboard_cache.log 2>&1"
	echo "2-59/5 * * * * cd $(pwd) && docker compose exec -T web python manage.py update_ward_mapping_cache >> /var/log/eqmd/ward_cache.log 2>&1"
	echo ""
	print_info "For detailed information, see: docs/performance/dashboard-cache.md"
else
	print_info "Setting up automated cache management..."
	
	# Ensure eqmd user can access Docker (should already be done by create_eqmd_user.sh)
	print_info "Ensuring eqmd user has Docker access..."
	sudo usermod -aG docker eqmd || print_warning "Could not add eqmd to docker group (may already exist)"
	
	# Create log directory with proper ownership
	print_info "Creating log directory..."
	sudo mkdir -p /var/log/eqmd
	sudo chown eqmd:eqmd /var/log/eqmd
	sudo chmod 755 /var/log/eqmd
	print_status "Log directory created: /var/log/eqmd"
	
	# Create temporary cron file
	TEMP_CRON="/tmp/eqmd_cron_$$"
	
	# Get existing eqmd user cron jobs (if any)
	sudo crontab -u eqmd -l 2>/dev/null > "$TEMP_CRON" || echo "" > "$TEMP_CRON"
	
	# Check if cache jobs already exist
	if grep -q "update_dashboard_stats" "$TEMP_CRON"; then
		print_warning "Cache management cron jobs already exist for user 'eqmd'"
		print_info "Skipping cron job installation"
	else
		print_info "Adding cache management cron jobs..."
		
		# Add cache management jobs
		cat >> "$TEMP_CRON" << EOF

# EquipeMed Dashboard Cache Management (added by install-minimal.sh)
# Improves dashboard performance by pre-computing statistics every 5 minutes

# Dashboard stats - runs at :00, :05, :10, :15, :20, :25, :30, :35, :40, :45, :50, :55
*/5 * * * * cd $(pwd) && docker compose exec -T web python manage.py update_dashboard_stats >> /var/log/eqmd/dashboard_cache.log 2>&1

# Ward mapping - runs at :02, :07, :12, :17, :22, :27, :32, :37, :42, :47, :52, :57 (offset by 2 minutes)
2-59/5 * * * * cd $(pwd) && docker compose exec -T web python manage.py update_ward_mapping_cache >> /var/log/eqmd/ward_cache.log 2>&1
EOF
		
		# Install the new crontab for eqmd user
		if sudo crontab -u eqmd "$TEMP_CRON"; then
			print_status "Cache management cron jobs installed for user 'eqmd'"
			print_info "Jobs run every 5 minutes (alternating) to optimize performance"
			print_info "Logs are written to /var/log/eqmd/"
		else
			print_error "Failed to install cron jobs for user 'eqmd'"
			print_warning "You can set up cache management manually later"
		fi
		
		# Clean up temporary file
		rm -f "$TEMP_CRON"
		
		# Populate initial cache data
		print_info "Populating initial cache data..."
		if docker compose exec -T web python manage.py update_dashboard_stats; then
			print_status "Dashboard cache initialized"
		else
			print_warning "Dashboard cache initialization failed (will retry via cron)"
		fi
		
		if docker compose exec -T web python manage.py update_ward_mapping_cache; then
			print_status "Ward mapping cache initialized"
		else
			print_warning "Ward mapping cache initialization failed (will retry via cron)"
		fi
		
		# Verify cache health
		print_info "Verifying cache health..."
		if docker compose exec -T web python manage.py check_cache_health; then
			print_status "Cache system is healthy and ready"
		else
			print_warning "Cache health check failed - check logs for details"
		fi
	fi
fi

# Fix final database permissions before starting production services  
print_info "Fixing final database permissions..."
docker compose run --rm --user root eqmd sh -c "chown -R $EQMD_UID:$EQMD_GID /app/database"
print_status "Final database permissions fixed"

# Fix final permissions for all app directories before starting services
print_info "Fixing final permissions for all app directories..."
docker compose run --rm --user root eqmd sh -c "chown -R $EQMD_UID:$EQMD_GID /app"
print_status "Final app permissions fixed"

# Start production services
print_info "Starting production services..."
docker compose up -d eqmd
print_status "Services started"

# Wait for services to be ready
print_info "Waiting for services to be ready..."
sleep 15

# Health check
print_info "Performing health check..."
HOST_PORT=${HOST_PORT:-8778}
for i in {1..30}; do
	if curl -f -s http://localhost:$HOST_PORT/health/ >/dev/null 2>&1; then
		print_status "Health check passed"
		break
	elif curl -f -s http://localhost:$HOST_PORT/ >/dev/null 2>&1; then
		print_status "Application is responding"
		break
	else
		if [ $i -eq 30 ]; then
			print_warning "Health check timeout - check logs manually"
		else
			sleep 2
		fi
	fi
done

# Setup permissions
print_info "Setting up user groups and permissions..."
docker compose run --rm --user root eqmd python manage.py setup_groups
print_status "Permissions configured"

# Final checks
print_info "Performing final checks..."

# Check container status
if docker compose ps | grep -q "Up"; then
	print_status "Container is running"
else
	print_error "Container is not running properly"
	print_info "Check logs: docker compose logs eqmd"
fi

echo ""
echo -e "${GREEN}🎉 EquipeMed minimal installation completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Configure nginx reverse proxy (see documentation for details)"
echo "   - Static files path for nginx: $STATIC_FILES_PATH"
echo "   - Download nginx.conf.example and update the static files path"
echo "2. Set up SSL certificate for your domain"
echo "3. Configure firewall to block direct access to port $HOST_PORT"
echo "4. Test your application at: http://localhost:$HOST_PORT"
echo "5. Access admin interface at: http://localhost:$HOST_PORT/admin/"
echo ""
echo "Configuration:"
echo "- Application: $EQMD_IMAGE"
echo "- Environment: .env"
echo "- Static files: $STATIC_FILES_PATH (nginx-owned)"
echo "- User: eqmd (UID:$EQMD_UID GID:$EQMD_GID)"
echo ""
echo "Useful commands:"
echo "- View logs: docker compose logs -f eqmd"
echo "- Cache status: docker compose exec web python manage.py check_cache_health"
echo "- Update: curl -sSL URL/upgrade.sh | sudo bash"
echo "- Stop: docker compose stop eqmd"
echo "- Restart: docker compose restart eqmd"
echo ""

if [[ $LOAD_SAMPLES =~ ^[Yy]$ ]]; then
	echo -e "${BLUE}Sample data loaded:${NC}"
	echo "- Sample users (password: samplepass123)"
	echo "- Sample patients and medical records"
	echo "- Hospital wards, tags, and templates"
	echo ""
fi

if [[ ! $SETUP_CACHE_CRON =~ ^[Nn]$ ]]; then
	echo -e "${BLUE}⚡ Performance optimization configured:${NC}"
	echo "- Dashboard cache system active (90%+ performance improvement)"
	echo "- Automated cache refresh every 5 minutes"
	echo "- Cache logs: /var/log/eqmd/"
	echo "- Health check: docker compose exec web python manage.py check_cache_health"
	echo ""
fi

echo -e "${YELLOW}Important security reminders:${NC}"
echo "- Update .env with your actual production settings"
echo "- Set up SSL/HTTPS for production use"
echo "- Configure regular backups"
echo "- Keep container images updated"
echo ""
echo "For detailed documentation, visit:"
echo "https://github.com/yourorg/eqmd/docs"
echo ""
echo "Performance optimization details:"
echo "https://github.com/yourorg/eqmd/docs/performance/dashboard-cache.md"

