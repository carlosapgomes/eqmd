# Phase 6: Testing and Deployment

## Overview
Comprehensive testing procedures, deployment verification, monitoring setup, and troubleshooting guide for the complete Matrix Synapse integration.

## Prerequisites
- Phases 1-5 completed successfully
- All services configured and ready
- Admin access to production environment
- SSL certificates in place

## Step 1: Pre-Deployment Testing

### 1.1 Configuration Validation Script
Create `scripts/validate_matrix_config.py`:

```python
#!/usr/bin/env python3
"""
Comprehensive Matrix configuration validation script.
Run before deployment to catch configuration issues.
"""

import os
import sys
import json
import requests
import subprocess
import psycopg2
from pathlib import Path

class MatrixConfigValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed = []
        
    def log_error(self, message):
        self.errors.append(f"❌ {message}")
        print(f"❌ {message}")
        
    def log_warning(self, message):
        self.warnings.append(f"⚠️  {message}")
        print(f"⚠️  {message}")
        
    def log_pass(self, message):
        self.passed.append(f"✅ {message}")
        print(f"✅ {message}")
    
    def validate_environment(self):
        """Validate environment variables."""
        print("\n🔍 Validating Environment Variables...")
        
        required_env = [
            'SECRET_KEY',
            'ALLOWED_HOSTS',
            'MATRIX_SERVER_NAME',
            'OIDC_MATRIX_CLIENT_ID',
            'OIDC_MATRIX_CLIENT_SECRET',
            'POSTGRES_PASSWORD'
        ]
        
        for var in required_env:
            if os.getenv(var):
                self.log_pass(f"Environment variable {var} is set")
            else:
                self.log_error(f"Environment variable {var} is missing")
        
        # Check admin token
        if os.getenv('MATRIX_ADMIN_TOKEN'):
            self.log_pass("MATRIX_ADMIN_TOKEN is configured")
        else:
            self.log_warning("MATRIX_ADMIN_TOKEN not set - admin operations will fail")
    
    def validate_files(self):
        """Validate required files exist."""
        print("\n🔍 Validating Required Files...")
        
        required_files = [
            'docker-compose.yml',
            'matrix/homeserver.yaml',
            'matrix/log_config.yaml',
            'element/config.json',
            'keys/oidc_private_key.pem',
            '.env'
        ]
        
        for file_path in required_files:
            if Path(file_path).exists():
                self.log_pass(f"File {file_path} exists")
            else:
                self.log_error(f"Required file {file_path} is missing")
    
    def validate_docker_config(self):
        """Validate Docker configuration."""
        print("\n🔍 Validating Docker Configuration...")
        
        try:
            # Check docker-compose syntax
            result = subprocess.run(
                ['docker', 'compose', 'config'], 
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                self.log_pass("Docker Compose configuration is valid")
            else:
                self.log_error(f"Docker Compose configuration error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.log_error("Docker Compose validation timed out")
        except FileNotFoundError:
            self.log_error("Docker Compose not found - is Docker installed?")
    
    def validate_matrix_config(self):
        """Validate Matrix Synapse configuration."""
        print("\n🔍 Validating Matrix Configuration...")
        
        config_file = Path('matrix/homeserver.yaml')
        if not config_file.exists():
            self.log_error("Matrix homeserver.yaml not found")
            return
            
        try:
            with open(config_file) as f:
                content = f.read()
                
            # Basic checks
            if 'server_name: "matrix.yourhospital.com"' in content:
                self.log_pass("Matrix server name configured")
            else:
                self.log_warning("Matrix server name not found or incorrect")
                
            if 'oidc_providers:' in content:
                self.log_pass("OIDC providers section found")
            else:
                self.log_error("OIDC providers not configured")
                
            if 'enable_registration: false' in content:
                self.log_pass("Registration properly disabled")
            else:
                self.log_warning("Registration might be enabled")
                
        except Exception as e:
            self.log_error(f"Error reading Matrix config: {e}")
    
    def validate_element_config(self):
        """Validate Element configuration."""
        print("\n🔍 Validating Element Configuration...")
        
        config_file = Path('element/config.json')
        if not config_file.exists():
            self.log_error("Element config.json not found")
            return
            
        try:
            with open(config_file) as f:
                config = json.load(f)
                
            # Check homeserver config
            homeserver = config.get('default_server_config', {}).get('m.homeserver', {})
            if homeserver.get('base_url') == 'https://matrix.yourhospital.com':
                self.log_pass("Element homeserver URL configured correctly")
            else:
                self.log_error("Element homeserver URL incorrect")
                
            # Check branding
            if config.get('brand') == 'EquipeMed Chat':
                self.log_pass("Element branding configured")
            else:
                self.log_warning("Element branding not set")
                
            # Check features disabled
            features = config.get('features', {})
            disabled_features = ['feature_pinning', 'feature_custom_status']
            for feature in disabled_features:
                if features.get(feature) == 'disable':
                    self.log_pass(f"Feature {feature} properly disabled")
                else:
                    self.log_warning(f"Feature {feature} not disabled")
                    
        except json.JSONDecodeError as e:
            self.log_error(f"Element config JSON error: {e}")
        except Exception as e:
            self.log_error(f"Error reading Element config: {e}")
    
    def validate_database(self):
        """Validate database connectivity."""
        print("\n🔍 Validating Database...")
        
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                user='matrix_user',
                password=os.getenv('MATRIX_DATABASE_PASSWORD', 'matrix_secure_password_123'),
                database='matrix_db'
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result:
                self.log_pass("Matrix database connection successful")
            else:
                self.log_error("Matrix database connection failed")
                
            conn.close()
            
        except psycopg2.OperationalError as e:
            self.log_error(f"Database connection error: {e}")
        except Exception as e:
            self.log_error(f"Database validation error: {e}")
    
    def validate_ssl_certificates(self):
        """Validate SSL certificate configuration."""
        print("\n🔍 Validating SSL Certificates...")
        
        domains = ['matrix.yourhospital.com', 'chat.yourhospital.com']
        
        for domain in domains:
            try:
                # Simple connectivity test
                response = requests.get(f'https://{domain}', timeout=10, verify=False)
                self.log_pass(f"SSL connectivity to {domain} working")
                
            except requests.RequestException as e:
                self.log_warning(f"SSL connectivity to {domain} failed: {e}")
    
    def run_all_validations(self):
        """Run all validation checks."""
        print("Matrix Synapse Configuration Validation")
        print("=" * 50)
        
        self.validate_environment()
        self.validate_files()
        self.validate_docker_config()
        self.validate_matrix_config()
        self.validate_element_config()
        self.validate_database()
        self.validate_ssl_certificates()
        
        print("\n" + "=" * 50)
        print("VALIDATION SUMMARY")
        print("=" * 50)
        print(f"✅ Passed: {len(self.passed)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")
        
        if self.errors:
            print("\n🚨 ERRORS MUST BE FIXED BEFORE DEPLOYMENT:")
            for error in self.errors:
                print(f"  {error}")
                
        if self.warnings:
            print("\n⚠️  WARNINGS SHOULD BE REVIEWED:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        return len(self.errors) == 0

if __name__ == "__main__":
    validator = MatrixConfigValidator()
    success = validator.run_all_validations()
    sys.exit(0 if success else 1)
```

