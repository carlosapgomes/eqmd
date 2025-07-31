# Permission System Refactor Plan

## Executive Summary

**Problem**: Current permission system gives doctors administrative privileges (user management, system admin) which creates security vulnerabilities and violates principle of least privilege.

**Solution**: Refactor to clean, role-based system where medical staff have medical permissions only, and administrative functions are handled by dedicated admin roles.

**Context**: Greenfield project with no deployment constraints. System serves as quick patient data access tool parallel to main EMR.

## Current State Analysis

### Critical Issues

1. **Overprivileged Medical Roles**: Doctors can create/edit/delete users and manage system permissions
2. **Security Risk**: Medical staff have access to Django admin, groups, permissions management
3. **Compliance Risk**: No clear separation between medical and administrative functions
4. **No Audit Trail**: Permission usage not logged for compliance

### Current Permission Flow

```
setup_groups.py -> _get_admin_restricted_permissions() -> Almost all system permissions to doctors
```

## Target State

### Clean Role Separation

```
ADMIN ROLES (Non-Medical):
├── Superuser (Full system access)
└── User Manager (HR/Admin staff - user account management)

MEDICAL ROLES (Clinical Staff):
├── Doctor (Full clinical access, no admin)
├── Resident (Full clinical access, no admin)
├── Nurse (Limited clinical access)
├── Physiotherapist (Clinical access)
└── Student (Read-only clinical access)
```

### Core Principles

1. **Medical ≠ Administrative**: Clear separation of concerns
2. **Least Privilege**: Minimum permissions necessary for role
3. **Simple & Practical**: Don't overengineer for a support tool
4. **Audit Ready**: Log critical access for compliance

## Refactoring Plan

### Phase 1: Permission Audit & Cleanup (Day 1)

#### Step 1.1: Document Current State

```bash
# Create permission audit
python manage.py permission_audit --action=report --output=current_permissions.json
```

#### Step 1.2: Identify Medical vs Administrative Permissions

Create `apps/core/permissions/permission_categories.py`:

```python
# Medical permissions - what medical staff actually need
MEDICAL_PERMISSIONS = [
    # Patient management
    'patients.view_patient',
    'patients.add_patient',
    'patients.change_patient',
    'patients.delete_patient',

    # Medical events
    'events.*',
    'dailynotes.*',
    'historyandphysicals.*',

    # Medical media
    'mediafiles.*',
    'pdf_forms.*',

    # Prescriptions (doctors/residents only)
    'outpatientprescriptions.*',

    # View-only for templates
    'sample_content.view_samplecontent',
]

# Administrative permissions - should NEVER go to medical staff
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

#### Step 1.3: Back Up Current System

```bash
# Export current groups and permissions
python manage.py dumpdata auth.group auth.permission > backup_permissions.json
```

### Phase 2: New Permission Architecture (Day 2)

#### Step 2.1: Create New Group Setup Command

Replace `apps/core/management/commands/setup_groups.py` with clean implementation:

```python
# Key changes:
# 1. Remove _get_admin_restricted_permissions() - too broad
# 2. Add _get_medical_permissions() - specific to clinical needs
# 3. Add _get_user_management_permissions() - for admin roles
# 4. Implement clear role boundaries
```

#### Step 2.2: Define Medical Permission Sets

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

#### Step 2.3: Add User Management Role

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

### Phase 3: Implementation & Testing (Day 3)

#### Step 3.1: Clean Install New Permissions

```bash
# Remove existing groups
python manage.py shell -c "
from django.contrib.auth.models import Group
Group.objects.filter(name__in=['Medical Doctors', 'Residents', 'Nurses', 'Physiotherapists', 'Students']).delete()
"

# Apply new permission system
python manage.py setup_groups --force

# Verify no admin permissions on medical roles
python manage.py permission_audit --action=verify_medical_roles
```

#### Step 3.2: Create Admin Accounts

```bash
# Create dedicated user management account
python manage.py createsuperuser  # For system admin

