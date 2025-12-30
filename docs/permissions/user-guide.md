# EquipeMed Permission System - User Guide

## Overview

This guide explains how the EquipeMed permission system works from a user perspective, including role-based access control and permission rules for single hospital operations.

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

**Full Access** - Complete control over all system features (same as Medical Doctors)

**Permissions:**

- ✅ View, create, edit, and delete patients
- ✅ Change patient status (including discharge)
- ✅ Edit patient personal data
- ✅ View, create, edit, and delete medical events
- ✅ Manage hospital and ward information
- ✅ Edit/delete own medical records within 24 hours
- ✅ Manage patient record numbers and admissions
- ✅ Access all patient statuses (inpatient, outpatient, emergency, discharged, transferred)

**Special Privileges:**

- Identical permissions to Medical Doctors
- Full system access for training and clinical work
- No restrictions on patient management or status changes

### Nurses

**Extended Patient Management** - Comprehensive patient care capabilities

**Permissions:**

- ✅ View, create, and edit patients
- ✅ Manage patient record numbers and admissions
- ✅ Limited patient status changes (cannot discharge)
- ✅ Can admit emergency patients to inpatient status
- ❌ Cannot delete patients
- ❌ Cannot edit patient personal data
- ✅ View, create, edit, and delete medical events
- ✅ View hospital and ward information
- ✅ Edit/delete own medical records within 24 hours
- ✅ Full media file management (photos, videos, series)
- ✅ Full access to daily notes and simple notes
- ✅ View-only access to history & physicals (physician documents)

**Special Rules:**

- Can change emergency patients to inpatient status
- Cannot perform patient discharge
- Can create and manage patient records
- Full access to media files for nursing documentation
- Cannot create or edit history & physical documents (physician responsibility)

### Physiotherapists

**Limited Access** - Therapy documentation only

**Permissions:**

- ✅ View patients (read-only access)
- ❌ Cannot create, edit, or delete patients
- ❌ Cannot change patient status
- ❌ Cannot edit patient personal data
- ❌ Cannot manage patient admissions or discharges
- ✅ View medical events (read-only)
- ❌ Cannot create or edit medical events
- ✅ View hospital and ward information (read-only)
- ✅ Create, edit, and delete therapy simple notes only

**Focus:**

- Physiotherapy documentation through simple notes
- View-only access to patient information
- No involvement in patient management or medical decisions
- Focused on therapeutic care documentation

### Students

**Supervised Learning Access** - Focused on observation and supervised documentation

**Permissions:**

- ✅ View all patients (learning purposes)
- ✅ View all medical documentation (daily notes, H&P, prescriptions)
- ✅ View medical events and hospital information
- ✅ Create simple notes for supervised observations
- ✅ Edit own simple notes for corrections
- ✅ Add photos and photo series for wound/surgery documentation
- ✅ View medical media files
- ✅ View PDF form templates
- ❌ Cannot create daily notes (too formal for students)
- ❌ Cannot create, edit, or delete patients
- ❌ Cannot change patient status or personal data
- ❌ Cannot submit PDF forms

**Learning Model:**

- Simple notes serve as supervised observations
- Residents review student notes and promote to formal records
- Media documentation helps with wound and surgical progress tracking
- Read-only access to formal medical documentation for learning

## Single Hospital Environment

### Hospital Configuration

EquipeMed is configured for single hospital operation using environment-based configuration:

- Hospital name, address, and contact information set via environment variables
- No hospital selection required - all users work within the same hospital
- Simplified patient access without hospital context restrictions

## Patient Access Rules

### General Access Rules

1. **Universal Access**: All medical staff can access all patients in the single hospital environment
2. **Role-Based Capabilities**: Your profession determines what actions you can perform
3. **Time-Based Restrictions**: Medical records can only be edited for 24 hours
4. **Status-Based Workflows**: Different patient statuses may have different management workflows

### Patient Status Types

- **Outpatient (Ambulatorial)**: Patients receiving care without admission
- **Inpatient (Internado)**: Patients admitted to the hospital  
- **Emergency (Emergência)**: Patients in emergency care
- **Discharged (Alta)**: Recently discharged patients
- **Transferred (Transferido)**: Patients transferred between departments or facilities