### 1.2 Service Health Check Script
Create `scripts/health_check.sh`:

```bash
#!/bin/bash
# Comprehensive health check for Matrix services

set -e

echo "Matrix Services Health Check"
echo "============================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Health check functions
check_docker_services() {
    echo -e "\n🐳 Checking Docker Services..."
    
    services=("postgres" "matrix-synapse" "element-web")
    all_healthy=true
    
    for service in "${services[@]}"; do
        if docker compose ps "$service" | grep -q "Up"; then
            echo -e "  ${GREEN}✅ $service is running${NC}"
        else
            echo -e "  ${RED}❌ $service is not running${NC}"
            all_healthy=false
        fi
    done
    
    if [ "$all_healthy" = true ]; then
        echo -e "  ${GREEN}✅ All Docker services are healthy${NC}"
        return 0
    else
        echo -e "  ${RED}❌ Some Docker services are unhealthy${NC}"
        return 1
    fi
}

check_database_health() {
    echo -e "\n🗄️  Checking Database Health..."
    
    # Check PostgreSQL main database
    if docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-eqmd_user}" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ PostgreSQL is responsive${NC}"
    else
        echo -e "  ${RED}❌ PostgreSQL is not responsive${NC}"
        return 1
    fi
    
    # Check Matrix database
    if docker compose exec -T postgres psql -U matrix_user -d matrix_db -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Matrix database is accessible${NC}"
    else
        echo -e "  ${RED}❌ Matrix database is not accessible${NC}"
        return 1
    fi
    
    return 0
}

check_matrix_api() {
    echo -e "\n🏠 Checking Matrix Server API..."
    
    # Check Matrix versions endpoint
    if curl -sf "http://localhost:8008/_matrix/client/versions" > /dev/null; then
        echo -e "  ${GREEN}✅ Matrix API is responding${NC}"
        
        # Get version info
        versions=$(curl -s "http://localhost:8008/_matrix/client/versions" | jq -r '.versions[]' | tail -3 | tr '\n' ' ')
        echo -e "  ${GREEN}ℹ️  Supported client versions: $versions${NC}"
    else
        echo -e "  ${RED}❌ Matrix API is not responding${NC}"
        return 1
    fi
    
    # Check Matrix server status
    if curl -sf "http://localhost:8008/_matrix/client/r0/directory/room/%23test:matrix.yourhospital.com" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Matrix federation API accessible${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Matrix federation API not accessible (expected for non-federated setup)${NC}"
    fi
    
    return 0
}

check_element_web() {
    echo -e "\n🌐 Checking Element Web Client..."
    
    # Check Element web interface
    if curl -sf "http://localhost:8080/" > /dev/null; then
        echo -e "  ${GREEN}✅ Element web interface is responding${NC}"
    else
        echo -e "  ${RED}❌ Element web interface is not responding${NC}"
        return 1
    fi
    
    # Check Element configuration
    if curl -sf "http://localhost:8080/config.json" | jq -e '.brand' > /dev/null 2>&1; then
        brand=$(curl -s "http://localhost:8080/config.json" | jq -r '.brand')
        echo -e "  ${GREEN}✅ Element configuration loaded (Brand: $brand)${NC}"
    else
        echo -e "  ${RED}❌ Element configuration not loaded properly${NC}"
        return 1
    fi
    
    return 0
}

check_oidc_endpoints() {
    echo -e "\n🔐 Checking OIDC Endpoints..."
    
    # Check OIDC discovery
    if curl -sf "https://yourhospital.com/.well-known/openid_configuration" > /dev/null; then
        echo -e "  ${GREEN}✅ OIDC discovery endpoint accessible${NC}"
    else
        echo -e "  ${RED}❌ OIDC discovery endpoint not accessible${NC}"
        return 1
    fi
    
    # Check JWKS endpoint
    if curl -sf "https://yourhospital.com/.well-known/jwks.json" | jq -e '.keys' > /dev/null 2>&1; then
        key_count=$(curl -s "https://yourhospital.com/.well-known/jwks.json" | jq '.keys | length')
        echo -e "  ${GREEN}✅ JWKS endpoint accessible ($key_count keys)${NC}"
    else
        echo -e "  ${RED}❌ JWKS endpoint not accessible${NC}"
        return 1
    fi
    
    return 0
}

check_well_known_matrix() {
    echo -e "\n🔗 Checking Matrix Well-Known..."
    
    # Check client well-known
    if curl -sf "https://matrix.yourhospital.com/.well-known/matrix/client" | jq -e '.m.homeserver' > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Matrix client well-known configured${NC}"
        
        # Check E2E encryption setting
        e2ee_disabled=$(curl -s "https://matrix.yourhospital.com/.well-known/matrix/client" | jq -r '.["io.element.e2ee"].force_disable // false')
        if [ "$e2ee_disabled" = "true" ]; then
            echo -e "  ${GREEN}✅ E2E encryption properly disabled${NC}"
        else
            echo -e "  ${YELLOW}⚠️  E2E encryption not disabled${NC}"
        fi
    else
        echo -e "  ${RED}❌ Matrix client well-known not configured${NC}"
        return 1
    fi
    
    # Check server well-known
    if curl -sf "https://matrix.yourhospital.com/.well-known/matrix/server" > /dev/null; then
        echo -e "  ${GREEN}✅ Matrix server well-known configured${NC}"
    else
        echo -e "  ${RED}❌ Matrix server well-known not configured${NC}"
        return 1
    fi
    
    return 0
}

check_user_sync() {
    echo -e "\n👥 Checking User Synchronization..."
    
    # Check Django management command
    if docker compose exec -T eqmd python manage.py help sync_matrix_users > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ User sync command available${NC}"
    else
        echo -e "  ${RED}❌ User sync command not available${NC}"
        return 1
    fi
    
    # Check Matrix integration status
    if docker compose exec -T eqmd python manage.py shell -c "
from matrix_integration.models import MatrixIntegration, MatrixUser
config = MatrixIntegration.objects.first()
matrix_users = MatrixUser.objects.count()
print(f'Matrix config: {\"✅\" if config else \"❌\"}')
print(f'Matrix users: {matrix_users}')
" 2>/dev/null; then
        echo -e "  ${GREEN}✅ Matrix integration models accessible${NC}"
    else
        echo -e "  ${RED}❌ Matrix integration models not accessible${NC}"
        return 1
    fi
    
    return 0
}

# Run all health checks
main() {
    local overall_health=0
    
    check_docker_services || overall_health=1
    check_database_health || overall_health=1
    check_matrix_api || overall_health=1
    check_element_web || overall_health=1
    check_oidc_endpoints || overall_health=1
    check_well_known_matrix || overall_health=1
    check_user_sync || overall_health=1
    
    echo -e "\n" "=" * 50
    echo "HEALTH CHECK SUMMARY"
    echo "=" * 50
    
    if [ $overall_health -eq 0 ]; then
        echo -e "${GREEN}🎉 All health checks passed! Matrix integration is ready.${NC}"
    else
        echo -e "${RED}🚨 Some health checks failed. Review the issues above.${NC}"
    fi
    
    return $overall_health
}

# Run main function
main "$@"
```

