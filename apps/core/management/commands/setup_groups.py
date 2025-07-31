"""
Management command to set up role-based permission groups.

This command creates groups based on profession types and assigns
appropriate permissions to each group following security best practices.

SECURITY REFACTOR: Implements clean separation between medical and administrative permissions.
Medical staff receive ONLY clinical permissions, admin staff receive user management permissions.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.core.permissions.constants import (
    MEDICAL_DOCTOR,
    RESIDENT, 
    NURSE,
    PHYSIOTHERAPIST,
    STUDENT,
)
from apps.core.permissions.permission_categories import (
    ADMIN_ONLY_PERMISSIONS,
    is_admin_permission,
    validate_role_permissions,
)


class Command(BaseCommand):
    help = 'Set up role-based permission groups for EquipeMed with security best practices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of groups (removes existing groups first)',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        if force:
            self.stdout.write('Removing existing groups...')
            self._remove_existing_groups()
        
        self.stdout.write('Creating profession-based groups with security boundaries...')
        
        with transaction.atomic():
            self._create_medical_doctor_group()
            self._create_resident_group()
            self._create_nurse_group()
            self._create_physiotherapist_group()
            self._create_student_group()
            self._create_user_manager_group()
        
        # Verify security compliance
        self.stdout.write('\nVerifying security compliance...')
        self._verify_security_compliance()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up all permission groups with security boundaries')
        )

    def _remove_existing_groups(self):
        """Remove existing profession-based groups."""
        group_names = [
            'Medical Doctors',
            'Residents',
            'Nurses', 
            'Physiotherapists',
            'Students',
            'User Managers',
        ]
        
        for group_name in group_names:
            try:
                group = Group.objects.get(name=group_name)
                group.delete()
                self.stdout.write(f'Removed group: {group_name}')
            except Group.DoesNotExist:
                pass

    def _create_medical_doctor_group(self):
        """Create Medical Doctors group with ONLY clinical permissions."""
        group, created = Group.objects.get_or_create(name='Medical Doctors')
        
        if created:
            self.stdout.write('Created group: Medical Doctors')
        
        permissions = self._get_doctor_permissions()
        self._set_group_permissions(group, permissions, 'Medical Doctors')

    def _create_resident_group(self):
        """Create Residents group with ONLY clinical permissions (same as doctors)."""
        group, created = Group.objects.get_or_create(name='Residents')
        
        if created:
            self.stdout.write('Created group: Residents')
        
        permissions = self._get_resident_permissions()
        self._set_group_permissions(group, permissions, 'Residents')

    def _create_nurse_group(self):
        """Create Nurses group with limited clinical permissions."""
        group, created = Group.objects.get_or_create(name='Nurses')
        
        if created:
            self.stdout.write('Created group: Nurses')
        
        permissions = self._get_nurse_permissions()
        self._set_group_permissions(group, permissions, 'Nurses')

    def _create_physiotherapist_group(self):
        """Create Physiotherapists group with clinical permissions for therapy work."""
        group, created = Group.objects.get_or_create(name='Physiotherapists')
        
        if created:
            self.stdout.write('Created group: Physiotherapists')
        
        permissions = self._get_physiotherapist_permissions()
        self._set_group_permissions(group, permissions, 'Physiotherapists')

    def _create_student_group(self):
        """Create Students group with read-only clinical permissions."""
        group, created = Group.objects.get_or_create(name='Students')
        
        if created:
            self.stdout.write('Created group: Students')
        
        permissions = self._get_student_permissions()
        self._set_group_permissions(group, permissions, 'Students')

    def _create_user_manager_group(self):
        """Create User Managers group for administrative staff who manage user accounts."""
        group, created = Group.objects.get_or_create(name='User Managers')
        
        if created:
            self.stdout.write('Created group: User Managers')
        
        permissions = self._get_user_manager_permissions()
        self._set_group_permissions(group, permissions, 'User Managers')

    def _set_group_permissions(self, group, permission_codenames, group_name):
        """Set permissions for a group and validate security compliance."""
        # Convert codenames to Permission objects
        permissions = []
        for codename in permission_codenames:
            try:
                if '.' in codename:
                    app_label, perm_code = codename.split('.', 1)
                    perm = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=perm_code
                    )
                    permissions.append(perm)
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping invalid permission format: {codename}')
                    )
            except Permission.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Permission not found: {codename}')
                )
        
        # Security validation
        is_valid, message = validate_role_permissions(group_name, permission_codenames)
        if not is_valid:
            self.stdout.write(self.style.ERROR(f'Security validation failed for {group_name}: {message}'))
            return
        
        group.permissions.set(permissions)
        self.stdout.write(f'Assigned {len(permissions)} permissions to {group_name}')

    def _get_doctor_permissions(self):
        """Full clinical permissions - NO administrative access."""
        permissions = []
        
        # Full patient access
        permissions.extend([
            'patients.view_patient',
            'patients.add_patient',
            'patients.change_patient',
            'patients.delete_patient',
        ])
        
        # Patient tag management (instances, not templates)
        permissions.extend([
            'patients.view_tag',
            'patients.add_tag',
            'patients.change_tag',
            'patients.delete_tag',
        ])
        
        # Medical events with time-limited editing
        permissions.extend([
            'events.view_event',
            'events.add_event',
            'events.change_event',
            'events.delete_event',
        ])
        
        # All medical documentation
        permissions.extend(self._get_app_permissions('dailynotes'))
        permissions.extend(self._get_app_permissions('historyandphysicals'))
        permissions.extend(self._get_app_permissions('simplenotes'))
        permissions.extend(self._get_app_permissions('outpatientprescriptions'))
        
        # Medical media management
        permissions.extend(self._get_app_permissions('mediafiles'))
        
        # Hospital forms
        permissions.extend(self._get_pdf_forms_permissions())
        
        # Template viewing only
        permissions.append('sample_content.view_samplecontent')
        
        return permissions

    def _get_resident_permissions(self):
        """Same clinical permissions as doctors."""
        return self._get_doctor_permissions()

    def _get_nurse_permissions(self):
        """Limited clinical permissions."""
        permissions = []
        
        # Patient viewing and limited updates
        permissions.extend([
            'patients.view_patient',
            'patients.change_patient',  # Limited to non-critical changes
        ])
        
        # Patient tag viewing and management
        permissions.extend([
            'patients.view_tag',
            'patients.add_tag',
            'patients.change_tag',
        ])
        
        # Basic event management
        permissions.extend([
            'events.view_event',
            'events.add_event',
            'events.change_event',  # Time-limited through business logic
        ])
        
        # Nursing documentation
        permissions.extend(self._get_app_permissions('dailynotes'))
        permissions.extend(self._get_app_permissions('simplenotes'))
        
        # Media viewing and basic uploads
        permissions.extend(self._get_view_permissions('mediafiles'))
        permissions.extend([
            'mediafiles.add_photo',  # For nursing documentation
            'mediafiles.add_photoseries',
        ])
        
        # Forms (view and fill)
        permissions.extend([
            'pdf_forms.view_pdfformtemplate',
            'pdf_forms.view_pdfformsubmission',
            'pdf_forms.add_pdfformsubmission',
        ])
        
        # Template viewing
        permissions.append('sample_content.view_samplecontent')
        
        return permissions

    def _get_physiotherapist_permissions(self):
        """Clinical permissions for physiotherapy work."""
        permissions = []
        
        # Full patient access (needed for therapy management)
        permissions.extend([
            'patients.view_patient',
            'patients.add_patient',
            'patients.change_patient',
            'patients.delete_patient',
        ])
        
        # Patient tag management
        permissions.extend([
            'patients.view_tag',
            'patients.add_tag',
            'patients.change_tag',
            'patients.delete_tag',
        ])
        
        # Full event management for therapy documentation
        permissions.extend([
            'events.view_event',
            'events.add_event',
            'events.change_event',
            'events.delete_event',
        ])
        
        # Medical documentation
        permissions.extend(self._get_app_permissions('dailynotes'))
        permissions.extend(self._get_app_permissions('historyandphysicals'))
        permissions.extend(self._get_app_permissions('simplenotes'))
        
        # Media for therapy documentation
        permissions.extend(self._get_app_permissions('mediafiles'))
        
        # PDF forms
        permissions.extend(self._get_pdf_forms_permissions())
        
        # Template viewing
        permissions.append('sample_content.view_samplecontent')
        
        # NO prescriptions (not in physiotherapist scope)
        # NO user management or admin permissions
        
        return permissions

    def _get_student_permissions(self):
        """Read-only permissions for medical students."""
        permissions = []
        
        # View-only patient access
        permissions.append('patients.view_patient')
        
        # View-only tags
        permissions.append('patients.view_tag')
        
        # View-only events
        permissions.append('events.view_event')
        
        # Can create learning notes (with supervision)
        permissions.extend([
            'dailynotes.view_dailynote',
            'dailynotes.add_dailynote',
            'dailynotes.change_dailynote',  # Own notes only through business logic
        ])
        
        permissions.extend([
            'simplenotes.view_simplenote',
            'simplenotes.add_simplenote',
            'simplenotes.change_simplenote',  # Own notes only
        ])
        
        # View medical media
        permissions.extend(self._get_view_permissions('mediafiles'))
        
        # View and fill forms (learning purposes)
        permissions.extend([
            'pdf_forms.view_pdfformtemplate',
            'pdf_forms.view_pdfformsubmission',
            'pdf_forms.add_pdfformsubmission',
        ])
        
        # Template viewing
        permissions.append('sample_content.view_samplecontent')
        
        return permissions

    def _get_user_manager_permissions(self):
        """User management permissions for administrative staff."""
        permissions = []
        
        # User account management only
        permissions.extend([
            'accounts.view_eqmdcustomuser',
            'accounts.add_eqmdcustomuser',
            'accounts.change_eqmdcustomuser',
        ])
        
        # Profile management
        permissions.extend([
            'accounts.view_userprofile',
            'accounts.change_userprofile',
        ])
        
        # Group viewing (for assignment, not modification)
        permissions.append('auth.view_group')
        
        # NO permission to modify groups or permissions
        # NO access to medical data
        # NO access to patient information
        
        return permissions

    # Helper methods for permission retrieval
    def _get_app_permissions(self, app_label):
        """Get all permissions for a specific app."""
        permissions = []
        try:
            app_permissions = Permission.objects.filter(content_type__app_label=app_label)
            for perm in app_permissions:
                permissions.append(f'{app_label}.{perm.codename}')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not load permissions for app {app_label}: {e}'))
        
        return permissions

    def _get_view_permissions(self, app_label):
        """Get only view permissions for a specific app."""
        permissions = []
        try:
            view_permissions = Permission.objects.filter(
                content_type__app_label=app_label,
                codename__startswith='view_'
            )
            for perm in view_permissions:
                permissions.append(f'{app_label}.{perm.codename}')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not load view permissions for app {app_label}: {e}'))
        
        return permissions

    def _get_pdf_forms_permissions(self):
        """Get PDF forms permissions (excluding template management)."""
        permissions = []
        
        # Users can work with submissions but not create/edit templates
        permissions.extend([
            'pdf_forms.view_pdfformtemplate',
            'pdf_forms.view_pdfformsubmission',
            'pdf_forms.add_pdfformsubmission',
            'pdf_forms.change_pdfformsubmission',
            'pdf_forms.delete_pdfformsubmission',
        ])
        
        # NO template creation/editing (admin-only)
        
        return permissions

    def _verify_security_compliance(self):
        """Verify that medical roles have no administrative permissions."""
        medical_groups = ['Medical Doctors', 'Residents', 'Nurses', 'Physiotherapists', 'Students']
        compliance_issues = []
        
        for group_name in medical_groups:
            try:
                group = Group.objects.get(name=group_name)
                admin_perms = []
                
                for perm in group.permissions.all():
                    perm_codename = f'{perm.content_type.app_label}.{perm.codename}'
                    if is_admin_permission(perm_codename):
                        admin_perms.append(perm_codename)
                
                if admin_perms:
                    compliance_issues.append({
                        'group': group_name,
                        'admin_permissions': admin_perms
                    })
                    
            except Group.DoesNotExist:
                pass
        
        if compliance_issues:
            self.stdout.write(self.style.ERROR('🚨 SECURITY COMPLIANCE FAILED'))
            for issue in compliance_issues:
                self.stdout.write(self.style.ERROR(f"- {issue['group']} has admin permissions: {issue['admin_permissions']}"))
        else:
            self.stdout.write(self.style.SUCCESS('✅ Security compliance verified - no medical roles have admin permissions'))