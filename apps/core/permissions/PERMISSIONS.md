# Permission Reference

## What Each Role Can Do

### Medical Doctor

✅ Add/edit/delete patients  
✅ Create medical events and notes  
✅ Upload medical images/videos  
✅ Fill hospital forms  
✅ Manage prescriptions  
✅ Assign/remove patient tags (instances)  
✅ Discharge patients and declare death  
✅ Edit patient personal data  
❌ Create/edit user accounts  
❌ Access Django admin  
❌ Modify system settings  
❌ Create/edit tag templates (AllowedTag)  

### Resident

✅ Add/edit/delete patients  
✅ Create medical events and notes  
✅ Upload medical images/videos  
✅ Fill hospital forms  
✅ Manage prescriptions  
✅ Assign/remove patient tags (instances)  
✅ Discharge patients and declare death  
✅ Edit patient personal data  
❌ Create/edit user accounts  
❌ Access Django admin  
❌ Modify system settings  
❌ Create/edit tag templates (AllowedTag)  

### Physiotherapist

✅ Add/edit/delete patients (for therapy needs)  
✅ Create medical events and therapy notes  
✅ Upload therapy-related media  
✅ Fill hospital forms  
✅ Assign/remove patient tags  
❌ Create prescriptions (not in scope)  
❌ Discharge patients or declare death  
❌ Edit patient personal data  
❌ Create/edit user accounts  
❌ Access Django admin  
❌ Modify system settings  

### Nurse

✅ View/edit patient information (limited)  
✅ Create basic medical events  
✅ Write nursing notes  
✅ View medical media  
✅ Fill hospital forms  
❌ Delete patients  
❌ Discharge patients or declare death  
❌ Create prescriptions  
❌ Edit patient personal data  
❌ Manage user accounts  
❌ Access Django admin  

### Student

✅ View patient information (read-only)  
✅ View medical events and notes  
✅ Create learning notes (dailynotes, simplenotes)  
✅ View medical media  
✅ Fill forms for practice  
❌ Add/edit/delete patients  
❌ Discharge patients or declare death  
❌ Create prescriptions  
❌ Edit patient personal data  
❌ Manage user accounts  
❌ Access Django admin  

### User Manager (Administrative)

✅ Create/edit user accounts  
✅ Assign users to medical roles  
✅ View user profiles  
✅ View available groups  
❌ Access patient data  
❌ View medical events  
❌ Access clinical information  
❌ Modify group permissions  

### Superuser (IT Administrator)

✅ Full system access  
✅ Technical administration  
✅ Change status of deceased patients (for data corrections)  
✅ Override all permission restrictions  
✅ Access Django admin  
✅ Modify system settings  

## Permission Categories

### Medical Permissions (Clinical Staff Only)

```python
MEDICAL_PERMISSIONS = [
    # Patient management
    'patients.view_patient',
    'patients.add_patient',
    'patients.change_patient',
    'patients.delete_patient',

    # Patient tags (instances, not templates)
    'patients.view_tag',
    'patients.add_tag',
    'patients.change_tag',
    'patients.delete_tag',

    # Medical events
    'events.*',
    'dailynotes.*',
    'historyandphysicals.*',
    'simplenotes.*',

    # Medical media
    'mediafiles.*',

    # Hospital forms
    'pdf_forms.*',

    # Prescriptions (doctors/residents only)
    'outpatientprescriptions.*',

    # View-only for templates
    'sample_content.view_samplecontent',
]
```

### Administrative Permissions (Should NEVER go to medical staff)

```python
ADMIN_ONLY_PERMISSIONS = [
    'auth.*',           # User/group management
    'admin.*',          # Django admin logs
    'accounts.*',       # User account management
    'contenttypes.*',   # System models
    'sessions.*',       # Session management
    'sites.*',          # Site configuration
    'patients.add_allowedtag',    # Tag template management
    'patients.change_allowedtag',
    'patients.delete_allowedtag',
]
```

## Role-Based Permission Implementation

### Doctor/Resident Permissions

```python
def _get_doctor_permissions(self):
    """Full clinical permissions - NO administrative access."""
    return [
        # Full patient access
        'patients.view_patient', 'patients.add_patient',
        'patients.change_patient', 'patients.delete_patient',

        # Patient tag management (instances, not templates)
        'patients.view_tag', 'patients.add_tag',
        'patients.change_tag', 'patients.delete_tag',

        # Medical events with time-limited editing
        'events.view_event', 'events.add_event',
        'events.change_event', 'events.delete_event',

        # All medical documentation
        'dailynotes.*', 'historyandphysicals.*',
        'outpatientprescriptions.*',

        # Medical media management
        'mediafiles.*',

        # Hospital forms
        'pdf_forms.*',

        # Template viewing only
        'sample_content.view_samplecontent',
    ]
```