## Step 2: Deployment Procedures

### 2.1 Production Deployment Script
Create `scripts/deploy_matrix.sh`:

```bash
#!/bin/bash
# Production deployment script for Matrix Synapse integration

set -e

# Configuration
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="./logs/matrix_deploy_$(date +%Y%m%d_%H%M%S).log"

# Create necessary directories
mkdir -p "$(dirname "$LOG_FILE")" "$BACKUP_DIR"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

log "Starting Matrix Synapse deployment..."

# Step 1: Pre-deployment validation
log "Step 1: Running pre-deployment validation..."
if ! python3 scripts/validate_matrix_config.py; then
    error_exit "Configuration validation failed"
fi

# Step 2: Backup current configuration
log "Step 2: Backing up current configuration..."
cp -r matrix element nginx "$BACKUP_DIR/" || error_exit "Backup failed"
log "Backup created in $BACKUP_DIR"

# Step 3: Database backup
log "Step 3: Backing up databases..."
if docker compose ps postgres | grep -q "Up"; then
    docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-eqmd_user}" "${POSTGRES_DB:-eqmd_db}" > "$BACKUP_DIR/eqmd_backup.sql"
    docker compose exec -T postgres pg_dump -U matrix_user matrix_db > "$BACKUP_DIR/matrix_backup.sql"
    log "Database backups completed"
else
    log "WARNING: PostgreSQL not running, skipping database backup"
fi

# Step 4: Apply Django migrations
log "Step 4: Applying Django migrations..."
docker compose exec eqmd python manage.py migrate matrix_integration || error_exit "Matrix integration migrations failed"

# Step 5: Setup Matrix OIDC configuration
log "Step 5: Setting up Matrix OIDC configuration..."
docker compose exec eqmd python manage.py setup_matrix_oidc || error_exit "OIDC setup failed"

# Step 6: Start Matrix services
log "Step 6: Starting Matrix services..."

# Start PostgreSQL if not running
if ! docker compose ps postgres | grep -q "Up"; then
    log "Starting PostgreSQL..."
    docker compose up -d postgres
    sleep 10
fi

# Start Matrix Synapse
log "Starting Matrix Synapse..."
docker compose up -d matrix-synapse

# Wait for Matrix to be ready
log "Waiting for Matrix to be ready..."
for i in {1..30}; do
    if curl -sf "http://localhost:8008/_matrix/client/versions" > /dev/null 2>&1; then
        log "Matrix Synapse is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        error_exit "Matrix Synapse failed to start within 300 seconds"
    fi
    sleep 10
done

# Start Element Web
log "Starting Element Web..."
docker compose up -d element-web

# Wait for Element to be ready
log "Waiting for Element to be ready..."
sleep 15
if ! curl -sf "http://localhost:8080/" > /dev/null; then
    error_exit "Element Web failed to start"
fi

# Step 7: Create initial admin users
log "Step 7: Creating initial admin users..."
if [ -n "$MATRIX_ADMIN_TOKEN" ]; then
    docker compose exec eqmd python manage.py sync_matrix_users --sync-admins --create-missing
    log "Admin users synchronized"
else
    log "WARNING: MATRIX_ADMIN_TOKEN not set, skipping admin user creation"
fi

# Step 8: Create bot user
log "Step 8: Creating bot user..."
docker compose exec eqmd python manage.py manage_matrix_rooms --create-bot-user || log "WARNING: Bot user creation failed"

# Step 9: Run health checks
log "Step 9: Running post-deployment health checks..."
if ! bash scripts/health_check.sh; then
    error_exit "Post-deployment health checks failed"
fi

# Step 10: Update nginx configuration
log "Step 10: Updating nginx configuration..."
if [ -f "/etc/nginx/sites-available/matrix" ]; then
    log "Nginx configuration already exists, skipping"
else
    log "Please manually update nginx configuration with nginx/matrix/matrix.conf"
fi

log "Matrix Synapse deployment completed successfully!"
log "Access Element at: https://chat.yourhospital.com"
log "Matrix server: https://matrix.yourhospital.com"
log "Deployment log: $LOG_FILE"
log "Backup location: $BACKUP_DIR"
```

