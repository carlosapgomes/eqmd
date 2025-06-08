# EquipeMed Permission System - User Guide

## Overview

This guide explains how the EquipeMed permission system works from a user perspective, including role-based access control, hospital context management, and permission rules.

## User Roles and Permissions

EquipeMed uses a role-based permission system based on medical professions. Each role has different levels of access to patients, medical records, and system features.

### Medical Doctors
**Full Access** - Complete control over all system features

**Permissions:**
- ✅ View, create, edit, and delete patients
- ✅ Change patient status (including discharge)
- ✅ Edit patient personal data
- ✅ View, create, edit, and delete medical events
- ✅ Manage hospital and ward information
- ✅ Access patients in any hospital (with proper context)
- ✅ Edit/delete own medical records within 24 hours

**Special Privileges:**
- Only doctors can discharge patients
- Only doctors can edit patient personal information
- Full access to all patient statuses (inpatient, outpatient, emergency, discharged, transferred)

### Residents
**Full Hospital Access** - Complete access to patients in current hospital

**Permissions:**
- ✅ View, create, edit, and delete patients in current hospital
- ✅ Change patient status (except discharge)
- ❌ Cannot discharge patients
- ❌ Cannot edit patient personal data
- ✅ View, create, edit, and delete medical events
- ✅ View hospital and ward information
- ✅ Edit/delete own medical records within 24 hours

**Restrictions:**
- Must have hospital context selected
- Cannot access patients in other hospitals
- Cannot perform final patient discharge

### Nurses
**Limited Patient Management** - Patient care with restrictions

**Permissions:**
- ✅ View and edit patients in current hospital
- ✅ Limited patient status changes (cannot discharge)
- ✅ Can admit emergency patients to inpatient status
- ❌ Cannot delete patients
- ❌ Cannot edit patient personal data
- ✅ View, create, edit, and delete medical events
- ✅ View hospital and ward information
- ✅ Edit/delete own medical records within 24 hours

**Special Rules:**
- Can change emergency patients to inpatient status
- Cannot perform patient discharge
- Limited to current hospital context

### Physiotherapists
**Full Hospital Access** - Similar to residents

**Permissions:**
- ✅ View, create, edit, and delete patients in current hospital
- ✅ Change patient status (except discharge)
- ❌ Cannot discharge patients
- ❌ Cannot edit patient personal data
- ✅ View, create, edit, and delete medical events
- ✅ View hospital and ward information
- ✅ Edit/delete own medical records within 24 hours

**Restrictions:**
- Must have hospital context selected
- Cannot access patients in other hospitals
- Cannot perform final patient discharge

### Students
**View-Only Access** - Limited to outpatients for learning

**Permissions:**
- ✅ View outpatients only in current hospital
- ❌ Cannot view inpatients, emergency, or discharged patients
- ❌ Cannot create, edit, or delete patients
- ❌ Cannot change patient status
- ❌ Cannot edit patient personal data
- ✅ View medical events (limited)
- ✅ View hospital and ward information
- ❌ Cannot edit or delete medical records

**Restrictions:**
- Limited to outpatients only
- Must have hospital context selected
- Read-only access to most features

## Hospital Context Management

### What is Hospital Context?

Hospital context determines which hospital you are currently working in. This is essential for:
- Accessing patients in your current hospital
- Ensuring data privacy and security
- Complying with hospital-specific workflows

### Setting Your Hospital Context

1. **Automatic Prompt**: If you don't have a hospital context set, you'll be prompted to select one
2. **Manual Selection**: Go to "Select Hospital" in the navigation menu
3. **Hospital Selection Page**: Choose from hospitals you have access to
4. **Session Persistence**: Your selection persists across browser sessions

### Hospital Context Rules

- **Required for Most Operations**: You must have a hospital context to access patients
- **Hospital Isolation**: You can only access patients in your selected hospital
- **Easy Switching**: You can change hospitals at any time through the interface
- **Security**: Prevents accidental access to patients in other hospitals

## Patient Access Rules

### General Access Rules

1. **Hospital Context Required**: You must have selected a current hospital
2. **Role-Based Access**: Your profession determines what you can do
3. **Patient Status Matters**: Some roles have restrictions based on patient status
4. **Time-Based Restrictions**: Medical records can only be edited for 24 hours

### Patient Status Types

- **Outpatient**: Patients receiving care but not admitted
- **Inpatient**: Patients admitted to the hospital
- **Emergency**: Patients in emergency care
- **Discharged**: Patients who have been discharged
- **Transferred**: Patients transferred to another facility

### Who Can Access Which Patients?

| Role | Outpatients | Inpatients | Emergency | Discharged | Transferred |
|------|-------------|------------|-----------|------------|-------------|
| **Medical Doctors** | ✅ All | ✅ All | ✅ All | ✅ All | ✅ All |
| **Residents** | ✅ Current Hospital | ✅ Current Hospital | ✅ Current Hospital | ✅ Current Hospital | ✅ Current Hospital |
| **Nurses** | ✅ Current Hospital | ✅ Current Hospital | ✅ Current Hospital | ✅ Current Hospital | ✅ Current Hospital |
| **Physiotherapists** | ✅ Current Hospital | ✅ Current Hospital | ✅ Current Hospital | ✅ Current Hospital | ✅ Current Hospital |
| **Students** | ✅ Current Hospital Only | ❌ No Access | ❌ No Access | ❌ No Access | ❌ No Access |

## Medical Record Rules

### Creating Medical Records

- **All Roles**: Can create medical records for patients they have access to
- **Event Types**: 10 different types of medical events available
- **Required Information**: Event type, date/time, and description
- **Patient Association**: Each event is linked to a specific patient

