# Patient Management

## Creating a New Patient

1. Navigate to Patients > Add Patient
2. Fill in the required fields:
   - Name
   - Birthday
   - Status (Inpatient/Outpatient/Emergency/Discharged/Transferred)
3. Optional: Add tags, contact information, and other details
4. Click "Save" to create the patient record

## Viewing Patients

1. Navigate to Patients > All Patients
2. Use filters to narrow down the patient list:
   - Status
   - Tags
   - Name/ID search
3. Click on a patient name to view detailed information

## Patient Access Rules

### Universal Access
- **All Medical Staff**: Can access all patients regardless of status
- **Simple Permission Model**: Single hospital environment eliminates hospital-based restrictions
- **Role-Based Capabilities**: Different roles have different action permissions

### Role-Based Permissions
- **Doctors/Residents**: 
  - Full access to all patients
  - Can discharge patients
  - Can modify patient personal data
  - Can change any patient status
- **Nurses/Physiotherapists/Students**: 
  - Full access to all patients
  - Limited status changes (cannot discharge)
  - Cannot modify patient personal data
  - Can create and edit medical records

## Editing Patient Information

1. Navigate to the patient detail page
2. Click "Edit" to modify patient information
3. **Status Changes**: Simple status updates without hospital dependencies
4. **Personal Data Changes**: Only available to doctors/residents
5. Click "Save" to apply changes

## Patient Status Explanation

- **Outpatient (Ambulatorial)**: Receiving care without hospital admission
- **Inpatient (Internado)**: Currently admitted to the hospital
- **Emergency (Emergência)**: In emergency care
- **Discharged (Alta)**: Recently discharged from hospital
- **Transferred (Transferido)**: Transferred to another facility

## Patient Search and Discovery

### Search Features
- **Name Search**: Find patients by first name, last name, or full name
- **ID Search**: Search by patient ID or fiscal/health card numbers
- **Tag Filtering**: Filter patients by assigned tags
- **Status Filtering**: View patients by current status

### Dashboard Widgets
- **Recent Patients**: Shows recently created or updated patients
- **Patient Statistics**: Displays count by status type
- **Quick Access**: Fast navigation to common patient operations

## Patient Tags

### Tag Management
- **Color-Coded System**: Visual organization of patient categories
- **Admin-Managed**: Tags created and managed through web admin interface
- **Multiple Tags**: Patients can have multiple tags for flexible categorization
- **Search Integration**: Tags available as filters in patient search

### Common Tag Categories
- Medical specialties (Cardiology, Neurology, etc.)
- Treatment types (Surgery, Rehabilitation, etc.)
- Priority levels (High priority, Routine, etc.)
- Care plans (Diabetes care, Post-op, etc.)

## Integration with Medical Records

### Event System Integration
- **Medical Events**: All patient events linked to patient records
- **Timeline View**: Complete chronological view of patient care
- **Event Types**: Daily notes, history/physical, media files, prescriptions
- **Universal Access**: All medical staff can view patient timeline

### Event Creation
- **Quick Creation**: Create events directly from patient detail page
- **Template Support**: Use sample content templates for common event types
- **Media Support**: Add photos, photo series, and video clips to patient records
- **Audit Trail**: Complete tracking of who created/modified each event

## Security and Privacy

### Data Protection
- **Personal Data**: Protected modification (doctors/residents only)
- **Event Creator Rights**: Only creators can edit/delete their events (24h window)
- **Audit Logging**: Complete tracking of patient record access and modifications
- **Role-Based Display**: Interface adapts based on user permissions

### Medical Record Integrity
- **Time-Based Editing**: Medical events can only be edited within 24 hours
- **Creator Protection**: Events protected from unauthorized modification
- **Status Protection**: Discharge operations restricted to qualified staff
- **Data Validation**: Comprehensive validation of patient information

## Best Practices

### Patient Data Entry
1. **Complete Information**: Enter all available patient details
2. **Accurate Status**: Ensure patient status reflects current care situation
3. **Consistent Naming**: Use standard naming conventions for patient names
4. **Tag Usage**: Apply relevant tags for better organization and discovery

### Ongoing Patient Management
1. **Regular Updates**: Keep patient status current as care progresses
2. **Event Documentation**: Create timely medical event records
3. **Status Transitions**: Update status when patient care level changes
4. **Data Quality**: Review and correct patient information as needed

### Team Collaboration
1. **Shared Access**: Leverage universal patient access for team care coordination
2. **Event Communication**: Use daily notes and events for team communication
3. **Tag Coordination**: Use consistent tagging across the medical team
4. **Status Awareness**: Monitor patient status changes for care coordination