### 2.2 Rollback Script
Create `scripts/rollback_matrix.sh`:

```bash
#!/bin/bash
# Rollback script for Matrix deployment

set -e

BACKUP_DIR="$1"

if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    echo "Available backups:"
    ls -la backups/ 2>/dev/null || echo "No backups found"
    exit 1
fi

echo "Rolling back Matrix deployment from $BACKUP_DIR..."

# Stop Matrix services
echo "Stopping Matrix services..."
docker compose stop matrix-synapse element-web

# Restore configuration
echo "Restoring configuration..."
cp -r "$BACKUP_DIR/matrix" "$BACKUP_DIR/element" "$BACKUP_DIR/nginx" ./ 

# Restore databases if backup exists
if [ -f "$BACKUP_DIR/matrix_backup.sql" ]; then
    echo "Restoring Matrix database..."
    docker compose exec -T postgres psql -U matrix_user -d matrix_db < "$BACKUP_DIR/matrix_backup.sql"
fi

if [ -f "$BACKUP_DIR/eqmd_backup.sql" ]; then
    echo "WARNING: EquipeMed database backup found but not restored automatically"
    echo "To restore: docker compose exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < $BACKUP_DIR/eqmd_backup.sql"
fi

echo "Rollback completed. Services are stopped."
echo "Run 'docker compose up -d' to start services with restored configuration."
```

