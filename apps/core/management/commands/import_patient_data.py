import json
import sys
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.patients.models import Patient, PatientRecordNumber

User = get_user_model()


class Command(BaseCommand):
    help = 'Import patient data from JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Path to JSON file with patient data',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be imported'))

        # Get JSON data
        if options['file']:
            try:
                with open(options['file'], 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except FileNotFoundError:
                raise CommandError(f'File not found: {options["file"]}')
            except json.JSONDecodeError as e:
                raise CommandError(f'Invalid JSON file: {e}')
        else:
            # Read from stdin
            try:
                data = json.load(sys.stdin)
            except json.JSONDecodeError as e:
                raise CommandError(f'Invalid JSON from stdin: {e}')

        if not isinstance(data, list):
            raise CommandError('JSON data must be a list of patient objects')

        # Get admin user
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                raise CommandError('No admin user found. Please create a superuser first.')
        except Exception as e:
            raise CommandError(f'Error finding admin user: {e}')

        self.stdout.write(f'Found admin user: {admin_user.username} ({admin_user.email})')
        self.stdout.write(f'Processing {len(data)} patient records...')

        imported_count = 0
        skipped_patients = []

        for idx, patient_data in enumerate(data):
            try:
                if self.import_patient(patient_data, admin_user):
                    imported_count += 1
            except Exception as e:
                skipped_patients.append({
                    'index': idx,
                    'data': patient_data,
                    'error': str(e)
                })
                self.stdout.write(
                    self.style.ERROR(f'Skipped patient at index {idx}: {e}')
                )

        # Final report
        self.display_final_report(imported_count, skipped_patients)

    def import_patient(self, patient_data, admin_user):
        """Import a single patient. Returns True if successful, raises exception if failed."""
        
        # Validate required fields
        required_fields = ['name', 'birth_date', 'patient_key', 'medical_record_number']
        for field in required_fields:
            if not patient_data.get(field):
                raise ValueError(f'Missing required field: {field}')

        # Parse birth date
        try:
            birth_date_str = patient_data['birth_date']
            birth_date = datetime.strptime(birth_date_str, '%d/%m/%Y').date()
        except (ValueError, TypeError) as e:
            raise ValueError(f'Invalid birth_date format "{birth_date_str}". Expected DD/MM/YYYY: {e}')

        # Map gender
        gender_mapping = {
            'male': Patient.GenderChoices.MALE,
            'female': Patient.GenderChoices.FEMALE,
            '': Patient.GenderChoices.NOT_INFORMED
        }
        
        input_gender = patient_data.get('gender', '').lower()
        if input_gender not in gender_mapping:
            raise ValueError(f'Invalid gender value: "{patient_data.get("gender")}". Expected: male, female, or empty')
        
        gender = gender_mapping[input_gender]

        # Get patient_key and medical_record_number
        patient_key = patient_data['patient_key']
        medical_record_number = patient_data['medical_record_number']

        if self.dry_run:
            self.stdout.write(f'Would import patient: {patient_data["name"]} (key: {patient_key})')
            return True

        # Check for existing patients with same patient_key or medical_record_number
        if Patient.objects.filter(current_record_number=patient_key).exists():
            raise ValueError(f'Patient with patient_key "{patient_key}" already exists')
        
        if Patient.objects.filter(current_record_number=medical_record_number).exists():
            raise ValueError(f'Patient with medical_record_number "{medical_record_number}" already exists')

        # Create patient with patient_key as initial current_record_number
        patient = Patient.objects.create(
            name=patient_data['name'],
            birthday=birth_date,
            gender=gender,
            healthcard_number=patient_data.get('unified_healthcare_system_number', ''),
            id_number='',  # Empty as requested
            fiscal_number='',  # Empty as requested
            phone=patient_data.get('phone', ''),
            address=patient_data.get('address', ''),
            city=patient_data.get('city', ''),
            state=patient_data.get('state', ''),
            zip_code=patient_data.get('zip', ''),
            status=Patient.Status.OUTPATIENT,
            current_record_number=patient_key,  # Start with patient_key
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Create first PatientRecordNumber for patient_key (old database key)
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number=patient_key,
            is_current=False,  # Will be set to False after creating the medical record number
            change_reason='Importação inicial - chave do sistema antigo',
            effective_date=timezone.now(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Create second PatientRecordNumber for medical_record_number (hospital record)
        medical_record = PatientRecordNumber.objects.create(
            patient=patient,
            record_number=medical_record_number,
            is_current=True,
            change_reason='Importação - número de prontuário hospitalar',
            effective_date=timezone.now(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Update patient to use medical_record_number as current
        patient.current_record_number = medical_record_number
        patient.save(update_fields=['current_record_number', 'updated_at'])

        self.stdout.write(f'  ✓ Imported patient: {patient.name} (record: {medical_record_number})')
        return True

    def display_final_report(self, imported_count, skipped_patients):
        """Display final import report."""
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('PATIENT IMPORT COMPLETED'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No data was actually imported'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {imported_count} patients'))
        
        if skipped_patients:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'Skipped {len(skipped_patients)} patients due to errors:'))
            self.stdout.write('')
            
            for item in skipped_patients:
                self.stdout.write(f'Index {item["index"]}:')
                self.stdout.write(f'  Name: {item["data"].get("name", "Unknown")}')
                self.stdout.write(f'  Patient Key: {item["data"].get("patient_key", "Unknown")}')
                self.stdout.write(f'  Error: {item["error"]}')
                self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS('='*60))