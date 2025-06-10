# Sample Data Population Guide

This guide explains how to use the `populate_sample_data` management command to create realistic test data for the EquipeMed application.

## Overview

The `populate_sample_data` command creates a comprehensive set of sample data including hospitals, medical staff, patients, and daily notes. This is essential for testing the application's features, permissions system, and user interface.

## Quick Start

```bash
# Basic usage - create all sample data
python manage.py populate_sample_data

# Preview what would be created (recommended first run)
python manage.py populate_sample_data --dry-run

# Clear existing sample data and create fresh data
python manage.py populate_sample_data --clear-existing
```

## What Gets Created

### 🏥 Hospitals (2 additional)

- **Hospital São João** (São Paulo)

  - UTI (12 beds)
  - Clínica Médica (30 beds)
  - Cardiologia (20 beds)

- **Hospital Santa Maria** (Rio de Janeiro)
  - Emergência (25 beds)
  - Cirurgia (18 beds)
  - Pediatria (15 beds)

### 👥 Medical Staff (11 users)

**All users have the same password: `samplepass123`**

| Role      | Count | Email Pattern          | Example               |
| --------- | ----- | ---------------------- | --------------------- |
| Doctors   | 5     | dr.{name}@example.com  | <dr.silva@example.com>  |
| Nurses    | 2     | enf.{name}@example.com | <enf.maria@example.com> |
| Residents | 2     | res.{name}@example.com | <res.ana@example.com>   |
| Students  | 2     | est.{name}@example.com | <est.paula@example.com> |

### 👤 Patients (40 total)

- **30 hospital patients**: 10 per hospital (mix of inpatients/emergency/outpatients)
- **10 outpatients**: Not assigned to any hospital
- **Realistic data**: Portuguese names, CPF, RG, addresses, phone numbers
- **Medical records**: Hospital registration numbers and admission dates

### 🏷️ Sample Tags (6 medical conditions)

- Diabetes (red)
- Hipertensão (orange)
- Cardiopata (purple)
- Idoso (violet)
- Crítico (pink)
- Alérgico (teal)

### 📝 Daily Notes (200 total)

- **5 notes per patient** with realistic medical evolution content
- **Date spread**: Notes distributed across the last 15 days
- **Multiple authors**: Created by different medical staff members
- **Medical terminology**: Professional Portuguese medical language

## Command Options

### `--dry-run`

Preview what would be created without actually creating any data.

```bash
python manage.py populate_sample_data --dry-run
```

**Use this first** to understand what the command will do.

### `--clear-existing`

Remove existing sample data before creating new data.

```bash
python manage.py populate_sample_data --clear-existing
```

This removes:

- All users with usernames starting with `sample_`
- All patients created by sample users
- All daily notes created by sample users
- All hospitals with names starting with `Hospital`
- All tags with names starting with `Tag`

## Sample User Credentials

### Login Information

**Password for ALL users: `samplepass123`**

### Sample Logins by Role

**Doctors:**

- <dr.silva@example.com> / samplepass123
- <dr.santos@example.com> / samplepass123
- <dr.oliveira@example.com> / samplepass123
- <dr.costa@example.com> / samplepass123
- <dr.ferreira@example.com> / samplepass123

**Nurses:**

- <enf.maria@example.com> / samplepass123
- <enf.jose@example.com> / samplepass123

**Residents:**

- <res.ana@example.com> / samplepass123
- <res.carlos@example.com> / samplepass123

**Students:**

- <est.paula@example.com> / samplepass123
- <est.pedro@example.com> / samplepass123

## Testing Scenarios

### Permission Testing

1. **Login as different user types** to test role-based permissions
2. **Hospital context switching** - users are assigned to multiple hospitals
3. **Patient access control** - test who can view/edit which patients
4. **Edit time windows** - daily notes have 24-hour edit restrictions

### Feature Testing

1. **Patient management** - Create, view, edit patient records
2. **Daily notes** - Add evolution notes and test permissions
3. **Hospital records** - View patient records across hospitals
4. **Tag system** - Assign and filter by medical condition tags
5. **Search functionality** - Search patients by name, ID, or health card
6. **Dashboard widgets** - Test recent patients and notes displays

### Data Relationships

- **Users ↔ Hospitals**: Staff members assigned to 1-2 hospitals
- **Patients ↔ Hospitals**: Hospital records with registration numbers
- **Events ↔ Users**: Daily notes created by medical staff
- **Patients ↔ Tags**: Medical condition tags with color coding

## Best Practices

### Development Workflow

1. **Start fresh**: Use `--clear-existing` when major changes are made
2. **Preview first**: Always run `--dry-run` before actual creation
3. **Test permissions**: Login with different user types to verify access control
4. **Verify data**: Check that relationships are properly created

### Data Management

- **Sample data identification**: All sample data uses `sample_` prefix for easy identification
- **Safe deletion**: The `--clear-existing` flag only removes sample data, not real data
- **Idempotent operation**: Safe to run multiple times
- **No conflicts**: Sample data won't interfere with real production data

## Troubleshooting

### Common Issues

**Permission Errors:**

```bash
# Make sure groups are set up first
python manage.py setup_groups
```

**Database Errors:**

```bash
# Ensure migrations are up to date
python manage.py migrate
```

**Import Errors:**

```bash
# Install faker if not available
pip install faker
# or with uv
uv add faker
```

### Verification Steps

After running the command, verify:

1. **Users created**: Check admin interface for new users
2. **Login works**: Test login with sample credentials
3. **Hospitals exist**: Verify hospitals and wards in admin
4. **Patients visible**: Check patient list for created patients
5. **Daily notes**: Verify notes appear in patient timelines
6. **Permissions work**: Test access control with different user types

## Integration with Testing

### Automated Testing

The sample data can be used in automated tests:

```python
# In test setup
call_command('populate_sample_data')

# Test with sample users
user = User.objects.get(username='sample_dr_silva')
self.client.force_login(user)
```

### Manual Testing

1. **Login as doctor**: Full access to all features
2. **Login as student**: Limited to outpatients only
3. **Switch hospitals**: Test hospital context switching
4. **Create/edit notes**: Test 24-hour edit window
5. **Search patients**: Test search and filtering

## Related Documentation

- [Database Reset Guide](database-reset.md) - How to reset database if needed
- [Testing Strategy](testing-strategy.md) - Comprehensive testing approach
- [Permissions User Guide](permissions/user-guide.md) - Understanding permission system

## Security Notes

⚠️ **Important**: This command is for development and testing only.

- **Never run in production** - Contains hardcoded passwords
- **Development environments only** - Sample data is not production-ready
- **Clean up after testing** - Use `--clear-existing` to remove sample data
- **Password security** - All users share the same simple password

---

**Remember**: The sample data password is `samplepass123` for all users.

