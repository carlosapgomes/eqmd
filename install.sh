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

# Create eqmd user if it doesn't exist
if ! id eqmd &>/dev/null; then
  print_info "Creating eqmd system user..."
  useradd --system --no-create-home --shell /usr/sbin/nologin eqmd
  print_status "eqmd user created"
else
  print_status "eqmd user already exists"
fi

# Get eqmd user ID and group ID
EQMD_UID=$(id -u eqmd)
EQMD_GID=$(id -g eqmd)
print_status "Found eqmd user with UID:$EQMD_UID GID:$EQMD_GID"

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

# Set environment variables for Docker build
export USER_ID=$EQMD_UID
export GROUP_ID=$EQMD_GID

# Build Docker image
print_info "Building Docker image..."
docker compose build eqmd
print_status "Docker image built successfully"

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

# Copy static files
print_info "Copying static files..."
if docker exec $CONTAINER_ID sh -c "cp -rv /app/staticfiles/* /var/www/equipemed/static/"; then
  print_status "Static files copied successfully"
else
  print_warning "Static files copy had some issues, but continuing..."
fi

# Fix static files permissions for nginx
print_info "Fixing static files permissions for nginx..."
chown -R www-data:www-data /var/www/equipemed/
chmod -R 755 /var/www/equipemed/
print_status "Permissions set for nginx"

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

# Check PWA files
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
echo "1. Configure nginx reverse proxy (see docs/deployment/docker-production-deployment.md)"
echo "2. Set up SSL certificate for your domain"
echo "3. Configure firewall to restrict direct access to port 8778"
echo "4. Test your application at: http://localhost:8778"
echo "5. Access admin interface at: http://localhost:8778/admin/"
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
echo "- Static files: /var/www/equipemed/static/"
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

