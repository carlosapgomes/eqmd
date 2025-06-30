# EquipeMed Database Reset Script

## Overview

The `reset_database.sh` script provides a comprehensive, automated solution for completely resetting the EquipeMed Django database and recreating all sample data. This script is designed for development environments and follows the established patterns from the project's documentation.

## Features

- **Complete Database Reset**: Removes all migration files, database, and recreates everything from scratch
- **Comprehensive Sample Data**: Creates hospitals, medical staff, patients, daily notes, drug templates, prescriptions, and more
- **Safety Features**: Confirmation prompts, dry-run mode, and error handling
- **User-Friendly**: Colored output, progress indicators, and detailed status messages
- **Robust Error Handling**: Exits gracefully on errors with helpful messages

## Usage

### Basic Usage

```bash
# Interactive mode with confirmation prompt
./reset_database.sh

# Skip confirmation prompt (use with caution!)
./reset_database.sh --skip-confirmation

# Preview what would be done without making changes
./reset_database.sh --dry-run

# Show help information
./reset_database.sh --help
```

### Command Line Options

- `--help, -h`: Show help message and exit
- `--skip-confirmation`: Skip the confirmation prompt (use with caution!)
- `--dry-run`: Show what would be done without making actual changes

## What the Script Does

### Step 1: Clean Migration Files
- Changes to the `apps/` directory
- Deletes all Django migration files except `__init__.py` files
- Removes compiled Python cache files (.pyc) from migrations directories
- Returns to the project root directory

### Step 2: Remove Database
- Deletes the `db.sqlite3` file if it exists
- Uses conditional deletion to avoid errors if file doesn't exist

### Step 3: Create Fresh Migrations
- Generates fresh migration files for all apps using `uv run python manage.py makemigrations`

### Step 4: Apply Migrations
- Applies all migrations to create the database schema using `uv run python manage.py migrate`

### Step 5: Create Administrative User
- Prompts for superuser creation using `uv run python manage.py createsuperuser`
- Interactive process requiring username, email, and password input

### Step 6: Initialize Application Data
- Sets up permission groups: `uv run python manage.py setup_groups`
- Creates sample tags: `uv run python manage.py create_sample_tags`
- Populates comprehensive sample data: `uv run python manage.py populate_sample_data`
- Assigns users to hospitals: `uv run python manage.py assign_users_to_hospitals --action=assign_all`

## Sample Data Created

After running the script, your database will contain:

### Users and Authentication
- Superuser account (created interactively)
- Multiple sample users with different profession types:
  - Medical doctors
  - Residents
  - Nurses
  - Physiotherapists
  - Students
- All sample users have the password: `samplepass123`

### Healthcare Infrastructure
- Multiple hospitals with wards
- User-hospital assignments
- Permission groups based on profession types

### Patient Data
- Patients with various admission statuses
- Patient-hospital records
- Daily notes and medical events
- Tags and allowed tags system

### Medical Templates and Prescriptions
- Drug templates for common medications
- Prescription templates for standard treatments
- Outpatient prescriptions with prescription items

## Safety Features

### Confirmation Prompt
The script requires explicit confirmation before proceeding with destructive operations. Type `yes` to confirm.

### Dry Run Mode
Use `--dry-run` to preview what the script would do without making any actual changes:

```bash
./reset_database.sh --dry-run
```

### Error Handling
- Exits immediately on any command failure
- Provides clear error messages
- Validates project directory structure before proceeding

### Directory Validation
Ensures the script is run from the correct EquipeMed project root by checking for:
- `manage.py` file
- `apps/` directory
- `pyproject.toml` file

## Requirements

- Must be run from the EquipeMed project root directory
- Requires `uv` command for Python environment management
- Bash shell environment
- Appropriate file system permissions

## Post-Reset Steps

After successful completion:

1. **Start the development server**:
   ```bash
   uv run python manage.py runserver
   ```

2. **Access the admin interface**:
   - URL: http://localhost:8000/admin/
   - Log in with your newly created superuser account

3. **Test sample data**:
   - Browse patients, events, daily notes
   - Test drug templates and prescription functionality
   - Verify permission system works correctly

## Troubleshooting

### Permission Errors
If you encounter permission errors:
```bash
chmod +x reset_database.sh
```

### Wrong Directory
Ensure you're in the project root:
```bash
cd /path/to/eqmd
./reset_database.sh
```

### Command Not Found
Ensure `uv` is installed and available in your PATH.

## Warning

⚠️ **IMPORTANT**: This script permanently deletes all data in your database. Only use this in development environments. Never run this script on production data without proper backups.

## Related Documentation

- `docs/database-reset.md` - Manual database reset procedures
- `docs/sample-data-population.md` - Sample data documentation
- Project README for general setup instructions
