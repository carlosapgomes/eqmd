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

### Step 3: Delete Database

**For SQLite (default):**

```bash
rm db.sqlite3
```

**For PostgreSQL:**

```bash
dropdb your_database_name
createdb your_database_name
```

**For MySQL:**

```bash
mysql -u root -p -e "DROP DATABASE your_database_name; CREATE DATABASE your_database_name;"
```

### Step 4: Create Fresh Migrations

```bash
python manage.py makemigrations
```

### Step 5: Apply Migrations

```bash
python manage.py migrate
```

### Step 6: Create Superuser

```bash
python manage.py createsuperuser
```

### Step 7: Set Up Initial Data

```bash
# Create permission groups
python manage.py setup_groups

# Create sample tags (optional)
python manage.py create_sample_tags

# Create comprehensive sample data (hospitals, users, patients, daily notes, drug templates, prescriptions)
python manage.py populate_sample_data

# Assign users to hospitals if needed
python manage.py assign_users_to_hospitals
```

## Option 2: Database-Only Reset

This keeps your migration files but resets all data.

### Step 1: Delete Database Only

```bash
# For SQLite
rm db.sqlite3

# For PostgreSQL
dropdb your_database_name && createdb your_database_name

# For MySQL
mysql -u root -p -e "DROP DATABASE your_database_name; CREATE DATABASE your_database_name;"
```

### Step 2: Apply Existing Migrations

```bash
python manage.py migrate
```

### Step 3: Recreate Initial Data

```bash
python manage.py createsuperuser
python manage.py setup_groups
python manage.py create_sample_tags
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
python manage.py shell
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
python manage.py makemigrations events dailynotes
python manage.py migrate
```

## Troubleshooting

### Migration Conflicts

If you get migration conflicts after reset:

```bash
python manage.py migrate --fake-initial
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
python manage.py migrate --fake
python manage.py migrate --fake-initial
```

## Post-Reset Checklist

After completing a database reset, verify:

- [ ] Development server starts without errors: `python manage.py runserver`
- [ ] Admin interface loads: `http://localhost:8000/admin/`
- [ ] Can create test patients, events, daily notes, drug templates, and prescriptions
- [ ] Permissions system works correctly
- [ ] Hospital context middleware functions properly
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
python manage.py showmigrations

# Check for migration issues
python manage.py makemigrations --dry-run

# Reset specific app
python manage.py migrate app_name zero

# Show SQL for migrations
python manage.py sqlmigrate app_name migration_number
```

## Getting Help

If you encounter issues not covered in this guide:

1. Check Django migration documentation
2. Review error logs in console output
3. Consult team members or project maintainers
4. Consider using Django's migration troubleshooting tools

---

**Remember**: Database resets are powerful tools that permanently delete data. Use them carefully and always in development environments unless absolutely necessary in production.
