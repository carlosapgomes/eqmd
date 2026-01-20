# Audit Trail Model Coverage Report

**Date**: January 20, 2026  
**Scope**: All Django models in the system  
**Total Models**: 42

---

## Executive Summary

- **Models WITH Audit Trail**: 20 (47%)
- **Models WITHOUT Audit Trail**: 22 (53%)

**Status**: Approximately half of the system's models have audit trail implementation. All core clinical data models (Patients, Events) are tracked, but many supporting models lack audit capabilities.

---

## Models WITH Audit Trail (20 models)

### 1. Models with Explicit HistoricalRecords (4 models)

These models have `HistoricalRecords` directly declared in their class definition.

#### Core Models

| Model              | Location                  | Description                  | Tracks                                                                                             |
| ------------------ | ------------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------- |
| **EqmdCustomUser** | `apps/accounts/models.py` | User accounts (AbstractUser) | Profession, registration numbers, account lifecycle, access expiration, supervisor assignments     |
| **Patient**        | `apps/patients/models.py` | Patient records              | Personal data (name, DOB, gender, ID numbers), address, hospital status, ward, bed, record numbers |
| **AllowedTag**     | `apps/patients/models.py` | Tag definitions              | Tag name, description, color, active status                                                        |

#### Base Event Model

| Model     | Location                | Description               | Tracks                                                                                   |
| --------- | ----------------------- | ------------------------- | ---------------------------------------------------------------------------------------- |
| **Event** | `apps/events/models.py` | Base class for all events | Event type, datetime, description, patient association, created/updated by, draft status |

---

### 2. Models Inheriting from Event (16 models)

These models inherit `HistoricalRecords` through the `Event` base class.

#### Patient Events

| Model                  | Location                             | Description                      | Tracks                                     |
| ---------------------- | ------------------------------------ | -------------------------------- | ------------------------------------------ |
| **DailyNote**          | `apps/dailynotes/models.py`          | Daily clinical notes (evoluções) | Note content, clinical observations        |
| **HistoryAndPhysical** | `apps/historyandphysicals/models.py` | Anamnesis and physical exam      | H&P content, examination findings          |
| **SimpleNote**         | `apps/simplenotes/models.py`         | Simple notes/observations        | Brief notes, observations                  |
| **DischargeReport**    | `apps/dischargereports/models.py`    | Discharge summaries              | Discharge diagnosis, summary, instructions |

#### Media Events

| Model           | Location                    | Description              | Tracks                   |
| --------------- | --------------------------- | ------------------------ | ------------------------ |
| **Photo**       | `apps/mediafiles/models.py` | Medical photos/images    | Image file, caption      |
| **PhotoSeries** | `apps/mediafiles/models.py` | Series of related photos | Multiple photos sequence |
| **VideoClip**   | `apps/mediafiles/models.py` | Medical video clips      | Video file, duration     |

#### Clinical Events

| Model                      | Location                                 | Description              | Tracks                            |
| -------------------------- | ---------------------------------------- | ------------------------ | --------------------------------- |
| **OutpatientPrescription** | `apps/outpatientprescriptions/models.py` | Outpatient prescriptions | Prescription details, medications |
| **PDFFormSubmission**      | `apps/pdf_forms/models.py`               | Form submissions         | Form field data, completed forms  |

#### Timeline Events (System Generated)

| Model                       | Location                | Description              | Tracks                                   |
| --------------------------- | ----------------------- | ------------------------ | ---------------------------------------- |
| **RecordNumberChangeEvent** | `apps/events/models.py` | Record number changes    | Old/new record numbers, reason           |
| **AdmissionEvent**          | `apps/events/models.py` | Hospital admissions      | Admission type, bed, diagnosis           |
| **DischargeEvent**          | `apps/events/models.py` | Hospital discharges      | Discharge type, diagnosis, stay duration |
| **StatusChangeEvent**       | `apps/events/models.py` | Patient status changes   | Previous/new status, reason              |
| **TagAddedEvent**           | `apps/events/models.py` | Tag added to patient     | Tag details, notes                       |
| **TagRemovedEvent**         | `apps/events/models.py` | Tag removed from patient | Tag details, notes                       |
| **TagBulkRemoveEvent**      | `apps/events/models.py` | Bulk tag removal         | Count of tags removed                    |

---

## Models WITHOUT Audit Trail (22 models)

### High Priority Models - Should Have Audit Trail

These models contain important data that should be tracked for security and compliance.

