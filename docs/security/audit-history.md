# Security and Audit History

**EquipeMed includes comprehensive audit history tracking and security
monitoring for all database changes.**

## Audit Trail Storage

All model changes are automatically tracked in dedicated history tables:

- **Patient changes**: `patients_historicalpatient`
- **User account changes**: `accounts_historicaleqmdcustomuser` (includes terms
  acceptance)
- **Medical events**: `events_historicalevent`
- **System configuration**: `patients_historicalallowedtag`

Each history record includes:

- **Complete model data** at time of change
- **User attribution** (who made the change)
- **Timestamp** (when change occurred)
- **Change type** (created/modified/deleted)
- **Change reason** (why change was made)
- **IP address** (where change originated)

## Catalogue tag audit

Catalogue tags keep two complementary audit trails:

- `patients_historicalallowedtag` (django-simple-history) records every field
  change to the row, including classification and descriptive edits;
- `patients_allowedtagtransition` is an append-only table for lifecycle and
  ownership changes: activate, deactivate, archive, restore and responsibility
  transfer. Each row stores the action, actor, timestamp, previous/new state,
  previous/new responsible leader and an optional reason.

Latest-action fields on the tag (`deactivated_*`, `reactivated_*`, `archived_*`,
`restored_*`) describe the most recent corresponding action; they supplement the
full transition history and never replace it. Archived rows are canonicalized as
inactive; restoration keeps the same identity inactive and records its actor.
The creator (`created_by`) is immutable across edits and transfers. Transition
rows are append-only through ordinary workflows and are never edited or deleted
by catalogue administration.

Catalogue lifecycle operations must use **Tags Permitidas** admin actions or the
catalogue services; direct field edits cannot change `is_active`, `is_deleted`
or responsibility. Administrator authority requires an active staff/superuser
account with the relevant catalogue permission, so staff status alone is
insufficient.

## Accessing Audit History

### 1. Django Admin Interface (Primary Method)

- Navigate to any model with history tracking
- Click **"History"** button on record change form
- View complete timeline with diff highlighting
- Filter and search historical changes

**Access**: `/admin/` → Select model → Select record → "History" button

### 2. Security Monitoring Commands

```bash
# Detect suspicious activity patterns
uv run python manage.py detect_suspicious_activity --comprehensive --days=7

# Real-time security monitoring with alerts
uv run python manage.py security_alert_monitor --continuous --critical-only

# Generate comprehensive security reports
uv run python manage.py security_report --days=30 --format=json --output=security_report.json
```

**Available Options**:

- `--comprehensive`: Full analysis across all models
- `--days=N`: Look back N days for analysis
- `--threshold=N`: Set suspicious activity threshold
- `--export=file.csv`: Export findings to CSV
- `--continuous`: Real-time monitoring mode
- `--critical-only`: Show only critical severity alerts

### 3. Custom History Views

- **Patient History**: `/patients/<patient_id>/history/`
- **User-specific queries**: Available through Django ORM
- **Bulk analysis**: Via management commands

### 4. Direct Database Access (Advanced)

```sql
-- Recent patient changes
SELECT h.history_date, h.history_type, h.name, h.status,
       u.username as changed_by, h.history_change_reason
FROM patients_historicalpatient h
LEFT JOIN accounts_eqmdcustomuser u ON h.history_user_id = u.id
ORDER BY h.history_date DESC LIMIT 50;

-- User privilege escalations
SELECT h.history_date, h.username, h.profession_type, h.is_staff, h.is_superuser
FROM accounts_historicaleqmdcustomuser h
WHERE h.history_type = '~' AND (h.is_staff = true OR h.is_superuser = true)
ORDER BY h.history_date DESC;
```

## Security Monitoring Features

### Real-time Threat Detection

- **Deletion attempts**: Critical alerts for any data deletion
- **Privilege escalations**: Immediate alerts for user permission changes
- **Bulk operations**: Detection of mass data modifications
- **After-hours activity**: Monitoring of changes outside normal hours
- **Failed access patterns**: Tracking of suspicious access attempts

### Automated Risk Assessment

- **Risk scoring**: Automated calculation based on activity patterns
- **Severity classification**: Critical, High, Medium, Low risk levels
- **Recommendations**: Automated security recommendations based on findings
- **Trend analysis**: Historical pattern identification and alerting

### Compliance and Reporting

- **Comprehensive audit trails**: Complete change history preservation
- **Export capabilities**: CSV, JSON formats for external analysis
- **Multi-format reports**: Text, JSON, CSV reporting options
- **Executive summaries**: High-level security overview reports

## Testing Audit History

```bash
# Run comprehensive history tracking tests
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/*/tests/test_history.py

# Test specific audit functionality
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/patients/tests/test_history.py::TestPatientHistory
```

## Security Best Practices

**For Administrators**:

- Regular security monitoring with `security_alert_monitor`
- Weekly security reports with `security_report`
- Monitor bulk operations and privilege changes
- Review after-hours activity patterns

**For Developers**:

- All model changes automatically tracked
- Include meaningful change reasons: `obj._change_reason = "Reason for change"`
- Test history functionality with comprehensive test suites
- Respect audit trail data - never modify history tables directly

## Related Security Features

- **[Terms of Use System](terms-of-use.md)**: Legal compliance with audit trail
  for user consent
- **Password Change Requirements**: Forced password changes for admin-created users
- **IP Address Tracking**: Enhanced history middleware with client IP logging
- **Security Monitoring**: Comprehensive detection and alerting system
