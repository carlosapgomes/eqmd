#!/bin/bash

# EquipeMed Database Reset Script
# This script performs a complete database reset and recreates all sample data
# for the EquipeMed Django project.
#
# WARNING: This will permanently delete all data in your database!
# Only use this in development environments.
#
# Usage: ./reset_database.sh [OPTIONS]
# Options:
#   --help, -h          Show this help message
#   --skip-confirmation Skip the confirmation prompt (use with caution!)
#   --dry-run          Show what would be done without making changes
#
# Author: EquipeMed Development Team
# Version: 1.0

set -e # Exit on any error

# Script options
SKIP_CONFIRMATION=false
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
  echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Function to show help
show_help() {
  echo "EquipeMed Database Reset Script"
  echo ""
  echo "This script performs a complete database reset and recreates all sample data"
  echo "for the EquipeMed Django project."
  echo ""
  echo "WARNING: This will permanently delete all data in your database!"
  echo "Only use this in development environments."
  echo ""
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  --help, -h          Show this help message"
  echo "  --skip-confirmation Skip the confirmation prompt (use with caution!)"
  echo "  --dry-run          Show what would be done without making changes"
  echo ""
  echo "Examples:"
  echo "  $0                  # Interactive mode with confirmation"
  echo "  $0 --skip-confirmation  # Skip confirmation prompt"
  echo "  $0 --dry-run        # Preview what would be done"
  echo ""
  exit 0
}

# Function to parse command line arguments
parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    --help | -h)
      show_help
      ;;
    --skip-confirmation)
      SKIP_CONFIRMATION=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      print_error "Unknown option: $1"
      echo "Use --help for usage information."
      exit 1
      ;;
    esac
  done
}

# Function to check if we're in the correct directory
check_project_directory() {
  if [[ ! -f "manage.py" ]] || [[ ! -d "apps" ]] || [[ ! -f "pyproject.toml" ]]; then
    print_error "This script must be run from the EquipeMed project root directory."
    print_error "Expected files: manage.py, apps/, pyproject.toml"
    exit 1
  fi
  print_status "Confirmed: Running from EquipeMed project root directory"
}

# Function to confirm destructive operations
confirm_reset() {
  if [[ "$SKIP_CONFIRMATION" == true ]]; then
    print_warning "Skipping confirmation prompt as requested"
    return 0
  fi

  if [[ "$DRY_RUN" == true ]]; then
    print_warning "DRY RUN MODE - No actual changes will be made"
    return 0
  fi

  print_header "DATABASE RESET CONFIRMATION"
  print_warning "This operation will:"
  echo "  • Delete all Django migration files (except __init__.py)"
  echo "  • Delete all compiled Python cache files (.pyc) from migrations"
  echo "  • Remove the SQLite database file (db.sqlite3)"
  echo "  • Recreate fresh migrations and database schema"
  echo "  • Prompt for superuser creation"
  echo "  • Populate the database with comprehensive sample data"
  echo ""
  print_warning "ALL EXISTING DATA WILL BE PERMANENTLY LOST!"
  echo ""

  read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation
  if [[ "$confirmation" != "yes" ]]; then
    print_status "Operation cancelled by user."
    exit 0
  fi
  echo ""
}

# Function to clean migration files
clean_migrations() {
  print_header "STEP 1: CLEANING MIGRATION FILES"

  if [[ "$DRY_RUN" == true ]]; then
    print_status "[DRY RUN] Would change to apps directory..."
    print_status "[DRY RUN] Would delete migration files (keeping __init__.py)..."
    print_status "[DRY RUN] Would delete compiled Python cache files from migrations..."
    print_status "[DRY RUN] Would return to project root directory..."
    print_success "[DRY RUN] Migration cleanup would be completed"
    return 0
  fi

  print_status "Changing to apps directory..."
  cd apps

  print_status "Deleting migration files (keeping __init__.py)..."
  if find . -path "*/migrations/*.py" -not -name "__init__.py" -delete 2>/dev/null; then
    print_success "Migration files deleted successfully"
  else
    print_warning "No migration files found to delete"
  fi

  print_status "Deleting compiled Python cache files from migrations..."
  if find . -path "*/migrations/*.pyc" -delete 2>/dev/null; then
    print_success "Cache files deleted successfully"
  else
    print_warning "No cache files found to delete"
  fi

  print_status "Returning to project root directory..."
  cd ..

  print_success "Migration cleanup completed"
}

# Function to remove database
remove_database() {
  print_header "STEP 2: REMOVING DATABASE"

  if [[ "$DRY_RUN" == true ]]; then
    if [[ -f "db.sqlite3" ]]; then
      print_status "[DRY RUN] Would remove SQLite database file..."
    else
      print_warning "[DRY RUN] Database file (db.sqlite3) not found - may already be deleted"
    fi
    print_success "[DRY RUN] Database removal would be completed"
    return 0
  fi

  if [[ -f "db.sqlite3" ]]; then
    print_status "Removing SQLite database file..."
    rm db.sqlite3
    print_success "Database file removed successfully"
  else
    print_warning "Database file (db.sqlite3) not found - may already be deleted"
  fi
}

