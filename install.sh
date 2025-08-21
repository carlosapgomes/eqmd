#!/bin/bash

# EquipeMed Production First-Time Installation Script
# This script automates the complete initial deployment process

set -e # Exit on any error

echo "🚀 Starting EquipeMed production installation..."

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

# Check prerequisites
print_info "Checking prerequisites..."

if ! command -v docker &>/dev/null; then
  print_error "docker is not installed or not in PATH"
  print_info "Please install Docker first: https://docs.docker.com/engine/install/"
  exit 1
fi

if ! command -v git &>/dev/null; then
  print_error "git is not installed or not in PATH"
  print_info "Please install git first"
  exit 1
fi

print_status "Prerequisites check passed"

# Create eqmd user with conflict resolution
print_info "Setting up eqmd user..."
if [ -f "./create_eqmd_user.sh" ]; then
  source ./create_eqmd_user.sh
else
  print_error "create_eqmd_user.sh script not found"
  exit 1
fi

# Source the environment variables
if [ -f "/tmp/eqmd_user_env" ]; then
  source /tmp/eqmd_user_env
  print_status "eqmd user configured with UID:$EQMD_UID GID:$EQMD_GID"
else
  print_error "Failed to get eqmd user environment variables"
  exit 1
fi

# Create required directories and fix permissions
print_info "Creating required directories..."
mkdir -p media staticfiles
chmod 755 media staticfiles
mkdir -p /var/www/equipemed/static
chown -R $EQMD_UID:$EQMD_GID .
chown -R $EQMD_UID:$EQMD_GID /var/www/equipemed/
print_status "Directories created and permissions set"

# Check if .env file exists
if [ ! -f ".env" ]; then
  print_warning "No .env file found. Creating template..."

  # Prompt for basic configuration
  echo ""
  print_prompt "Enter your domain name (e.g., yourdomain.com): "
  read -r DOMAIN_NAME

  print_prompt "Enter your hospital name: "
  read -r HOSPITAL_NAME

  print_prompt "Enter your hospital address: "
  read -r HOSPITAL_ADDRESS

  print_prompt "Enter your hospital phone: "
  read -r HOSPITAL_PHONE

  print_prompt "Enter your hospital email: "
  read -r HOSPITAL_EMAIL

  # Generate a secure secret key
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")

  cat >.env <<EOF
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=$DOMAIN_NAME,www.$DOMAIN_NAME,localhost,127.0.0.1
HOSPITAL_NAME=$HOSPITAL_NAME
HOSPITAL_ADDRESS=$HOSPITAL_ADDRESS
HOSPITAL_PHONE=$HOSPITAL_PHONE
HOSPITAL_EMAIL=$HOSPITAL_EMAIL
HOSPITAL_PDF_FORMS_ENABLED=true
EOF

  print_status ".env file created"
  print_warning "Please review and edit .env file if needed before proceeding"

  echo ""
  print_prompt "Press Enter to continue after reviewing .env file..."
  read -r
else
  print_status "Using existing .env file"
fi

# Registry configuration (no authentication needed for public images)
print_info "Using public container registry..."
print_status "Registry configuration confirmed"

# Pull image instead of building (or build if registry not available)
print_info "Getting Docker image..."
EQMD_IMAGE="${REGISTRY:-ghcr.io/yourorg/eqmd}:${TAG:-latest}"
export EQMD_IMAGE

if docker pull "$EQMD_IMAGE" 2>/dev/null; then
    print_status "Docker image pulled from registry: $EQMD_IMAGE"
else
    print_warning "Failed to pull from registry, building locally..."
    export USER_ID=$EQMD_UID
    export GROUP_ID=$EQMD_GID
    docker compose build eqmd
    print_status "Docker image built locally"
fi

# Run database migrations
print_info "Running database migrations..."
docker compose run --rm eqmd python manage.py migrate
print_status "Database migrations completed"

# Create superuser first
echo ""
print_info "Creating superuser account..."
docker compose run --rm eqmd python manage.py createsuperuser

# Ask about sample data
echo ""
print_prompt "Do you want to load sample data? This includes sample users, patients, medical records, and templates. (y/N): "
read -r LOAD_SAMPLES

if [[ $LOAD_SAMPLES =~ ^[Yy]$ ]]; then
  print_info "Loading comprehensive sample data..."
  docker compose run --rm eqmd python manage.py populate_sample_data
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

# Start production services
print_info "Starting production services..."
docker compose up -d eqmd

print_info "Waiting for container to start..."
sleep 10

# Get container ID and copy static files
print_info "Getting container ID..."
CONTAINER_ID=$(docker compose ps -q eqmd)

if [ -z "$CONTAINER_ID" ]; then
  print_error "Container failed to start!"
  echo "Check logs with: docker compose logs eqmd"
  exit 1
fi

print_status "Container ID: $CONTAINER_ID"

# Initialize static files using init container
print_info "Initializing static files..."
if docker compose --profile init run --rm static-init; then
  print_status "Static files initialized successfully"
else
  print_warning "Static files initialization had some issues, but continuing..."
fi

# Setup groups and permissions
print_info "Setting up user groups and permissions..."
docker compose run --rm eqmd python manage.py setup_groups
print_status "Groups and permissions configured"

# Verify deployment
print_info "Verifying deployment..."

# Check container status
if docker compose ps | grep -q "Up"; then
  print_status "Container is running"
else
  print_error "Container is not running properly"
  docker compose ps
fi

# Check static files in volume
print_info "Checking static files..."
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

# Health check (if health endpoint exists)
if curl -f -s http://localhost:8778/health/ >/dev/null 2>&1; then
  print_status "Health check passed"
elif curl -f -s http://localhost:8778/ >/dev/null 2>&1; then
  print_status "Application is responding"
else
  print_warning "Application health check failed - check logs"
fi

echo ""
echo -e "${GREEN}🎉 EquipeMed installation completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Configure nginx reverse proxy (see nginx.conf.example)"
echo "2. Set up SSL certificate for your domain"
echo "3. Configure firewall to restrict direct access to port 8778"
echo "4. Test your application at: http://localhost:8778"
echo "5. Access admin interface at: http://localhost:8778/admin/"
echo "6. Static files are served from named volume: eqmd_static_files"
echo ""
echo "Useful commands:"
echo "- View logs: docker compose logs -f eqmd"
echo "- Stop service: docker compose stop eqmd"
echo "- Restart service: docker compose restart eqmd"
echo "- Update application: sudo ./upgrade.sh"
echo ""
echo "Configuration files:"
echo "- Environment: .env"
echo "- Docker: docker-compose.yml"
echo "- Static files volume: eqmd_static_files"
echo "- Static files path: $STATIC_VOLUME_PATH"
echo "- User creation: create_eqmd_user.sh"
echo "- Nginx config: nginx.conf.example"
echo ""

if [[ $LOAD_SAMPLES =~ ^[Yy]$ ]]; then
  echo -e "${BLUE}Comprehensive sample data loaded:${NC}"
  echo "- Sample users (doctors, nurses, residents, students) - password: samplepass123"
  echo "- Sample patients with admission records and medical history"
  echo "- Hospital wards, tags, and medical templates"
  echo "- Drug templates and prescription templates"
  echo "- Daily notes and outpatient prescriptions"
  echo "- Sample PDF forms for testing"
  echo ""
fi

echo -e "${YELLOW}Important security reminders:${NC}"
echo "- Never commit .env file to version control"
echo "- Set up regular database backups"
echo "- Keep Docker images updated"
echo "- Monitor application logs regularly"
echo ""
echo "For troubleshooting, see: docs/deployment/docker-production-deployment.md"