# Create user manager account (via admin interface)
# Assign to "User Managers" group
```

#### Step 3.3: Test Medical Staff Permissions

```python
# Test script: apps/core/tests/test_new_permissions.py
class TestNewPermissionSystem(TestCase):
    def test_doctor_has_no_admin_access(self):
        doctor = UserFactory(profession_type=0)  # Medical doctor

        # Should have medical permissions
        self.assertTrue(doctor.has_perm('patients.add_patient'))
        self.assertTrue(doctor.has_perm('events.add_event'))

        # Should NOT have admin permissions
        self.assertFalse(doctor.has_perm('accounts.add_eqmdcustomuser'))
        self.assertFalse(doctor.has_perm('auth.add_group'))
        self.assertFalse(doctor.has_perm('admin.view_logentry'))

    def test_user_manager_has_limited_admin_access(self):
        user_manager = UserFactory()
        user_manager.groups.add(Group.objects.get(name='User Managers'))

        # Should have user management permissions
        self.assertTrue(user_manager.has_perm('accounts.add_eqmdcustomuser'))

        # Should NOT have medical data access
        self.assertFalse(user_manager.has_perm('patients.view_patient'))
        self.assertFalse(user_manager.has_perm('events.view_event'))
```

### Phase 4: Documentation & Validation (Day 4)

#### Step 4.1: Update Documentation

Update `CLAUDE.md` with new permission structure:

```markdown
## Permission System

### Medical Roles (Clinical Staff Only)

- **Doctors/Residents**: Full clinical access, patient management, medical documentation
- **Nurses**: Limited clinical access, basic patient updates, nursing notes
- **Physiotherapists**: Clinical access, therapy documentation
- **Students**: Read-only clinical access

### Administrative Roles (Non-Clinical Staff)

- **Superuser**: Full system access (IT administrators)
- **User Managers**: User account management only (HR/Administrative staff)

### Key Principle

**Medical staff manage patients, administrative staff manage users.**
No overlap between clinical and administrative permissions.
```

#### Step 4.2: Create Permission Reference

Create `apps/core/permissions/PERMISSIONS.md`:

```markdown
# Permission Reference

## What Each Role Can Do

### Medical Doctor

✅ Add/edit/delete patients
✅ Create medical events and notes  
✅ Upload medical images/videos
✅ Fill hospital forms
✅ Manage prescriptions
❌ Create/edit user accounts
❌ Access Django admin
❌ Modify system settings

### User Manager (Administrative)

✅ Create/edit user accounts
✅ Assign users to medical roles
✅ View user profiles
❌ Access patient data
❌ View medical events
❌ Access clinical information
```

#### Step 4.3: Validation Checklist

- [ ] Medical staff cannot access Django admin interface
- [ ] Medical staff cannot create/edit/delete user accounts
- [ ] Medical staff retain all necessary clinical permissions
- [ ] User managers can manage accounts but not access patient data
- [ ] Superuser retains full system access
- [ ] All existing medical functionality works correctly

## Implementation Notes

### Keep It Simple

- **Don't overengineer**: This is a support tool, not a full EMR
- **Focus on core issue**: Remove admin permissions from medical roles
- **Maintain functionality**: Ensure medical staff can do their clinical work
- **Clear boundaries**: Medical vs administrative responsibilities

### Future Considerations

- **Audit logging**: Can be added later if compliance requires
- **Time-based permissions**: Not needed for this support tool context
- **Patient-specific permissions**: Current universal access model is appropriate
- **Emergency access**: Superuser can handle emergency scenarios

### Risk Mitigation

- **Backup current system**: Can rollback if issues arise
- **Test thoroughly**: Verify medical functionality preserved
- **Staged deployment**: Test with small group first
- **Clear documentation**: Ensure team understands new structure

## Success Criteria

1. **Security**: Medical staff cannot manage user accounts or access admin functions
2. **Functionality**: All clinical features work exactly as before
3. **Clarity**: Clear separation between medical and administrative roles
4. **Maintainability**: Simple, understandable permission structure
5. **Compliance Ready**: Foundation for future audit requirements

## Rollback Plan

If issues arise:

```bash
# Restore original permissions
python manage.py loaddata backup_permissions.json

# Revert to original setup_groups.py from git
git checkout HEAD~1 -- apps/core/management/commands/setup_groups.py
python manage.py setup_groups --force
```

## Conclusion

This refactor addresses the critical security vulnerability while maintaining all clinical functionality. The new system follows security best practices with clear role separation, making it suitable for a medical environment without overengineering for the support tool context.