| Model                        | Location                       | Risk Level | Why It Needs Audit Trail                       |
| ---------------------------- | ------------------------------ | ---------- | ---------------------------------------------- |
| **PatientAdmission**         | `apps/patients/models.py`      | 🔴 HIGH    | Admission/discharge data, clinical decisions   |
| **PatientRecordNumber**      | `apps/patients/models.py`      | 🔴 HIGH    | Medical record numbers, patient identification |
| **Ward**                     | `apps/patients/models.py`      | 🟡 MEDIUM  | Hospital ward configuration                    |
| **PDFFormTemplate**          | `apps/pdf_forms/models.py`     | 🟡 MEDIUM  | Form templates define clinical data structure  |
| **DrugTemplate**             | `apps/drugtemplates/models.py` | 🟡 MEDIUM  | Drug definitions affect prescriptions          |
| **PrescriptionTemplate**     | `apps/drugtemplates/models.py` | 🟡 MEDIUM  | Prescription templates                         |
| **PrescriptionTemplateItem** | `apps/drugtemplates/models.py` | 🟡 MEDIUM  | Template line items                            |

### Medium Priority Models - Should Consider Audit Trail

| Model               | Location                    | Risk Level | Why It Needs Audit Trail                        |
| ------------------- | --------------------------- | ---------- | ----------------------------------------------- |
| **Tag**             | `apps/patients/models.py`   | 🟡 MEDIUM  | Tag instances assigned to patients              |
| **UserProfile**     | `apps/accounts/models.py`   | 🟢 LOW     | User profile settings (non-critical)            |
| **MediaFile**       | `apps/mediafiles/models.py` | 🟡 MEDIUM  | General media file storage                      |
| **PhotoSeriesFile** | `apps/mediafiles/models.py` | 🟢 LOW     | Files within photo series (event tracks series) |

### Bot Authentication Models - May Not Need Audit Trail

These models have their own audit logging mechanisms (`*AuditLog` models).

| Model                     | Location                 | Risk Level | Notes                           |
| ------------------------- | ------------------------ | ---------- | ------------------------------- |
| **MatrixUserBinding**     | `apps/botauth/models.py` | 🟢 LOW     | Has MatrixBindingAuditLog       |
| **MatrixBindingAuditLog** | `apps/botauth/models.py` | 🟢 LOW     | IS an audit log (self-auditing) |
| **BotClientProfile**      | `apps/botauth/models.py` | 🟢 LOW     | Has BotClientAuditLog           |
| **BotClientAuditLog**     | `apps/botauth/models.py` | 🟢 LOW     | IS an audit log (self-auditing) |
| **DelegationAuditLog**    | `apps/botauth/models.py` | 🟢 LOW     | IS an audit log (self-auditing) |
| **BotDelegationConfig**   | `apps/botauth/models.py` | 🟢 LOW     | Has DelegationAuditLog          |

### Integration Models - May Not Need Audit Trail

| Model                          | Location                            | Risk Level | Notes                       |
| ------------------------------ | ----------------------------------- | ---------- | --------------------------- |
| **MatrixGlobalRoom**           | `apps/matrix_integration/models.py` | 🟢 LOW     | Matrix room management      |
| **MatrixDirectRoom**           | `apps/matrix_integration/models.py` | 🟢 LOW     | Matrix direct message rooms |
| **MatrixBotConversationState** | `apps/matrix_integration/models.py` | 🟢 LOW     | Bot conversation state      |

### Template/Configuration Models - May Not Need Audit Trail

| Model                | Location                                 | Risk Level | Notes                                                  |
| -------------------- | ---------------------------------------- | ---------- | ------------------------------------------------------ |
| **PrescriptionItem** | `apps/outpatientprescriptions/models.py` | 🟢 LOW     | Items within prescriptions (event tracks prescription) |
| **SampleContent**    | `apps/sample_content/models.py`          | 🟢 LOW     | Demo/sample data for testing                           |

---

## Analysis by Category

### Clinical Data Models

| Category            | With Audit             | Without Audit                                                                 | Coverage     |
| ------------------- | ---------------------- | ----------------------------------------------------------------------------- | ------------ |
| **Patient Records** | Patient                | PatientAdmission, PatientRecordNumber, Tag                                    | 1/4 (25%)    |
| **Clinical Events** | 16 event types         | -                                                                             | 16/16 (100%) |
| **Form Templates**  | -                      | PDFFormTemplate, DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem | 0/4 (0%)     |
| **Prescriptions**   | OutpatientPrescription | PrescriptionItem                                                              | 1/2 (50%)    |

