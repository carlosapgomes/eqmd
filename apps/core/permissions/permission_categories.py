"""
Permission categorization for EquipeMed authorization refactor.

This module defines clear boundaries between medical and administrative permissions
to support the security refactoring outlined in the permission system refactor plan.
"""

# Medical permissions - what medical staff actually need for clinical work
MEDICAL_PERMISSIONS = [
    # Patient management - core clinical functionality
    'patients.view_patient',
    'patients.add_patient', 
    'patients.change_patient',
    'patients.delete_patient',
    
    # Patient tag instances (not templates) - for patient categorization
    'patients.view_tag',
    'patients.add_tag',
    'patients.change_tag', 
    'patients.delete_tag',
    
    # Medical events - all clinical documentation
    'events.view_event',
    'events.add_event',
    'events.change_event',
    'events.delete_event',
    
    # Daily notes - nursing and medical evolution notes
    'dailynotes.view_dailynote',
    'dailynotes.add_dailynote',
    'dailynotes.change_dailynote',
    'dailynotes.delete_dailynote',
    
    # History and physicals - medical documentation
    'historyandphysicals.view_historyandphysical',
    'historyandphysicals.add_historyandphysical', 
    'historyandphysicals.change_historyandphysical',
    'historyandphysicals.delete_historyandphysical',
    
    # Simple notes - basic documentation
    'simplenotes.view_simplenote',
    'simplenotes.add_simplenote',
    'simplenotes.change_simplenote',
    'simplenotes.delete_simplenote',
    
    # Medical media files - clinical images and videos
    'mediafiles.view_mediafile',
    'mediafiles.add_mediafile',
    'mediafiles.change_mediafile',
    'mediafiles.delete_mediafile',
    
    'mediafiles.view_photo',
    'mediafiles.add_photo',
    'mediafiles.change_photo',
    'mediafiles.delete_photo',
    
    'mediafiles.view_photoseries',
    'mediafiles.add_photoseries',
    'mediafiles.change_photoseries',
    'mediafiles.delete_photoseries',
    
    'mediafiles.view_videoclip',
    'mediafiles.add_videoclip',
    'mediafiles.change_videoclip',
    'mediafiles.delete_videoclip',
    
    # PDF forms - hospital documentation
    'pdf_forms.view_pdfformtemplate',
    'pdf_forms.view_pdfformsubmission',
    'pdf_forms.add_pdfformsubmission',
    'pdf_forms.change_pdfformsubmission',
    'pdf_forms.delete_pdfformsubmission',
    
    # Outpatient prescriptions - doctors and residents only
    'outpatientprescriptions.view_prescription',
    'outpatientprescriptions.add_prescription',
    'outpatientprescriptions.change_prescription',
    'outpatientprescriptions.delete_prescription',
    
    # Sample content - view-only access to templates
    'sample_content.view_samplecontent',
]

# Administrative permissions - should NEVER go to medical staff
ADMIN_ONLY_PERMISSIONS = [
    # User and group management - HR/Admin functions
    'auth.view_user',
    'auth.add_user', 
    'auth.change_user',
    'auth.delete_user',
    
    'auth.view_group',
    'auth.add_group',
    'auth.change_group', 
    'auth.delete_group',
    
    'auth.view_permission',
    'auth.add_permission',
    'auth.change_permission',
    'auth.delete_permission',
    
    # User account management - Custom user model
    'accounts.view_eqmdcustomuser',
    'accounts.add_eqmdcustomuser',
    'accounts.change_eqmdcustomuser',
    'accounts.delete_eqmdcustomuser',
    
    'accounts.view_userprofile',
    'accounts.add_userprofile',
    'accounts.change_userprofile',
    'accounts.delete_userprofile',
    
    # Django admin interface
    'admin.view_logentry',
    'admin.add_logentry',
    'admin.change_logentry',
    'admin.delete_logentry',
    
    # Content types - system-level model management
    'contenttypes.view_contenttype',
    'contenttypes.add_contenttype',
    'contenttypes.change_contenttype',
    'contenttypes.delete_contenttype',
    
    # Sessions - system security
    'sessions.view_session',
    'sessions.add_session',
    'sessions.change_session',
    'sessions.delete_session',
    
    # Sites framework - system configuration
    'sites.view_site',
    'sites.add_site',
    'sites.change_site',
    'sites.delete_site',
    
    # Administrative tag templates - system configuration
    'patients.view_allowedtag',
    'patients.add_allowedtag',
    'patients.change_allowedtag',
    'patients.delete_allowedtag',
    
    # Sample content management - template administration  
    'sample_content.add_samplecontent',
    'sample_content.change_samplecontent',
    'sample_content.delete_samplecontent',
    
    # PDF form template management - system configuration
    'pdf_forms.add_pdfformtemplate',
    'pdf_forms.change_pdfformtemplate', 
    'pdf_forms.delete_pdfformtemplate',
]