### Access Rules by Role

**Universal Patient Access** - All medical staff can access all patients

| Role | Patient Access | Capabilities |
|------|---------------|-------------|
| **Medical Doctors** | ✅ All patients | Full management capabilities |
| **Residents** | ✅ All patients | Full management capabilities (identical to doctors) |
| **Nurses** | ✅ All patients | Extended patient management, cannot discharge |
| **Physiotherapists** | ✅ All patients | View-only access, therapy documentation |
| **Students** | ✅ All patients | Supervised learning, simple notes and media only |

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
| **Outpatient → Inpatient** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Emergency → Inpatient** | ✅ | ✅ | ✅ (Special Rule) | ❌ | ❌ |
| **Inpatient → Outpatient** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Any → Discharged** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Any → Transferred** | ✅ | ✅ | ✅ | ❌ | ❌ |

### Special Rules

- **Nurse Emergency Rule**: Nurses can admit emergency patients to inpatient status
- **Doctor & Resident Discharge Rule**: Only doctors and residents can discharge patients

## Personal Data Protection

### Patient Personal Data

Patient personal data includes:

- Name, date of birth, contact information
- Identification numbers (ID, fiscal number, health card)
- Address and emergency contacts
- Insurance information

### Who Can Edit Personal Data?

- **Medical Doctors & Residents**: Only doctors and residents can modify patient personal information
- **Universal Access**: All doctors and residents can edit personal data for any patient in the hospital

### Why These Restrictions?

- **Data Integrity**: Ensures accurate patient information
- **Legal Compliance**: Meets healthcare data protection requirements
- **Audit Trail**: Tracks who makes changes to sensitive information
- **Security**: Prevents unauthorized modifications

## Common Workflows

### Starting Your Shift

1. **Log In**: Use your EquipeMed credentials
2. **Access Dashboard**: View patient statistics and recent patients
3. **Begin Work**: Access patients and create medical records as needed

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

## Troubleshooting

### "You don't have permission" Messages

- **Check Role**: Verify your role has the required permissions for the action
- **Time Limits**: Check if 24-hour editing window has expired
- **Business Logic**: Some restrictions are enforced by business rules (e.g., only doctors can discharge)

### Cannot Access Patients

- **Role Restrictions**: Verify your role allows the specific type of patient access
- **Authentication**: Ensure you are properly logged in

### Cannot Edit Medical Records

- **Creator Check**: You can only edit your own records
- **Time Limit**: Records can only be edited within 24 hours
- **Permission Level**: Verify you have event editing permissions

## Getting Help

### Technical Support

- **System Administrator**: Contact your IT department
- **User Manual**: Refer to this documentation
- **Training**: Request additional training if needed

### Permission Issues

- **Role Assignment**: Contact your supervisor or HR department
- **Group Membership**: Verify your profession type is correctly set
- **System Access**: Ensure your account is properly configured

### Medical Record Questions

- **Clinical Supervisor**: Consult with medical staff supervisors
- **Compliance Officer**: For audit and compliance questions
- **Training Department**: For workflow and procedure questions

## Best Practices

### Security

- **Log Out**: Always log out when finished
- **Personal Data**: Be careful when editing patient personal information
- **Access Control**: Don't share login credentials
- **Role Awareness**: Understand your role's capabilities and limitations

### Medical Records

- **Timely Entry**: Create medical records promptly
- **Accurate Information**: Ensure all information is correct
- **Complete Documentation**: Include all relevant details
- **24-Hour Rule**: Edit records within the time limit if needed

### Patient Management

- **Verify Identity**: Always confirm patient identity
- **Status Updates**: Keep patient status current
- **Role Awareness**: Understand your role's limitations
- **Collaboration**: Work effectively with other medical staff

### System Usage

- **Regular Updates**: Keep patient information current
- **Proper Workflows**: Follow established procedures
- **Error Reporting**: Report system issues promptly
- **Training**: Stay updated on system changes