**Clinical Data Coverage**: 18/26 models (69%)

### System Models

| Category            | With Audit     | Without Audit | Coverage  |
| ------------------- | -------------- | ------------- | --------- |
| **User Accounts**   | EqmdCustomUser | UserProfile   | 1/2 (50%) |
| **Tags**            | AllowedTag     | Tag           | 1/2 (50%) |
| **Hospital Config** | -              | Ward          | 0/1 (0%)  |

**System Models Coverage**: 2/5 models (40%)

### Bot/Integration Models

| Category               | With Audit | Without Audit               | Coverage |
| ---------------------- | ---------- | --------------------------- | -------- |
| **Bot Auth**           | -          | 6 models (3 are audit logs) | N/A\*    |
| **Matrix Integration** | -          | 3 models                    | 0/3 (0%) |

\*Note: Bot auth models have dedicated audit log models (MatrixBindingAuditLog, BotClientAuditLog, DelegationAuditLog)

**Bot/Integration Coverage**: 0/6 models (0%) - but has separate audit logs

### Media Models

| Category         | With Audit                    | Without Audit              | Coverage  |
| ---------------- | ----------------------------- | -------------------------- | --------- |
| **Media Events** | Photo, PhotoSeries, VideoClip | MediaFile, PhotoSeriesFile | 3/5 (60%) |

**Media Models Coverage**: 3/5 models (60%)

---

## Security Impact Assessment

### ✅ Well Protected (Core Clinical Data)

All **clinical events** are fully tracked:

- ✅ Daily notes, H&P, prescriptions, discharge reports
- ✅ Photos, videos, and media events
- ✅ Form submissions
- ✅ Timeline events (admissions, discharges, status changes)

**Impact**: Complete audit trail of all clinical documentation and patient encounters.

### ⚠️ Partially Protected (Patient Records)

**Patient** model tracked, but related models missing:

- ✅ Patient personal data tracked
- ✅ Tags configuration tracked
- ❌ Patient admissions NOT tracked
- ❌ Record numbers NOT tracked (only events about them)
- ❌ Individual tag instances NOT tracked

**Impact**: Can track patient data changes, but cannot track admission/discharge details or record number assignments in detail.

### ⚠️ Risk Gaps (Configuration & Templates)

Critical configuration models without audit:

- ❌ Ward configurations (hospital organization)
- ❌ PDF form templates (clinical data structure)
- ❌ Drug and prescription templates (affect prescriptions)

**Impact**: Cannot detect tampering with system configuration, form structures, or drug definitions.

### 🟢 Acceptable Gaps (Supporting Models)

Models where audit trail may not be critical:

- User profile settings (non-security data)
- Media file storage (event tracking covers clinical context)
- Matrix room management (integration details)
- Prescription items (parent prescription event tracks them)

---

## Recommendations

### Priority 1: Add Audit Trail to High-Risk Models

These models contain clinical or configuration data that should be tracked:

1. **PatientAdmission** - `apps/patients/models.py`

   - Tracks admission/discharge decisions
   - Critical for patient safety
   - Should track: admission_type, bed, diagnosis, discharge decisions

2. **PatientRecordNumber** - `apps/patients/models.py`

   - Medical record numbers are patient identifiers
   - Changes could affect patient identification
   - Should track: record_number changes

3. **PDFFormTemplate** - `apps/pdf_forms/models.py`

   - Defines clinical data structure
   - Template changes could affect data collection
   - Should track: field configurations, validation rules

4. **DrugTemplate** - `apps/drugtemplates/models.py`

   - Drug definitions affect prescriptions
   - Should track: drug names, dosages, contraindications

5. **PrescriptionTemplate** & **PrescriptionTemplateItem** - `apps/drugtemplates/models.py`

   - Prescription templates affect clinical practice
   - Should track: template configurations

6. **Ward** - `apps/patients/models.py`
   - Hospital ward organization
   - Should track: ward names, capacities, assignments

### Priority 2: Consider Audit Trail for Medium-Risk Models

7. **Tag** - `apps/patients/models.py`

   - Tag instances assigned to patients
   - Currently only AllowedTag (template) is tracked
   - Should track: tag assignments to patients

8. **MediaFile** - `apps/mediafiles/models.py`
   - General media file storage
   - Should track: file uploads, modifications

### Priority 3: Evaluate Bot/Integration Models