# Role-based permission sets for clean group assignment
DOCTOR_PERMISSIONS = [
    # Full patient access
    'patients.view_patient',
    'patients.add_patient',
    'patients.change_patient', 
    'patients.delete_patient',
    
    # Patient tag instances
    'patients.view_tag',
    'patients.add_tag',
    'patients.change_tag',
    'patients.delete_tag',
    
    # Full medical events
    'events.view_event',
    'events.add_event',
    'events.change_event',
    'events.delete_event',
    
    # All medical documentation apps
    'dailynotes.*',
    'historyandphysicals.*',
    'simplenotes.*',
    
    # Medical media management
    'mediafiles.*',
    
    # Hospital forms
    'pdf_forms.view_pdfformtemplate',
    'pdf_forms.view_pdfformsubmission',
    'pdf_forms.add_pdfformsubmission',
    'pdf_forms.change_pdfformsubmission',
    'pdf_forms.delete_pdfformsubmission',
    
    # Prescriptions (doctors/residents only)
    'outpatientprescriptions.*',
    
    # Template viewing
    'sample_content.view_samplecontent',
]

RESIDENT_PERMISSIONS = DOCTOR_PERMISSIONS  # Same as doctors

NURSE_PERMISSIONS = [
    # Patient viewing and limited updates
    'patients.view_patient',
    'patients.change_patient',
    
    # Patient tag viewing and management
    'patients.view_tag',
    'patients.add_tag',
    'patients.change_tag',
    
    # Basic event management
    'events.view_event', 
    'events.add_event',
    'events.change_event',  # Time-limited through business logic
    
    # Nursing documentation
    'dailynotes.*',
    'simplenotes.*',
    
    # Media viewing and basic uploads
    'mediafiles.view_*',
    'mediafiles.add_photo',  # For nursing documentation
    
    # Forms (view and fill)
    'pdf_forms.view_pdfformtemplate',
    'pdf_forms.view_pdfformsubmission',
    'pdf_forms.add_pdfformsubmission',
    
    # Template viewing
    'sample_content.view_samplecontent',
]

PHYSIOTHERAPIST_PERMISSIONS = [
    # Full patient access (needed for therapy management)
    'patients.view_patient',
    'patients.add_patient',
    'patients.change_patient',
    'patients.delete_patient',
    
    # Patient tag management
    'patients.view_tag',
    'patients.add_tag',
    'patients.change_tag',
    'patients.delete_tag',
    
    # Full event management for therapy documentation
    'events.view_event',
    'events.add_event',
    'events.change_event',
    'events.delete_event',
    
    # Medical documentation
    'dailynotes.*',
    'historyandphysicals.*',
    'simplenotes.*',
    
    # Media for therapy documentation
    'mediafiles.*',
    
    # PDF forms
    'pdf_forms.view_pdfformtemplate',
    'pdf_forms.view_pdfformsubmission',
    'pdf_forms.add_pdfformsubmission',
    'pdf_forms.change_pdfformsubmission',
    'pdf_forms.delete_pdfformsubmission',
    
    # Template viewing
    'sample_content.view_samplecontent',
    
    # NO prescriptions (not in physiotherapist scope)
]

STUDENT_PERMISSIONS = [
    # View-only patient access
    'patients.view_patient',
    
    # View-only tags
    'patients.view_tag',
    
    # View-only events
    'events.view_event',
    
    # Can create learning notes (with supervision)
    'dailynotes.view_dailynote',
    'dailynotes.add_dailynote',
    'dailynotes.change_dailynote',  # Own notes only through business logic
    
    'simplenotes.view_simplenote',
    'simplenotes.add_simplenote',
    'simplenotes.change_simplenote',  # Own notes only
    
    # View medical media
    'mediafiles.view_*',
    
    # View and fill forms (learning purposes)
    'pdf_forms.view_pdfformtemplate',
    'pdf_forms.view_pdfformsubmission',
    'pdf_forms.add_pdfformsubmission',
    
    # Template viewing
    'sample_content.view_samplecontent',
]

# User management permissions for administrative roles
USER_MANAGER_PERMISSIONS = [
    # User account management only
    'accounts.view_eqmdcustomuser',
    'accounts.add_eqmdcustomuser',
    'accounts.change_eqmdcustomuser',
    
    # Profile management
    'accounts.view_userprofile', 
    'accounts.change_userprofile',
    
    # Group viewing (for assignment, not modification)
    'auth.view_group',
    
    # NO permission to modify groups or permissions
    # NO access to medical data
    # NO access to patient information
]

def get_permissions_for_role(role_name):
    """Get permission list for a specific role."""
    role_permissions = {
        'Medical Doctors': DOCTOR_PERMISSIONS,
        'Residents': RESIDENT_PERMISSIONS,
        'Nurses': NURSE_PERMISSIONS,
        'Physiotherapists': PHYSIOTHERAPIST_PERMISSIONS,
        'Students': STUDENT_PERMISSIONS,
        'User Managers': USER_MANAGER_PERMISSIONS,
    }
    return role_permissions.get(role_name, [])

def is_medical_role(role_name):
    """Check if a role is a medical role (not administrative)."""
    medical_roles = ['Medical Doctors', 'Residents', 'Nurses', 'Physiotherapists', 'Students']
    return role_name in medical_roles

def is_admin_permission(permission_codename):
    """Check if a permission should be restricted to admin users only."""
    return permission_codename in ADMIN_ONLY_PERMISSIONS

def validate_role_permissions(role_name, permissions):
    """Validate that a role doesn't have inappropriate permissions."""
    if is_medical_role(role_name):
        # Medical roles should not have admin permissions
        admin_perms = [p for p in permissions if is_admin_permission(p)]
        if admin_perms:
            return False, f"Medical role '{role_name}' has admin permissions: {admin_perms}"
    
    return True, "Permissions are appropriate for role"