### Nurse Permissions

```python
def _get_nurse_permissions(self):
    """Limited clinical permissions."""
    return [
        # Patient viewing and limited updates
        'patients.view_patient', 'patients.change_patient',

        # Basic event management
        'events.view_event', 'events.add_event',

        # Nursing documentation
        'dailynotes.*',

        # Media viewing
        'mediafiles.view_*',

        # Forms (view/fill only)
        'pdf_forms.view_*', 'pdf_forms.add_pdfformsubmission',
    ]
```

### Physiotherapist Permissions

```python
def _get_physiotherapist_permissions(self):
    """Clinical permissions for physiotherapy work."""
    permissions = []
    
    # Full patient access (same as doctors for therapy needs)
    permissions.extend(self._get_patient_related_permissions())
    
    # Full event management for therapy documentation
    permissions.extend(self._get_event_permissions())
    
    # Medical documentation apps
    permissions.extend(self._get_app_permissions('dailynotes'))
    permissions.extend(self._get_app_permissions('historyandphysicals'))
    permissions.extend(self._get_app_permissions('simplenotes'))
    
    # Media for therapy documentation
    permissions.extend(self._get_app_permissions('mediafiles'))
    
    # PDF forms
    permissions.extend(self._get_app_permissions('pdf_forms'))
    
    # View sample content
    permissions.extend(self._get_view_permissions('sample_content'))
    
    # NO prescriptions (not in physiotherapist scope)
    # NO user management or admin permissions
    
    return permissions
```

### Student Permissions

```python
def _get_student_permissions(self):
    """Read-only permissions for medical students."""
    permissions = []
    
    # View-only patient access
    permissions.extend(self._get_patient_view_permissions())
    
    # View-only event access  
    permissions.extend(self._get_event_view_permissions())
    
    # Can create basic notes for learning (with supervision)
    permissions.extend(self._get_app_permissions('dailynotes'))
    permissions.extend(self._get_app_permissions('simplenotes'))
    
    # View medical media
    permissions.extend(self._get_view_permissions('mediafiles'))
    
    # View and fill forms (learning purposes)
    permissions.extend(self._get_view_permissions('pdf_forms'))
    permissions.append('pdf_forms.add_pdfformsubmission')
    
    # View sample content
    permissions.extend(self._get_view_permissions('sample_content'))
    
    # NO prescriptions
    # NO patient management (add/change/delete)
    # NO user management or admin permissions
    
    return permissions
```

### User Manager Permissions

```python
def _create_user_manager_group(self):
    """For administrative staff who manage user accounts."""
    group, created = Group.objects.get_or_create(name='User Managers')

    permissions = [
        # User account management
        'accounts.view_eqmdcustomuser',
        'accounts.add_eqmdcustomuser',
        'accounts.change_eqmdcustomuser',

        # Profile management
        'accounts.view_userprofile',
        'accounts.change_userprofile',

        # Group assignment (not creation)
        'auth.view_group',

        # NO permission to modify system permissions
        # NO access to medical data
    ]

    group.permissions.set(permissions)
```

## Security Principles

### 1. Medical ≠ Administrative

Clear separation between clinical work and system administration.

### 2. Least Privilege

Each role gets minimum permissions necessary for their function.

### 3. No Privilege Escalation

Medical staff cannot gain administrative access through any means.

### 4. Audit Ready

Foundation in place for future audit logging requirements.

## Validation Checklist

- [ ] Medical staff cannot access Django admin interface
- [ ] Medical staff cannot create/edit/delete user accounts
- [ ] Medical staff retain all necessary clinical permissions
- [ ] User managers can manage accounts but not access patient data
- [ ] Superuser retains full system access
- [ ] All existing medical functionality works correctly
- [ ] No medical role has administrative permissions
- [ ] Administrative roles have no access to clinical data

## Implementation Commands

```bash
# Set up new permission groups
uv run python manage.py setup_groups --force

# Audit permission system
uv run python manage.py permission_audit --action=report

# Verify medical roles have no admin permissions
uv run python manage.py permission_audit --action=verify_medical_roles

# Assign user to group
uv run python manage.py user_permissions --action=assign
```

## Emergency Access

In case of system issues:

- **Superuser** can override all restrictions
- **IT administrators** have full system access
- **Emergency procedures** documented separately

## Future Enhancements

- **Audit logging**: Can be added for compliance requirements
- **Time-based permissions**: Not needed for current support tool context
- **Patient-specific permissions**: Current universal access model is appropriate
- **Advanced role management**: Keep simple for this context