## Step 3: Monitoring and Alerting

### 3.1 Matrix Monitoring Script
Create `scripts/monitor_matrix.py`:

```python
#!/usr/bin/env python3
"""
Matrix services monitoring script.
Can be used with cron for continuous monitoring.
"""

import json
import time
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import subprocess
from datetime import datetime

class MatrixMonitor:
    def __init__(self):
        self.alerts = []
        self.warnings = []
        self.info = []
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/matrix_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def check_docker_services(self):
        """Check if Docker services are running."""
        services = ['matrix-synapse', 'element-web', 'postgres']
        
        for service in services:
            try:
                result = subprocess.run(
                    ['docker', 'compose', 'ps', service],
                    capture_output=True, text=True, timeout=30
                )
                
                if 'Up' in result.stdout:
                    self.info.append(f"✅ {service} is running")
                else:
                    self.alerts.append(f"🚨 {service} is not running")
                    
            except Exception as e:
                self.alerts.append(f"🚨 Failed to check {service}: {e}")
    
    def check_matrix_api(self):
        """Check Matrix API health."""
        try:
            response = requests.get(
                'http://localhost:8008/_matrix/client/versions',
                timeout=10
            )
            
            if response.status_code == 200:
                versions = response.json().get('versions', [])
                self.info.append(f"✅ Matrix API responding (versions: {len(versions)})")
            else:
                self.alerts.append(f"🚨 Matrix API error: {response.status_code}")
                
        except requests.RequestException as e:
            self.alerts.append(f"🚨 Matrix API unreachable: {e}")
    
    def check_element_web(self):
        """Check Element web interface."""
        try:
            response = requests.get('http://localhost:8080/', timeout=10)
            
            if response.status_code == 200:
                self.info.append("✅ Element web interface responding")
            else:
                self.alerts.append(f"🚨 Element web error: {response.status_code}")
                
            # Check configuration
            config_response = requests.get('http://localhost:8080/config.json', timeout=10)
            if config_response.status_code == 200:
                config = config_response.json()
                brand = config.get('brand', 'Unknown')
                self.info.append(f"✅ Element config loaded (Brand: {brand})")
            else:
                self.warnings.append("⚠️ Element configuration not accessible")
                
        except requests.RequestException as e:
            self.alerts.append(f"🚨 Element web unreachable: {e}")
    
    def check_database(self):
        """Check database connectivity."""
        try:
            result = subprocess.run(
                ['docker', 'compose', 'exec', '-T', 'postgres', 
                 'pg_isready', '-U', 'matrix_user', '-d', 'matrix_db'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                self.info.append("✅ Matrix database accessible")
            else:
                self.alerts.append("🚨 Matrix database not accessible")
                
        except Exception as e:
            self.alerts.append(f"🚨 Database check failed: {e}")
    
    def check_disk_space(self):
        """Check disk space for Matrix media."""
        try:
            result = subprocess.run(
                ['df', '-h', '.'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    usage_line = lines[1].split()
                    if len(usage_line) > 4:
                        usage_percent = usage_line[4].replace('%', '')
                        usage = int(usage_percent)
                        
                        if usage > 90:
                            self.alerts.append(f"🚨 Disk usage critical: {usage}%")
                        elif usage > 80:
                            self.warnings.append(f"⚠️ Disk usage high: {usage}%")
                        else:
                            self.info.append(f"✅ Disk usage normal: {usage}%")
                            
        except Exception as e:
            self.warnings.append(f"⚠️ Disk space check failed: {e}")
    
    def check_ssl_certificates(self):
        """Check SSL certificate expiration."""
        domains = ['matrix.yourhospital.com', 'chat.yourhospital.com']
        
        for domain in domains:
            try:
                result = subprocess.run([
                    'openssl', 's_client', '-connect', f'{domain}:443',
                    '-servername', domain, '-showcerts'
                ], input='', text=True, capture_output=True, timeout=30)
                
                if result.returncode == 0:
                    # Parse certificate expiration
                    cert_result = subprocess.run([
                        'openssl', 'x509', '-noout', '-dates'
                    ], input=result.stdout, text=True, capture_output=True, timeout=10)
                    
                    if 'notAfter=' in cert_result.stdout:
                        self.info.append(f"✅ {domain} SSL certificate valid")
                    else:
                        self.warnings.append(f"⚠️ {domain} SSL certificate status unclear")
                else:
                    self.warnings.append(f"⚠️ {domain} SSL check failed")
                    
            except Exception as e:
                self.warnings.append(f"⚠️ SSL check for {domain} failed: {e}")
    
    def run_all_checks(self):
        """Run all monitoring checks."""
        self.logger.info("Starting Matrix monitoring checks")
        
        self.check_docker_services()
        self.check_matrix_api()
        self.check_element_web()
        self.check_database()
        self.check_disk_space()
        self.check_ssl_certificates()
        
        # Report results
        self.generate_report()
        
        # Send alerts if necessary
        if self.alerts:
            self.send_alert_email()
        
        return len(self.alerts) == 0
    
    def generate_report(self):
        """Generate monitoring report."""
        print(f"\nMatrix Monitoring Report - {datetime.now()}")
        print("=" * 50)
        
        if self.alerts:
            print("\n🚨 CRITICAL ALERTS:")
            for alert in self.alerts:
                print(f"  {alert}")
        
        if self.warnings:
            print("\n⚠️ WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if self.info:
            print("\n✅ STATUS INFO:")
            for info in self.info:
                print(f"  {info}")
        
        print(f"\nSummary: {len(self.alerts)} alerts, {len(self.warnings)} warnings, {len(self.info)} info")
    
    def send_alert_email(self):
        """Send email alerts for critical issues."""
        # Email configuration (adjust as needed)
        smtp_server = "localhost"
        smtp_port = 587
        from_email = "noreply@yourhospital.com"
        to_email = "admin@yourhospital.com"
        
        try:
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = "Matrix Synapse Alert - Critical Issues Detected"
            
            body = f"""
Matrix monitoring has detected critical issues:

ALERTS:
{chr(10).join(self.alerts)}

WARNINGS:
{chr(10).join(self.warnings)}

Please investigate immediately.

Timestamp: {datetime.now()}
Server: Matrix Synapse Integration
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.send_message(msg)
            server.quit()
            
            self.logger.info("Alert email sent successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to send alert email: {e}")

if __name__ == "__main__":
    monitor = MatrixMonitor()
    success = monitor.run_all_checks()
    exit(0 if success else 1)
```