### Editing Medical Records

- **24-Hour Rule**: You can only edit your own medical records within 24 hours of creation
- **Creator Only**: Only the person who created the record can edit it
- **Audit Trail**: All changes are tracked for medical record integrity
- **No Backdating**: Cannot edit records older than 24 hours

### Deleting Medical Records

- **Same Rules as Editing**: 24-hour window and creator-only restriction
- **Permanent Action**: Deletion is permanent and cannot be undone
- **Audit Compliance**: Deletion is tracked for compliance purposes

## Patient Status Changes

### Who Can Change Patient Status?

| Status Change | Medical Doctors | Residents | Nurses | Physiotherapists | Students |
|---------------|-----------------|-----------|---------|------------------|----------|
| **Outpatient → Inpatient** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Emergency → Inpatient** | ✅ | ✅ | ✅ (Special Rule) | ✅ | ❌ |
| **Inpatient → Outpatient** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Any → Discharged** | ✅ Only | ❌ | ❌ | ❌ | ❌ |
| **Any → Transferred** | ✅ | ✅ | ✅ | ✅ | ❌ |

### Special Rules

- **Nurse Emergency Rule**: Nurses can admit emergency patients to inpatient status
- **Doctor Discharge Rule**: Only doctors can discharge patients
- **Hospital Context Required**: Must be in the same hospital as the patient

## Personal Data Protection

### Patient Personal Data

Patient personal data includes:
- Name, date of birth, contact information
- Identification numbers (ID, fiscal number, health card)
- Address and emergency contacts
- Insurance information

### Who Can Edit Personal Data?

- **Medical Doctors Only**: Only doctors can modify patient personal information
- **Hospital Context Rules**:
  - **Outpatients**: Any doctor can edit
  - **Inpatients/Emergency/Discharged/Transferred**: Doctor must be in the same hospital

### Why These Restrictions?

- **Data Integrity**: Ensures accurate patient information
- **Legal Compliance**: Meets healthcare data protection requirements
- **Audit Trail**: Tracks who makes changes to sensitive information
- **Security**: Prevents unauthorized modifications

## Common Workflows

### Starting Your Shift

1. **Log In**: Use your EquipeMed credentials
2. **Select Hospital**: Choose your current hospital if not already set
3. **Access Dashboard**: View patient statistics and recent patients
4. **Begin Work**: Access patients and create medical records as needed

### Accessing a Patient

1. **Search**: Use the patient search feature
2. **Select Patient**: Click on the patient from search results
3. **View Details**: Review patient information and medical history
4. **Take Action**: Create medical records, update status, etc. (based on your role)

### Creating a Medical Record

1. **Access Patient**: Navigate to the patient's detail page
2. **Add Event**: Click "Add Medical Event" or similar button
3. **Select Type**: Choose the appropriate event type
4. **Fill Details**: Enter event date/time and description
5. **Save**: Submit the medical record

### Changing Patient Status

1. **Access Patient**: Navigate to the patient's detail page
2. **Edit Patient**: Click the edit button (if you have permission)
3. **Update Status**: Change the patient status field
4. **Save Changes**: Submit the form

### Switching Hospitals

1. **Navigation Menu**: Click "Select Hospital" in the menu
2. **Choose Hospital**: Select from available hospitals
3. **Confirm Selection**: Your hospital context will be updated
4. **Continue Work**: Access patients in the new hospital context

## Troubleshooting

### "You don't have permission" Messages

- **Check Role**: Verify your role has the required permissions
- **Hospital Context**: Ensure you have selected a hospital
- **Patient Location**: Verify the patient is in your current hospital
- **Time Limits**: Check if 24-hour editing window has expired

### Cannot Access Patients

- **Hospital Context**: Make sure you have selected a hospital
- **Patient Status**: Students can only access outpatients
- **Role Restrictions**: Verify your role allows patient access

### Cannot Edit Medical Records

- **Creator Check**: You can only edit your own records
- **Time Limit**: Records can only be edited within 24 hours
- **Permission Level**: Verify you have event editing permissions

### Hospital Selection Issues

- **Available Hospitals**: You can only select hospitals you have access to
- **Session Issues**: Try logging out and back in
- **Contact Admin**: If you need access to additional hospitals

## Getting Help

### Technical Support

- **System Administrator**: Contact your IT department
- **User Manual**: Refer to this documentation
- **Training**: Request additional training if needed

### Permission Issues

- **Role Assignment**: Contact your supervisor or HR department
- **Hospital Access**: Request access through proper channels
- **Group Membership**: Verify your profession type is correctly set

### Medical Record Questions

- **Clinical Supervisor**: Consult with medical staff supervisors
- **Compliance Officer**: For audit and compliance questions
- **Training Department**: For workflow and procedure questions

## Best Practices

### Security

- **Log Out**: Always log out when finished
- **Hospital Context**: Only select hospitals where you're currently working
- **Personal Data**: Be careful when editing patient personal information
- **Access Control**: Don't share login credentials

### Medical Records

- **Timely Entry**: Create medical records promptly
- **Accurate Information**: Ensure all information is correct
- **Complete Documentation**: Include all relevant details
- **24-Hour Rule**: Edit records within the time limit if needed

### Patient Management

- **Verify Identity**: Always confirm patient identity
- **Status Updates**: Keep patient status current
- **Hospital Context**: Ensure you're in the correct hospital
- **Role Awareness**: Understand your role's limitations

### System Usage

- **Regular Updates**: Keep patient information current
- **Proper Workflows**: Follow established procedures
- **Error Reporting**: Report system issues promptly
- **Training**: Stay updated on system changes