9. **Bot Authentication Models** - `apps/botauth/models.py`
   - Evaluate if existing audit log models are sufficient
   - Consider adding HistoricalRecords to main models for redundancy

### Priority 4: Low Priority (Optional)

10. **UserProfile** - `apps/accounts/models.py`

    - Non-critical user settings
    - May not need audit trail

11. **Matrix Integration Models** - `apps/matrix_integration/models.py`
    - Integration details
    - May not need audit trail

---

## Implementation Guide

To add audit trail to a model:

### Step 1: Import HistoricalRecords

```python
from simple_history.models import HistoricalRecords
```

### Step 2: Add History Field to Model

```python
class YourModel(models.Model):
    # Your existing fields...

    # Add history tracking
    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
        cascade_delete_history=False,  # Keep history even if object deleted
    )
```

### Step 3: Update Admin (if applicable)

```python
from simple_history.admin import SimpleHistoryAdmin

@admin.register(YourModel)
class YourModelAdmin(SimpleHistoryAdmin):
    list_display = ['name', 'created_at']  # Regular fields
    history_list_display = ['name', 'history_change_reason']  # History view fields
```

### Step 4: Create Migration

```bash
# Generate migration
uv run python manage.py makemigrations

# Apply migration
uv run python manage.py migrate
```

---

## Implementation Effort Estimate

| Priority       | Models    | Estimated Effort | Impact     |
| -------------- | --------- | ---------------- | ---------- |
| **Priority 1** | 6 models  | 2-3 days         | High       |
| **Priority 2** | 2 models  | 0.5-1 day        | Medium     |
| **Priority 3** | 6 models  | 1-2 days         | Low-Medium |
| **Priority 4** | 4 models  | 0.5-1 day        | Low        |
| **Total**      | 18 models | 4-7 days         | High       |

---

## Summary Statistics

| Metric                         | Count | Percentage     |
| ------------------------------ | ----- | -------------- |
| **Total Models**               | 42    | 100%           |
| **Models With Audit Trail**    | 20    | 47%            |
| **Models Without Audit Trail** | 22    | 53%            |
| **Explicit HistoricalRecords** | 4     | 10%            |
| **Inherited from Event**       | 16    | 38%            |
| **High Priority Missing**      | 6     | 27% of missing |
| **Medium Priority Missing**    | 2     | 9% of missing  |
| **Low Priority Missing**       | 14    | 64% of missing |

### By App

| App                         | Total | With Audit | Without | Coverage |
| --------------------------- | ----- | ---------- | ------- | -------- |
| **patients**                | 5     | 2          | 3       | 40%      |
| **events**                  | 8     | 8          | 0       | 100%     |
| **accounts**                | 1     | 1          | 1       | 50%      |
| **dailynotes**              | 1     | 1          | 0       | 100%     |
| **dischargereports**        | 1     | 1          | 0       | 100%     |
| **historyandphysicals**     | 1     | 1          | 0       | 100%     |
| **mediafiles**              | 5     | 3          | 2       | 60%      |
| **outpatientprescriptions** | 2     | 1          | 1       | 50%      |
| **pdf_forms**               | 2     | 1          | 1       | 50%      |
| **simplenotes**             | 1     | 1          | 0       | 100%     |
| **botauth**                 | 6     | 0          | 6       | 0%\*     |
| **drugtemplates**           | 3     | 0          | 3       | 0%       |
| **matrix_integration**      | 3     | 0          | 3       | 0%       |
| **sample_content**          | 1     | 0          | 1       | 0%       |
| **pdfgenerator**            | 0     | 0          | 0       | N/A      |
| **research**                | 0     | 0          | 0       | N/A      |

\*Note: Bot auth has 3 dedicated audit log models (MatrixBindingAuditLog, BotClientAuditLog, DelegationAuditLog)

---

## Conclusion

The current audit trail implementation provides **strong coverage for clinical events** (100% of event types tracked) but has **significant gaps in supporting models**:

**Strengths**:

- ✅ All clinical documentation fully tracked
- ✅ Patient personal data changes tracked
- ✅ Event-based audit trail is comprehensive

**Weaknesses**:

- ❌ Patient admissions and record numbers not tracked
- ❌ Form and drug templates not tracked
- ❌ Hospital configuration (wards) not tracked
- ❌ Tag assignments to patients not tracked

**Recommendation**: Implement Priority 1 models first (2-3 days effort) to close the most critical security gaps, particularly PatientAdmission and PatientRecordNumber which affect patient identification and care tracking.

---

**Report End**