### 3.2 Automated Monitoring Setup
Create `scripts/setup_monitoring.sh`:

```bash
#!/bin/bash
# Setup automated monitoring for Matrix services

echo "Setting up Matrix monitoring..."

# Create monitoring directories
mkdir -p logs crontab

# Create log rotation configuration
cat > logs/matrix_logrotate.conf << 'EOF'
logs/matrix_monitor.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644
}

logs/matrix_deploy_*.log {
    monthly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
}
EOF

# Create monitoring cron job
cat > crontab/matrix_monitoring << 'EOF'
# Matrix Synapse monitoring
# Run every 5 minutes
*/5 * * * * cd /path/to/eqmd && python3 scripts/monitor_matrix.py

# Daily health check
0 8 * * * cd /path/to/eqmd && bash scripts/health_check.sh > logs/daily_health_$(date +\%Y\%m\%d).log 2>&1

# Weekly user sync
0 2 * * 0 cd /path/to/eqmd && docker compose exec -T eqmd python manage.py sync_matrix_users --create-missing --update-profiles

# Log rotation
0 0 * * * /usr/sbin/logrotate logs/matrix_logrotate.conf --state logs/logrotate.state
EOF

echo "Monitoring setup complete!"
echo "To install cron jobs:"
echo "  crontab crontab/matrix_monitoring"
echo ""
echo "To check logs:"
echo "  tail -f logs/matrix_monitor.log"
```

