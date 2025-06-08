## Key Concepts

### User Roles

Users in EquipeMed can have one of the following roles, determined by their `profession_type`:

- **Medical Doctor** (0): Full access to patient data and can change patient status
- **Resident** (1): Similar to doctors but with some restrictions
- **Nurse** (2): Can view and edit patient data but cannot change patient status
- **Physiotherapist** (3): Limited access to patient data
- **Student** (4): Limited access to patient data

### Hospital Context

A key concept in EquipeMed is the "hospital context":

- Users can be members of multiple hospitals
- Users can only be logged into one hospital at a time
- The current hospital is stored in the user's session
- Access to inpatient data is restricted based on the user's current hospital

### Patient Status

Patients can have one of the following statuses:

- **Inpatient** (0): Currently admitted to a hospital
- **Outpatient** (1): Not currently admitted
- **Deceased** (2): Deceased

Access to patient data depends on the patient's status and the user's hospital context.

## Permission Rules

### Patient Access

1. **All users can access outpatient data**
2. **All users can access inpatient data (except changing status or personal data)**
3. **For modifying inpatient status or personal data:**
   - Users must be members of the patient's hospital
   - Users must be logged into the patient's hospital

### Patient Status Changes

1. **Only medical doctors can change patient status**
2. **For inpatients:**
   - The doctor must be a member of the patient's hospital
   - The doctor must be logged into the patient's hospital
3. **For outpatients:**
   - Any doctor can change the status

### Patient Personal Data Changes

1. **For inpatients:**
   - Only medical doctors can change personal data
   - The doctor must be a member of the patient's hospital
   - The doctor must be logged into the patient's hospital
2. **For outpatients:**
   - Any doctor can change personal data

### Event Management

1. **All users can view and add events**
2. **Events can only be edited or deleted:**
   - By the user who created the event
   - Within 24 hours of creation
