# Patient Management

## Creating a New Patient

1. Navigate to Patients > Add Patient
2. Fill in the required fields:
   - Name
   - Birthday
   - Status (Inpatient/Outpatient/Emergency/Discharged/Transferred)
3. **Hospital Assignment**: 
   - Hospital field appears automatically based on status selection
   - Required for: Inpatient, Emergency, Transferred patients
   - Not required for: Outpatient, Discharged patients
4. Optional: Add tags, contact information, and other details
5. Click "Save" to create the patient record

## Viewing Patients

1. Navigate to Patients > All Patients
2. Use filters to narrow down the patient list:
   - Status
   - Hospital (searches both current hospital and treatment history)
   - Tags
3. Click on a patient name to view detailed information

## Patient Access Rules

### Hospital-Based Access Control
- **Admitted Patients** (Inpatient, Emergency, Transferred):
  - Strict hospital access - only staff from patient's current hospital can access
  - Requires active hospital assignment
- **Outpatients & Discharged Patients**:
  - Broader access - staff can access patients from any hospital where:
    - Patient has treatment history, OR
    - Staff belongs to patient's historical hospitals
  - No current hospital assignment required

### Role-Based Permissions
- **Students**: Can only access outpatients (across all their hospitals)
- **Nurses/Physiotherapists/Residents**: Full access within permission rules
- **Doctors**: Full access and can modify patient personal data

## Editing Patient Information

1. Navigate to the patient detail page
2. Click "Edit" to modify patient information
3. **Status Changes**: Hospital field visibility updates automatically
   - Changing to Inpatient/Emergency/Transferred: Hospital field becomes required
   - Changing to Outpatient/Discharged: Hospital field is cleared automatically
4. Click "Save" to apply changes

## Patient Status Explanation

- **Outpatient (Ambulatorial)**: Receiving care without hospital admission
- **Inpatient (Internado)**: Currently admitted to a hospital (requires hospital assignment)
- **Emergency (Emergência)**: In emergency care (requires hospital assignment)
- **Discharged (Alta)**: Recently discharged from hospital
- **Transferred (Transferido)**: Transferred between hospitals (requires hospital assignment)

## Hospital Records

Each patient maintains a **PatientHospitalRecord** for every hospital where they receive treatment:
- Tracks first and last admission dates
- Maintains unique record numbers per hospital
- Preserves treatment history even when patient status changes
- Used for cross-hospital access permissions for outpatients