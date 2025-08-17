# Patients App - Complete Guide

**Full CRUD patient management with tagging system and status tracking**

## Overview

- Patient models: Patient, AllowedTag, Tag
- Search by name, ID, fiscal/health card numbers
- Status tracking: inpatient, outpatient, emergency, discharged, transferred, deceased
- Gender field: Masculino, Feminino, Outro, Não Informado (default for legacy data)
- Color-coded tagging system with web admin interface
- Dashboard widgets: patient stats, recent patients
- Template tags: `patient_status_badge`, `patient_tags`
- URL structure: `/patients/`, `/patients/<uuid>/`, `/patients/tags/`

## Patient Status Management

- **Status Types**: inpatient, outpatient, emergency, discharged, transferred, deceased
- **Role-Based Access**: Different access levels based on user profession and patient status
- **Death Declaration**: Only doctors/residents can declare death (change to deceased status)
- **Admin Override**: Only admin/superuser can change deceased patients (for data corrections)
- **Simple Validation**: Basic status validation without complex assignment logic
- **Universal Access**: All medical staff can access all patients regardless of status

## Patient Model Fields

### Core Information
- `name`: Full patient name
- `birth_date`: Date of birth
- `gender`: Choice field (Masculino, Feminino, Outro, Não Informado)
- `fiscal_number`: Government identification number
- `health_card_number`: Health system identification

### Contact Information
- `phone`: Primary phone number
- `email`: Email address
- `address`: Full address
- `emergency_contact`: Emergency contact information

### Medical Information
- `status`: Current patient status (choices above)
- `admission_date`: Date of admission (for inpatients)
- `discharge_date`: Date of discharge (when applicable)
- `allergies`: Known allergies (text field)
- `medical_notes`: General medical notes

### System Fields
- `id`: UUID primary key
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `created_by`: User who created the record
- `updated_by`: User who last updated the record

## Tagging System

### AllowedTag Model
- Defines available tag categories
- Admin-managed color coding
- Hierarchical organization support

### Tag Model
- Links patients to allowed tags
- Many-to-many relationship through Patient model
- Audit trail for tag assignments

### Tag Management
- Web interface for tag assignment
- Color-coded display
- Filter patients by tags
- Bulk tag operations

## Patient Status Workflow

### Status Transitions
```
New Patient → inpatient/outpatient/emergency
inpatient → discharged/deceased/outpatient
outpatient → inpatient/discharged/deceased
emergency → inpatient/discharged/deceased/outpatient
discharged → (final state, can be reopened)
deceased → (final state, admin override only)
```

### Permission Requirements
- **Any Status → inpatient/outpatient/emergency**: Medical staff
- **Any Status → discharged**: Doctors/residents only
- **Any Status → deceased**: Doctors/residents only
- **deceased → Any Status**: Admin/superuser only (data corrections)

## Internal Transfer Management

### Overview
- **Internal transfers** change ward/bed location without changing patient status
- Available for INPATIENT and EMERGENCY patients only
- Automatically generates timeline events
- Updates both patient location and current admission records

### Transfer Process
1. **Access**: Transfer button available on patient details page
2. **Ward Selection**: Choose from active hospital wards
3. **Bed Assignment**: Optional bed/room identifier
4. **Reason**: Required justification for transfer
5. **Timeline Event**: Automatic event creation with transfer history

### Data Updates
- `Patient.ward` → new ward
- `Patient.bed` → new bed identifier
- `PatientAdmission.ward` → new ward (current admission)
- `PatientAdmission.final_bed` → new bed (current admission)
- `Event` → transfer timeline record

### Timeline Integration
- Event Type: `TRANSFER_EVENT` (17)
- Description: "Transferência interna: [Old Location] → [New Location]"
- Reason included in event description
- Searchable in patient timeline

### UI Features
- **Current Location Display**: Shows current ward and bed
- **Ward Dropdown**: Active wards only, current ward disabled
- **Validation**: Prevents transfer to same location
- **Success Message**: Confirms transfer with new location

## Search and Filtering

### Search Fields
- Patient name (fuzzy matching)
- Fiscal number (exact match)
- Health card number (exact match)
- Phone number (partial match)

### Filter Options
- Patient status
- Assigned tags
- Date ranges (admission, discharge, creation)
- Gender
- Age ranges

### Advanced Search
- Combine multiple criteria
- Save search queries
- Export search results

## Dashboard Integration

### Patient Statistics Widget
- Total patients by status
- Recent admissions/discharges
- Status distribution charts
- Trending data

### Recent Patients Widget
- Last 10 updated patients
- Quick access to patient details
- Status indicators

## Template Tags

### patient_status_badge
```django
{% load patients_tags %}
{% patient_status_badge patient.status %}
```
Renders color-coded status badge.

### patient_tags
```django
{% load patients_tags %}
{% patient_tags patient %}
```
Renders assigned tags with colors.

### patient_age
```django
{% load patients_tags %}
{% patient_age patient %}
```
Calculates and displays patient age.

## URL Patterns

- `/patients/` - Patient list view
- `/patients/create/` - Create new patient
- `/patients/<uuid>/` - Patient detail view
- `/patients/<uuid>/edit/` - Edit patient
- `/patients/<uuid>/delete/` - Delete patient (soft delete)
- `/patients/<uuid>/history/` - Audit history
- `/patients/<uuid>/status/transfer/` - Internal ward/bed transfer
- `/patients/tags/` - Tag management interface
- `/patients/search/` - Advanced search
- `/patients/export/` - Export patient data

## Permissions and Access Control

### View Permissions
- All medical staff can view all patients
- Students have read-only access
- Administrative staff have no patient access

### Edit Permissions
- Doctors/residents: Full edit access
- Nurses: Limited edit access (contact info, notes)
- Physiotherapists: Limited edit access
- Students: No edit access

### Special Permissions
- Delete patients: Doctors/residents only
- Change deceased status: Admin override only
- View audit history: All medical staff
- Manage tags: Admin/superuser only

## Integration with Other Apps

### Events Integration
- Patient timeline shows all events
- Event creation linked to patient
- Patient context in event views

### MediaFiles Integration
- Patient photos and videos
- Secure file access control
- Timeline integration

### Daily Notes Integration
- Patient-specific daily notes
- Filter by patient
- Timeline display

## Data Validation

### Required Fields
- Name, birth_date, status
- At least one contact method (phone or email)

### Format Validation
- Fiscal number format checking
- Health card number validation
- Email format validation
- Phone number format

### Business Logic Validation
- Age constraints (birth_date not in future)
- Status transition validation
- Duplicate patient detection
- Contact information completeness

## Audit History

All patient changes are tracked:
- Field-level change detection
- User attribution
- Timestamp tracking
- Change reason logging
- IP address recording

Access via:
- Django admin history interface
- Patient detail page history tab
- Security monitoring commands
- Direct database queries

## Performance Considerations

### Database Indexes
- Optimized for common search patterns
- Status-based filtering
- Name and ID lookups
- Date range queries

### Query Optimization
- Select_related for foreign keys
- Prefetch_related for many-to-many
- Only() for list views
- Pagination for large datasets

### Caching Strategy
- Patient statistics caching
- Tag assignments caching
- Search result caching
- Template fragment caching