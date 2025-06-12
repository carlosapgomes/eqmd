# Hospital Records Management

## Overview

Hospital Records (PatientHospitalRecord) track a patient's treatment history at each hospital. These records:
- Maintain historical relationships even when patient status changes
- Enable cross-hospital access for outpatients
- Track admission/discharge dates and record numbers
- Support the new patient-hospital relationship model

## Hospital Assignment vs Hospital Records

### Current Hospital Assignment (`current_hospital`)
- **Purpose**: Tracks where admitted patients are currently located
- **Required for**: Inpatient, Emergency, Transferred statuses
- **Automatically cleared**: When patient becomes Outpatient or Discharged
- **Access Control**: Used for strict hospital access for admitted patients

### Hospital Records (`PatientHospitalRecord`)
- **Purpose**: Historical treatment records at each hospital
- **Persistent**: Maintained regardless of current patient status
- **Access Control**: Used for broader outpatient access across hospitals
- **Unique Records**: One record per patient per hospital

## Adding a Hospital Record

1. Navigate to a patient's detail page
2. Click "Add Hospital Record"
3. Fill in required information:
   - Hospital (required)
   - Record Number (unique per hospital)
   - First Admission Date (optional)
   - Last Admission Date (optional)
   - Last Discharge Date (optional)
4. Click "Save" to create the record

## Managing Patient Status and Hospital Assignment

### Admitting a Patient (Outpatient → Inpatient/Emergency)

1. Navigate to patient's detail page
2. Click "Edit Patient"
3. Change status to "Inpatient" or "Emergency"
4. **Hospital field appears automatically**
5. Select the admitting hospital (required)
6. Enter bed/room information if available
7. Click "Save" - system automatically:
   - Sets `current_hospital`
   - Updates `last_admission_date`
   - Creates/updates PatientHospitalRecord

### Discharging a Patient (Inpatient → Discharged/Outpatient)

1. Navigate to patient's detail page
2. Click "Edit Patient"
3. Change status to "Discharged" or "Outpatient"
4. **Hospital field becomes hidden/optional**
5. Click "Save" - system automatically:
   - Clears `current_hospital`
   - Updates `last_discharge_date`
   - Preserves PatientHospitalRecord for access control

### Transferring a Patient

1. Navigate to patient's detail page
2. Click "Edit Patient"
3. Change status to "Transferred" (if not already)
4. Select the new hospital
5. Update bed/room information
6. Click "Save" - system automatically:
   - Updates `current_hospital`
   - Creates/updates PatientHospitalRecord for new hospital

## Access Control Through Hospital Records

### For Admitted Patients
- Access controlled by `current_hospital` only
- Staff must be in same hospital as patient
- Strict hospital isolation

### For Outpatients/Discharged Patients
- Access controlled by PatientHospitalRecord history
- Staff can access patients from any hospital where:
  - Patient has historical records, AND
  - Staff belongs to that hospital
- Enables continuity of care across facilities

## Best Practices

### Record Management
- Always create PatientHospitalRecord when patient receives treatment at a hospital
- Use unique record numbers per hospital
- Keep admission/discharge dates accurate
- Don't delete hospital records (they enable access control)

### Status Changes
- Use appropriate status transitions (Outpatient → Inpatient → Discharged)
- Let the system automatically manage hospital assignments
- Verify hospital field visibility matches status requirements

### Multi-Hospital Patients
- Outpatients can have records at multiple hospitals
- Each hospital maintains separate record numbers
- Historical records enable cross-hospital collaboration

### Data Integrity
- Hospital records should reflect actual treatment relationships
- Admission dates should match medical records
- Record numbers should follow hospital conventions