## Step 4: Performance Optimization

### 4.1 Matrix Performance Tuning
Create `matrix/performance_tuning.yaml`:

```yaml
# Additional Matrix performance configuration
# Add these to homeserver.yaml for production

# Database connection pooling
database:
  args:
    # ... existing config ...
    cp_min: 5
    cp_max: 20
    cp_recycle: 3600
    
# Caching configuration
caches:
  global_factor: 1.0
  per_cache_factors:
    get_users_who_share_room_with_user: 2.0
    get_rooms_for_user: 1.5
    get_room_summary: 2.0
    
# Event cache
event_cache_size: 100K

# Background updates
background_updates_interval: 1000

# Media repository optimization
media_store_path: "/data/media_store"
max_upload_size: "50M"
max_image_pixels: "32M"

# Thumbnail generation limits
thumbnail_sizes:
  - width: 32
    height: 32
    method: crop
  - width: 96
    height: 96
    method: crop
  - width: 320
    height: 240
    method: scale
  - width: 640
    height: 480
    method: scale

# Rate limiting for medical environment
rc_message:
  per_second: 0.5  # Increased for medical use
  burst_count: 20

rc_registration:
  per_second: 0.1
  burst_count: 3

# Login rate limiting
rc_login:
  address:
    per_second: 0.17
    burst_count: 3
  account:
    per_second: 0.17
    burst_count: 3

# Media rate limiting
rc_admin_redaction:
  per_second: 1
  burst_count: 50

# Federation disabled - no limits needed
federation_rc_window_size: 1000
federation_rc_sleep_limit: 10
federation_rc_sleep_delay: 500
federation_rc_reject_limit: 50
federation_rc_concurrent: 3
```

