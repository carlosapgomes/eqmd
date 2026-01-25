# Database Reset Guide

This guide provides instructions for completely resetting the Django database and migrations for the EquipeMed project.

## ⚠️ Important Warning

**These operations will permanently delete all data in your database.** Make sure you have backups if you need to preserve any data.

## When to Use This Guide

- Fixing migration conflicts or corruption
- Resolving model inheritance issues (like Event/DailyNote problems)
- Starting fresh during development
- Cleaning up inconsistent database state

## Option 1: Complete Reset (Recommended for Development)

This deletes all migrations and database data for a completely fresh start.

### Step 1: Stop the Development Server

```bash
# Press Ctrl+C to stop any running Django server
```

### Step 2: Delete Migration Files

Go to the `apps` directory and delete all migration files except `__init__.py`.

```bash
# Delete all migration files but keep __init__.py
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
```

### Step 3: Delete Database (PostgreSQL)

```bash
dropdb your_database_name
createdb your_database_name
```

### Step 4: Create Fresh Migrations

```bash
uv run python manage.py makemigrations
```

### Step 5: Apply Migrations

```bash
uv run python manage.py migrate
```

### Step 6: Create Superuser

```bash
uv run python manage.py createsuperuser
```

### Step 7: Set Up Initial Data

```bash
# Create permission groups
uv run python manage.py setup_groups

# Create sample wards
uv run python manage.py create_sample_wards

# Create sample tags (optional)
uv run python manage.py create_sample_tags

# Create comprehensive sample data (users, patients, daily notes, drug templates, prescriptions)
uv run python manage.py populate_sample_data
```

### Step 8: Backup Your Ward Configuration (Optional)

After setting up your wards, create a backup to easily restore them later:

```bash
# Backup current wards to JSON file
uv run python manage.py ward_backup backup --output my_wards_backup.json
```

## Option 2: Database-Only Reset

This keeps your migration files but resets all data.

### Step 1: Delete Database Only (PostgreSQL)

```bash
dropdb your_database_name && createdb your_database_name
```

### Step 2: Apply Existing Migrations

```bash
uv run python manage.py migrate
```

### Step 3: Recreate Initial Data

```bash
uv run python manage.py createsuperuser
uv run python manage.py setup_groups

# Option A: Create sample wards
uv run python manage.py create_sample_wards

# Option B: Restore wards from backup (if you have one)
uv run python manage.py ward_backup restore --input my_wards_backup.json

# Create sample tags (optional)
uv run python manage.py create_sample_tags
```

## Option 3: Selective App Reset

Reset only specific apps while keeping others intact.

### Step 1: Remove App Migrations

```bash
# Example: Reset only events and dailynotes apps
rm apps/events/migrations/0*.py
rm apps/dailynotes/migrations/0*.py
```

### Step 2: Reset App Tables

```bash
# This requires manual SQL or django-extensions
uv run python manage.py shell
```

```python
# In Django shell
from django.db import connection
cursor = connection.cursor()
cursor.execute("DROP TABLE IF EXISTS events_event CASCADE;")
cursor.execute("DROP TABLE IF EXISTS dailynotes_dailynote CASCADE;")
```

### Step 3: Recreate App Migrations

```bash
uv run python manage.py makemigrations events dailynotes
uv run python manage.py migrate
```

## Troubleshooting

### Migration Conflicts

If you get migration conflicts after reset:

```bash
uv run python manage.py migrate --fake-initial
```

### Permission Errors

If you can't delete files:

```bash
sudo rm -rf apps/*/migrations/0*.py
```

### Database Connection Errors

Make sure no Django processes are running:

```bash
ps aux | grep python
# Kill any remaining Django processes
```

### Foreign Key Constraints

If you get foreign key errors during selective reset:

```bash
uv run python manage.py migrate --fake
uv run python manage.py migrate --fake-initial
```

## Post-Reset Checklist

After completing a database reset, verify:

- [ ] Development server starts without errors: `uv run python manage.py runserver`
- [ ] Admin interface loads: `http://localhost:8000/admin/`
- [ ] Can create test tags, patients, events, daily notes, drug templates, and prescriptions
- [ ] Permissions system works correctly
- [ ] Drug templates and prescription functionality works

## Best Practices

1. **Development Environment Only**: Never run these commands on production
2. **Backup First**: Always backup important data before resetting
3. **Team Coordination**: Inform team members before major resets
4. **Version Control**: Commit code changes before database operations
5. **Test After Reset**: Run test suite to ensure everything works

## Related Commands

```bash
# Check migration status
uv run python manage.py showmigrations

# Check for migration issues
uv run python manage.py makemigrations --dry-run

# Reset specific app
uv run python manage.py migrate app_name zero

# Show SQL for migrations
uv run python manage.py sqlmigrate app_name migration_number
```

## Ward Backup and Restore

The `ward_backup` management command helps preserve your ward configuration across database resets.

### Backup Wards

```bash
# Backup all wards to default file (ward_backup.json)
uv run python manage.py ward_backup backup

# Backup to specific file
uv run python manage.py ward_backup backup --output my_wards.json

# Backup only active wards
uv run python manage.py ward_backup backup --active-only --output active_wards.json
```

### Restore Wards

```bash
# Restore from default file (ward_backup.json)
uv run python manage.py ward_backup restore

# Restore from specific file
uv run python manage.py ward_backup restore --input my_wards.json

# Clear all existing wards before restore (dangerous!)
uv run python manage.py ward_backup restore --clear-existing --input my_wards.json

# Update existing wards with same abbreviation
uv run python manage.py ward_backup restore --update-existing --input my_wards.json
```

### Ward Backup Best Practices

1. **Regular Backups**: Create ward backups after configuring your hospital's ward structure
2. **Version Control**: Consider adding backup files to version control for team sharing
3. **Before Reset**: Always backup before database resets to avoid manual reconfiguration
4. **Safe Restore**: Default restore mode skips existing wards to prevent accidental overwrites

### Ward Backup File Format

The backup creates a JSON file with ward data and metadata:

```json
{
  "metadata": {
    "created_at": "2025-08-29T07:32:41.248656",
    "total_wards": 6,
    "active_only": false,
    "version": "1.0"
  },
  "wards": [
    {
      "name": "Unidade de Terapia Intensiva",
      "abbreviation": "UTI",
      "description": "Unidade de cuidados intensivos para pacientes críticos",
      "is_active": true,
      "floor": "3º Andar",
      "capacity_estimate": 12
    }
  ]
}
```

**Note**: UUID identifiers and user references are excluded for portability across different environments.

## Getting Help

If you encounter issues not covered in this guide:

1. Check Django migration documentation
2. Review error logs in console output
3. Consult team members or project maintainers
4. Consider using Django's migration troubleshooting tools

---

**Remember**: Database resets are powerful tools that permanently delete data. Use them carefully and always in development environments unless absolutely necessary in production.
