"""
Management command to set up role-based permission groups.

This command creates groups based on profession types and assigns
appropriate permissions to each group.
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


class Command(BaseCommand):
    help = 'Set up role-based permission groups for EquipeMed'

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
        
        self.stdout.write('Creating profession-based groups...')
        
        with transaction.atomic():
            self._create_medical_doctor_group()
            self._create_resident_group()
            self._create_nurse_group()
            self._create_physiotherapist_group()
            self._create_student_group()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up all permission groups')
        )

    def _remove_existing_groups(self):
        """Remove existing profession-based groups."""
        group_names = [
            'Medical Doctors',
            'Residents',
            'Nurses', 
            'Physiotherapists',
            'Students',
        ]
        
        for group_name in group_names:
            try:
                group = Group.objects.get(name=group_name)
                group.delete()
                self.stdout.write(f'Removed group: {group_name}')
            except Group.DoesNotExist:
                pass

    def _create_medical_doctor_group(self):
        """Create Medical Doctors group with full permissions."""
        group, created = Group.objects.get_or_create(name='Medical Doctors')
        
        if created:
            self.stdout.write('Created group: Medical Doctors')
        
        # Medical doctors get full permissions for all models
        permissions = self._get_all_model_permissions()
        group.permissions.set(permissions)
        
        self.stdout.write(f'Assigned {permissions.count()} permissions to Medical Doctors')

    def _create_resident_group(self):
        """Create Residents group with full access to current hospital patients."""
        group, created = Group.objects.get_or_create(name='Residents')
        
        if created:
            self.stdout.write('Created group: Residents')
        
        # Residents get full permissions for patients, events, and hospital records
        permissions = self._get_patient_related_permissions()
        permissions.extend(self._get_event_permissions())
        permissions.extend(self._get_hospital_permissions())
        
        group.permissions.set(permissions)
        
        self.stdout.write(f'Assigned {len(permissions)} permissions to Residents')

    def _create_nurse_group(self):
        """Create Nurses group with limited patient status changes."""
        group, created = Group.objects.get_or_create(name='Nurses')
        
        if created:
            self.stdout.write('Created group: Nurses')
        
        # Nurses get patient view/change permissions and event permissions
        permissions = []
        permissions.extend(self._get_patient_view_change_permissions())
        permissions.extend(self._get_event_permissions())
        permissions.extend(self._get_hospital_view_permissions())
        
        group.permissions.set(permissions)
        
        self.stdout.write(f'Assigned {len(permissions)} permissions to Nurses')

    def _create_physiotherapist_group(self):
        """Create Physiotherapists group with full access to current hospital patients."""
        group, created = Group.objects.get_or_create(name='Physiotherapists')
        
        if created:
            self.stdout.write('Created group: Physiotherapists')
        
        # Physiotherapists get similar permissions to residents
        permissions = self._get_patient_related_permissions()
        permissions.extend(self._get_event_permissions())
        permissions.extend(self._get_hospital_permissions())
        
        group.permissions.set(permissions)
        
        self.stdout.write(f'Assigned {len(permissions)} permissions to Physiotherapists')

    def _create_student_group(self):
        """Create Students group with limited access to outpatients only."""
        group, created = Group.objects.get_or_create(name='Students')
        
        if created:
            self.stdout.write('Created group: Students')
        
        # Students get only view permissions for patients and limited event access
        permissions = self._get_patient_view_permissions()
        permissions.extend(self._get_event_view_permissions())
        permissions.extend(self._get_hospital_view_permissions())
        
        group.permissions.set(permissions)
        
        self.stdout.write(f'Assigned {len(permissions)} permissions to Students')

    def _get_all_model_permissions(self):
        """Get all permissions for all models."""
        return Permission.objects.all()

    def _get_patient_related_permissions(self):
        """Get all patient-related permissions."""
        permissions = []
        
        # Get patient app content types
        try:
            from apps.patients.models import Patient, PatientHospitalRecord, AllowedTag, Tag
            
            patient_ct = ContentType.objects.get_for_model(Patient)
            record_ct = ContentType.objects.get_for_model(PatientHospitalRecord)
            tag_ct = ContentType.objects.get_for_model(AllowedTag)
            tag_instance_ct = ContentType.objects.get_for_model(Tag)
            
            # Add all permissions for these models
            permissions.extend(Permission.objects.filter(content_type=patient_ct))
            permissions.extend(Permission.objects.filter(content_type=record_ct))
            permissions.extend(Permission.objects.filter(content_type=tag_ct))
            permissions.extend(Permission.objects.filter(content_type=tag_instance_ct))
            
        except ImportError:
            self.stdout.write(self.style.WARNING('Patients app not available'))
        
        return permissions

    def _get_patient_view_change_permissions(self):
        """Get view and change permissions for patients (no delete)."""
        permissions = []
        
        try:
            from apps.patients.models import Patient, PatientHospitalRecord, AllowedTag, Tag
            
            patient_ct = ContentType.objects.get_for_model(Patient)
            record_ct = ContentType.objects.get_for_model(PatientHospitalRecord)
            tag_ct = ContentType.objects.get_for_model(AllowedTag)
            tag_instance_ct = ContentType.objects.get_for_model(Tag)
            
            # Add view and change permissions (no delete)
            for ct in [patient_ct, record_ct, tag_ct, tag_instance_ct]:
                permissions.extend(Permission.objects.filter(
                    content_type=ct,
                    codename__in=[f'view_{ct.model}', f'change_{ct.model}', f'add_{ct.model}']
                ))
            
        except ImportError:
            self.stdout.write(self.style.WARNING('Patients app not available'))
        
        return permissions

    def _get_patient_view_permissions(self):
        """Get only view permissions for patients."""
        permissions = []
        
        try:
            from apps.patients.models import Patient, PatientHospitalRecord, AllowedTag, Tag
            
            patient_ct = ContentType.objects.get_for_model(Patient)
            record_ct = ContentType.objects.get_for_model(PatientHospitalRecord)
            tag_ct = ContentType.objects.get_for_model(AllowedTag)
            tag_instance_ct = ContentType.objects.get_for_model(Tag)
            
            # Add only view permissions
            for ct in [patient_ct, record_ct, tag_ct, tag_instance_ct]:
                permissions.extend(Permission.objects.filter(
                    content_type=ct,
                    codename=f'view_{ct.model}'
                ))
            
        except ImportError:
            self.stdout.write(self.style.WARNING('Patients app not available'))
        
        return permissions

    def _get_event_permissions(self):
        """Get all event-related permissions."""
        permissions = []
        
        try:
            from apps.events.models import Event
            
            event_ct = ContentType.objects.get_for_model(Event)
            permissions.extend(Permission.objects.filter(content_type=event_ct))
            
        except ImportError:
            self.stdout.write(self.style.WARNING('Events app not available'))
        
        return permissions

    def _get_event_view_permissions(self):
        """Get only view permissions for events."""
        permissions = []
        
        try:
            from apps.events.models import Event
            
            event_ct = ContentType.objects.get_for_model(Event)
            permissions.extend(Permission.objects.filter(
                content_type=event_ct,
                codename=f'view_{event_ct.model}'
            ))
            
        except ImportError:
            self.stdout.write(self.style.WARNING('Events app not available'))
        
        return permissions

    def _get_hospital_permissions(self):
        """Get all hospital-related permissions."""
        permissions = []
        
        try:
            from apps.hospitals.models import Hospital, Ward
            
            hospital_ct = ContentType.objects.get_for_model(Hospital)
            ward_ct = ContentType.objects.get_for_model(Ward)
            
            permissions.extend(Permission.objects.filter(content_type=hospital_ct))
            permissions.extend(Permission.objects.filter(content_type=ward_ct))
            
        except ImportError:
            self.stdout.write(self.style.WARNING('Hospitals app not available'))
        
        return permissions

    def _get_hospital_view_permissions(self):
        """Get only view permissions for hospitals."""
        permissions = []
        
        try:
            from apps.hospitals.models import Hospital, Ward
            
            hospital_ct = ContentType.objects.get_for_model(Hospital)
            ward_ct = ContentType.objects.get_for_model(Ward)
            
            for ct in [hospital_ct, ward_ct]:
                permissions.extend(Permission.objects.filter(
                    content_type=ct,
                    codename=f'view_{ct.model}'
                ))
            
        except ImportError:
            self.stdout.write(self.style.WARNING('Hospitals app not available'))
        
        return permissions