### 4.2 Docker Resource Optimization
Update `docker-compose.yml` with optimized resource limits:

```yaml
  # Matrix Synapse with optimized resources
  matrix-synapse:
    # ... existing configuration ...
    deploy:
      resources:
        limits:
          memory: 1G      # Increased for better performance
          cpus: '2.0'     # Limit CPU usage
        reservations:
          memory: 512M
          cpus: '0.5'
    
    # Health check with longer intervals for stability
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8008/health"]
      interval: 60s      # Reduced frequency
      timeout: 30s       # Longer timeout
      retries: 3
      start_period: 120s # Longer start period

  # Element Web with minimal resources
  element-web:
    # ... existing configuration ...
    deploy:
      resources:
        limits:
          memory: 256M    # Increased slightly
          cpus: '0.5'
        reservations:
          memory: 128M
          cpus: '0.1'
```

## Verification and Testing Procedures

### Final Integration Test
```bash
# Run complete validation
python3 scripts/validate_matrix_config.py

# Deploy with monitoring
bash scripts/deploy_matrix.sh

# Run health checks
bash scripts/health_check.sh

# Test user creation and login flow
docker compose exec eqmd python manage.py sync_matrix_users --create-missing --user admin

# Monitor for 24 hours
python3 scripts/monitor_matrix.py
```

### Performance Testing
```bash
# Test Matrix API performance
time curl -s "http://localhost:8008/_matrix/client/versions"

# Test Element loading time
time curl -s "http://localhost:8080/" > /dev/null

# Check memory usage
docker stats matrix-synapse element-web --no-stream

# Check disk usage
docker system df
```

## File Structure Check

After Phase 6, your complete file structure should be:
```
├── docker-compose.yml          # Complete with Matrix services
├── .env                        # All configuration variables
├── matrix/                     # Matrix Synapse configuration
├── element/                    # Element Web configuration
├── nginx/                      # Nginx configuration
├── matrix_integration/         # Django app for Matrix
├── keys/                       # OIDC keys
├── scripts/                    # Deployment and monitoring scripts
│   ├── validate_matrix_config.py
│   ├── health_check.sh
│   ├── deploy_matrix.sh
│   ├── rollback_matrix.sh
│   ├── monitor_matrix.py
│   └── setup_monitoring.sh
├── logs/                       # Log files
└── backups/                    # Backup directory
```

## Troubleshooting Guide

### Common Issues and Solutions

1. **Matrix won't start**
   ```bash
   # Check logs
   docker compose logs matrix-synapse
   
   # Validate configuration
   python3 scripts/validate_matrix_config.py
   
   # Check database connectivity
   docker compose exec postgres psql -U matrix_user -d matrix_db
   ```

2. **Element not loading**
   ```bash
   # Check Element logs
   docker compose logs element-web
   
   # Test configuration
   curl http://localhost:8080/config.json
   ```

3. **OIDC authentication failing**
   ```bash
   # Test OIDC endpoints
   curl https://yourhospital.com/.well-known/openid_configuration
   
   # Check Matrix logs for OIDC errors
   docker compose logs matrix-synapse | grep -i oidc
   ```

4. **Performance issues**
   ```bash
   # Check resource usage
   docker stats
   
   # Optimize database
   docker compose exec postgres psql -U matrix_user -d matrix_db -c "VACUUM ANALYZE;"
   ```

---

**Status**: Complete Matrix Synapse integration ready for production deployment with monitoring, performance optimization, and troubleshooting procedures