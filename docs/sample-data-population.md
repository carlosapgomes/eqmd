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

### 🏥 Hospital Configuration

- **Single Hospital Environment**: Configured via environment variables
- **Hospital Settings**: Name, address, phone, email, logo set via HOSPITAL_CONFIG  
- **No Database Models**: Hospital information stored in settings, not database

### 👥 Medical Staff (11 users)

**All users have the same password: `samplepass123`**

| Role      | Count | Email Pattern          | Example               |
| --------- | ----- | ---------------------- | --------------------- |
| Doctors   | 5     | dr.{name}@example.com  | <dr.silva@example.com>  |
| Nurses    | 2     | enf.{name}@example.com | <enf.maria@example.com> |
| Residents | 2     | res.{name}@example.com | <res.ana@example.com>   |
| Students  | 2     | est.{name}@example.com | <est.paula@example.com> |

### 👤 Patients (30 total)

- **30 patients total**: Mix of inpatients, emergency, outpatients, discharged, transferred
- **Universal Access**: All patients accessible to all medical staff
- **Realistic data**: Portuguese names, CPF, RG, addresses, phone numbers
- **Simplified Records**: No hospital assignments, focus on medical care

### 🏷️ Sample Tags (6 medical conditions)

- Diabetes (red)
- Hipertensão (orange)
- Cardiopata (purple)
- Idoso (violet)
- Crítico (pink)
- Alérgico (teal)

### 💊 Drug Templates (15 total)

Realistic pharmaceutical data with Brazilian medications:

**Public Templates (10):**
- Dipirona Sódica 500mg
- Paracetamol 750mg
- Omeprazol 20mg
- Losartana Potássica 50mg
- Metformina 850mg
- Sinvastatina 20mg
- Captopril 25mg
- Hidroclorotiazida 25mg
- Ácido Acetilsalicílico 100mg
- Atenolol 50mg

**Private Templates (5):**
- Amoxicilina 500mg
- Azitromicina 500mg
- Prednisona 20mg
- Diclofenaco Sódico 50mg
- Furosemida 40mg

### 📋 Prescription Templates (5 total)

Common medical scenarios with multiple medications:

**Public Templates (4):**
- Hipertensão Arterial - Tratamento Inicial (2 medications)
- Diabetes Mellitus Tipo 2 - Monoterapia (1 medication)
- Dislipidemia - Tratamento com Estatina (1 medication)
- Proteção Gástrica + Analgesia (2 medications)

**Private Templates (1):**
- Infecção Respiratória - Antibiótico (1 medication)

### 📝 Outpatient Prescriptions (60-90 total)

- **2-3 prescriptions per patient** with realistic medical scenarios
- **Date spread**: Prescriptions distributed across the last 60 days
- **Doctor-only creation**: Only doctors can create prescriptions
- **Template usage**: 40% use prescription templates, 60% individual drug selection
- **Usage tracking**: Drug template usage counts are automatically updated
- **Realistic instructions**: Portuguese medical instructions and return guidelines

### 📋 Sample Content Templates

Sample content templates for various event types can be created with:

```bash
python manage.py create_sample_content
```

This creates templates for:
- Daily evolution notes (Evolução)
- History and physical exams (Anamnese e Exame Físico)  
- Simple observations (Nota/Observação)
- Discharge reports (Relatório de Alta)
- Exam requests (Requisição de Exame)

### 📝 Daily Notes (150 total)

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

- All events (including outpatient prescriptions and daily notes) created by sample users
- All prescription templates created by sample users
- All drug templates created by sample users
- All patients created by sample users
- All users with usernames starting with `sample_`
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
3. **Daily note duplication** - Test duplicate functionality from detail page, list views, and patient timeline
4. **Hospital records** - View patient records across hospitals
5. **Tag system** - Assign and filter by medical condition tags
6. **Search functionality** - Search patients by name, ID, or health card
7. **Dashboard widgets** - Test recent patients and notes displays
8. **Event timeline** - Test timeline view with type-specific event cards
9. **Sample content templates** - Test template creation, viewing, and API access
10. **Drug templates** - Create, edit, and use drug templates in prescriptions
11. **Prescription templates** - Create multi-drug prescription templates
12. **Outpatient prescriptions** - Create prescriptions using templates or individual drugs
13. **Usage tracking** - Verify drug template usage counts are updated
14. **Template permissions** - Test public vs private template visibility

### Data Relationships

- **Users ↔ Hospitals**: Staff members assigned to 1-2 hospitals
- **Patients ↔ Hospitals**: Hospital records with registration numbers
- **Events ↔ Users**: Daily notes and prescriptions created by medical staff
- **Patients ↔ Tags**: Medical condition tags with color coding
- **Drug Templates ↔ Users**: Templates created by medical staff with public/private visibility
- **Prescription Templates ↔ Users**: Multi-drug templates created by medical staff
- **Prescriptions ↔ Drug Templates**: Prescription items linked to source templates with usage tracking
- **Prescriptions ↔ Patients**: Outpatient prescriptions linked to patients with realistic dates

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
5. **Duplicate daily notes**: Test duplication from timeline, detail page, and list views
6. **Timeline event cards**: Verify DailyNote events show duplicate button, other events don't
7. **Search patients**: Test search and filtering

## Related Documentation

- [Database Reset Guide](database-reset.md) - How to reset database if needed
- [Testing Guide](TESTING.md) - Comprehensive testing framework and strategy
- [Permissions User Guide](permissions/user-guide.md) - Understanding permission system

## Security Notes

⚠️ **Important**: This command is for development and testing only.

- **Never run in production** - Contains hardcoded passwords
- **Development environments only** - Sample data is not production-ready
- **Clean up after testing** - Use `--clear-existing` to remove sample data
- **Password security** - All users share the same simple password

---

**Remember**: The sample data password is `samplepass123` for all users.

