# Template for docs/apps/dischargereports.md

## Discharge Reports Documentation

This file should be created as `docs/apps/dischargereports.md` during Phase 5 of implementation.

### Content Structure

```markdown
# Discharge Reports (apps/dischargereports)

**Medical discharge report management system with Firebase import capabilities.**

## Overview

The discharge reports app provides comprehensive medical discharge report creation, editing, and management. It extends the Event model to integrate seamlessly with the patient timeline system.

## Features

### Core Functionality
- **Draft System**: Reports start as drafts and can be finalized
- **Event Integration**: Full integration with patient timeline
- **Print/PDF Generation**: Professional Portuguese discharge reports
- **Responsive Design**: Works on desktop and mobile devices
- **Timeline Filtering**: Dedicated filter for discharge reports

### Draft Logic
- New reports default to `is_draft = True`
- Draft reports can be edited and deleted freely
- Finalized reports follow standard 24-hour edit window
- Two save options: "Save Draft" and "Save Final"

## Model Structure

### DischargeReport Fields
- `admission_date`: Date of hospital admission
- `discharge_date`: Date of hospital discharge
- `medical_specialty`: Medical specialty responsible for discharge
- `admission_history`: Clinical admission history
- `problems_and_diagnosis`: Main problems and diagnoses
- `exams_list`: Exams performed during stay
- `procedures_list`: Procedures performed
- `inpatient_medical_history`: Medical evolution during stay
- `discharge_status`: Patient condition at discharge
- `discharge_recommendations`: Post-discharge recommendations
- `is_draft`: Boolean indicating draft status

## URLs and Views

### URL Patterns
- `/dischargereports/` - List view
- `/dischargereports/create/` - Create new report
- `/dischargereports/<uuid>/` - Detail view
- `/dischargereports/<uuid>/update/` - Edit report
- `/dischargereports/<uuid>/delete/` - Delete draft
- `/dischargereports/<uuid>/print/` - Print version

### View Classes
- `DischargeReportListView`: Browse all reports
- `DischargeReportCreateView`: Create new reports
- `DischargeReportDetailView`: View report details
- `DischargeReportUpdateView`: Edit existing reports (draft or 24h window)
- `DischargeReportDeleteView`: Delete draft reports only
- `DischargeReportPrintView`: Print-friendly version

## Templates

### Template Structure
- `dischargereport_create.html`: Separate creation template
- `dischargereport_update.html`: Separate editing template
- `dischargereport_detail.html`: Read-only view
- `dischargereport_list.html`: Browse interface
- `dischargereport_print.html`: Print/PDF layout

### Event Card Integration
- Custom event card: `event_card_dischargereport.html`
- Shows specialty, dates, and draft status
- Action buttons: View, Print, Edit (if allowed)

## Print System

### PDF Report Layout
Professional Portuguese discharge reports including:

1. **Header**: Hospital branding and "Relatório de Alta"
2. **Patient Info**: Name, record number, demographics, dates
3. **Medical Content**: All report sections in order
4. **Footer**: Generation timestamp and user name
5. **Pagination**: Multi-page support with page numbers

### CSS Styling
- Print-specific CSS for proper formatting
- Hospital branding integration
- Responsive layouts for different paper sizes

## Firebase Import System

### Management Command
```bash
# Import discharge reports from Firebase
uv run python manage.py import_firebase_discharge_reports \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --dry-run

# Docker version  
docker compose exec eqmd python manage.py import_firebase_discharge_reports \
  --credentials-file /app/firebase-key.json \
  --database-url https://your-project.firebaseio.com
```

### Command Options

- `--credentials-file`: Firebase service account JSON
- `--database-url`: Firebase Realtime Database URL  
- `--dry-run`: Show what would be imported without saving
- `--since-date`: Import only records after date (YYYY-MM-DD)
- `--limit`: Limit number of records (testing)

### Firebase Data Structure

The command imports from `patientDischargeReports` reference with this structure:

```json
{
  "firebase-key": {
    "content": {
      "admissionDate": "2025-08-22",
      "dischargeDate": "2025-09-05", 
      "specialty": "Cirurgia Vascular",
      "admissionHistory": "...",
      "problemsAndDiagnostics": "...",
      "examsList": "...",
      "proceduresList": "...",
      "inpatientMedicalHistory": "...",
      "patientDischargeStatus": "...",
      "dischargeRecommendations": "..."
    },
    "datetime": 1757081600582,
    "patient": "-OVHlG3K_Lvt-GD40xOv",
    "username": "Doctor Name"
  }
}
```

### Data Mapping

| Firebase Field | Django Field |
|----------------|--------------|
| `content.admissionDate` | `admission_date` |
| `content.dischargeDate` | `discharge_date` |
| `content.specialty` | `medical_specialty` |
| `content.admissionHistory` | `admission_history` |
| `content.problemsAndDiagnostics` | `problems_and_diagnosis` |
| `content.examsList` | `exams_list` |
| `content.proceduresList` | `procedures_list` |
| `content.inpatientMedicalHistory` | `inpatient_medical_history` |
| `content.patientDischargeStatus` | `discharge_status` |
| `content.dischargeRecommendations` | `discharge_recommendations` |

### PatientAdmission Creation

The import command automatically creates `PatientAdmission` records:

- `admission_type`: "scheduled"
- `discharge_type`: "medical"  
- `is_active`: False
- `stay_duration_days`: Calculated from dates
- Empty beds, wards, and diagnoses

## Testing

### Running Tests

```bash
# All discharge report tests
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/

# Specific test files
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_models.py
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_views.py
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_firebase_import.py
```

### Test Coverage

- Model validation and methods
- CRUD view functionality  
- Permission and draft logic
- Firebase import process
- Timeline integration
- Print template rendering

## Permissions

### Draft System Permissions

- **Create**: Any authenticated user with event creation rights
- **Edit Draft**: Original creator or users with edit permissions  
- **Edit Finalized**: Standard 24-hour window applies
- **Delete**: Draft reports only
- **View**: Standard patient access permissions

### Timeline Integration

- Reports appear in patient timeline with proper filtering
- Event cards show appropriate actions based on permissions
- Draft status clearly indicated in UI

## Troubleshooting

### Common Issues

**Firebase Import Fails**

- Verify credentials file path and permissions
- Check database URL format
- Ensure patients exist before importing reports
- Use `--dry-run` to test configuration

**Print Layout Issues**  

- Test across different browsers
- Verify CSS media queries for print
- Check hospital branding template tags

**Timeline Not Showing Reports**

- Verify `DISCHARGE_REPORT_EVENT` constant  
- Check event card template registration
- Test timeline filtering JavaScript

**Draft Logic Problems**

- Verify `is_draft` field default value
- Check view permission logic
- Test save button functionality

## Development Notes

### Adding New Fields

1. Add field to model with migration
2. Update form class and widgets  
3. Modify templates (create, update, detail, print)
4. Update Firebase import mapping if needed
5. Add to test fixtures

### Extending Print Layout

1. Modify `dischargereport_print.html` template
2. Update print CSS for new sections
3. Test pagination with additional content
4. Verify hospital branding integration

This documentation provides comprehensive coverage of the discharge reports feature for both users and developers.

```