# Function to create fresh migrations
create_migrations() {
  print_header "STEP 3: CREATING FRESH MIGRATIONS"

  if [[ "$DRY_RUN" == true ]]; then
    print_status "[DRY RUN] Would generate fresh migration files for all apps..."
    print_success "[DRY RUN] Fresh migrations would be created successfully"
    return 0
  fi

  print_status "Generating fresh migration files for all apps..."
  if uv run python manage.py makemigrations; then
    print_success "Fresh migrations created successfully"
  else
    print_error "Failed to create migrations"
    exit 1
  fi
}

# Function to apply migrations
apply_migrations() {
  print_header "STEP 4: APPLYING MIGRATIONS"

  if [[ "$DRY_RUN" == true ]]; then
    print_status "[DRY RUN] Would apply all migrations to create database schema..."
    print_success "[DRY RUN] Database schema would be created successfully"
    return 0
  fi

  print_status "Applying all migrations to create database schema..."
  if uv run python manage.py migrate; then
    print_success "Database schema created successfully"
  else
    print_error "Failed to apply migrations"
    exit 1
  fi
}

# Function to create superuser
create_superuser() {
  print_header "STEP 5: CREATING ADMINISTRATIVE USER"

  if [[ "$DRY_RUN" == true ]]; then
    print_status "[DRY RUN] Would create superuser account..."
    print_warning "[DRY RUN] Would prompt for superuser credentials."
    print_success "[DRY RUN] Superuser would be created successfully"
    return 0
  fi

  print_status "Creating superuser account..."
  print_warning "You will be prompted to enter superuser credentials."
  echo ""

  if uv run python manage.py createsuperuser; then
    print_success "Superuser created successfully"
  else
    print_error "Failed to create superuser"
    exit 1
  fi
}

# Function to initialize application data
initialize_data() {
  print_header "STEP 6: INITIALIZING APPLICATION DATA"

  if [[ "$DRY_RUN" == true ]]; then
    print_status "[DRY RUN] Would set up permission groups..."
    print_status "[DRY RUN] Would create sample wards..."
    print_status "[DRY RUN] Would populate comprehensive sample data..."
    print_status "[DRY RUN] This includes: admin user, hospital, medical staff, patients, sample tags, daily notes, drug templates, prescription templates, and outpatient prescriptions"
    print_success "[DRY RUN] Application data would be initialized successfully"
    return 0
  fi

  print_status "Setting up permission groups..."
  if uv run python manage.py setup_groups; then
    print_success "Permission groups created successfully"
  else
    print_error "Failed to create permission groups"
    exit 1
  fi

  print_status "Creating sample wards..."
  if uv run python manage.py create_sample_wards; then
    print_success "Sample wards created successfully"
  else
    print_error "Failed to create sample wards"
    exit 1
  fi

  print_status "Populating comprehensive sample data..."
  print_status "This includes: admin user, hospitals, medical staff, patients, sample tags, daily notes, drug templates, prescription templates, and outpatient prescriptions"
  if uv run python manage.py populate_sample_data; then
    print_success "Sample data populated successfully"
  else
    print_error "Failed to populate sample data"
    exit 1
  fi

  # print_status "Assigning users to hospitals..."
  # if uv run python manage.py assign_users_to_hospitals --action=assign_all; then
  #   print_success "Users assigned to hospitals successfully"
  # else
  #   print_error "Failed to assign users to hospitals"
  #   exit 1
  # fi
}

# Function to display completion message
display_completion() {
  if [[ "$DRY_RUN" == true ]]; then
    print_header "DRY RUN COMPLETED!"
    echo ""
    print_success "Dry run completed successfully. No actual changes were made."
    print_status "To perform the actual reset, run the script without --dry-run option."
    return 0
  fi

  print_header "DATABASE RESET COMPLETED SUCCESSFULLY!"

  echo ""
  print_success "Your EquipeMed database has been completely reset and populated with sample data."
  echo ""
  print_status "Next steps:"
  echo "  1. Start the development server: uv run python manage.py runserver"
  echo "  2. Access the admin interface: http://localhost:8000/admin/"
  echo "  3. Log in with your newly created superuser account"
  echo ""
  print_status "Sample user credentials:"
  echo "  • All sample users have the password: samplepass123"
  echo "  • Sample users include medical doctors, residents, nurses, physiotherapists, and students"
  echo "  • Each user is assigned to one or more hospitals with appropriate permissions"
  echo ""
  print_status "Available sample data:"
  echo "  • Multiple hospitals with wards"
  echo "  • Hospital wards (UTI, PS, CM, CC, PED, MAT)"
  echo "  • Medical staff with different profession types"
  echo "  • Patients with various admission statuses"
  echo "  • Daily notes and medical events"
  echo "  • Drug templates and prescription templates"
  echo "  • Outpatient prescriptions"
  echo "  • Permission groups and sample tags (Portuguese medical terminology)"
  echo ""
  print_success "Database reset completed successfully!"
}

# Main execution
main() {
  # Parse command line arguments first
  parse_arguments "$@"

  print_header "EQUIPEMED DATABASE RESET SCRIPT"

  if [[ "$DRY_RUN" == true ]]; then
    print_status "Starting dry run - showing what would be done without making changes..."
  else
    print_status "Starting complete database reset and sample data recreation..."
  fi

  # Check environment
  check_project_directory

  # Confirm operation
  confirm_reset

  # Execute reset steps
  clean_migrations
  remove_database
  create_migrations
  apply_migrations
  create_superuser
  initialize_data

  # Display completion message
  display_completion
}

# Run main function
main "$@"
