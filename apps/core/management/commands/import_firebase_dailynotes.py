import json
import sys
from datetime import datetime, timezone
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone

try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    firebase_admin = None

from apps.patients.models import Patient, PatientRecordNumber
from apps.dailynotes.models import DailyNote

User = get_user_model()


class Command(BaseCommand):
    help = 'Import dailynotes from Firebase Realtime Database to EQMD'

    def add_arguments(self, parser):
        parser.add_argument(
            '--credentials-file',
            type=str,
            required=True,
            help='Path to Firebase service account credentials JSON file',
        )
        parser.add_argument(
            '--database-url',
            type=str,
            required=True,
            help='Firebase Realtime Database URL (e.g., https://your-project.firebaseio.com)',
        )
        parser.add_argument(
            '--project-name',
            type=str,
            required=True,
            help='Firebase project name',
        )
        parser.add_argument(
            '--base-reference',
            type=str,
            default='dailynotes',
            help='Firebase database reference path (default: dailynotes)',
        )
        parser.add_argument(
            '--user-email',
            type=str,
            help='Email of user to use as created_by/updated_by. If not provided, uses first superuser',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit the number of dailynotes to import (useful for testing)',
        )

    def handle(self, *args, **options):
        if firebase_admin is None:
            raise CommandError(
                'firebase-admin package is not installed. Please install it with: uv add firebase-admin'
            )

        self.dry_run = options['dry_run']
        self.limit = options.get('limit')
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be imported'))

        # Initialize Firebase
        try:
            self.init_firebase(options['credentials_file'], options['database_url'])
        except Exception as e:
            raise CommandError(f'Failed to initialize Firebase: {e}')

        # Get user for imports
        try:
            self.import_user = self.get_import_user(options.get('user_email'))
        except Exception as e:
            raise CommandError(f'Failed to get import user: {e}')

        self.stdout.write(f'Using import user: {self.import_user.username} ({self.import_user.email})')

        # Fetch dailynotes from Firebase
        try:
            dailynotes_data = self.fetch_firebase_dailynotes(options['base_reference'])
        except Exception as e:
            raise CommandError(f'Failed to fetch dailynotes from Firebase: {e}')

        if not dailynotes_data:
            self.stdout.write(self.style.WARNING('No dailynotes found in Firebase'))
            return

        self.stdout.write(f'Found {len(dailynotes_data)} dailynotes in Firebase')

        # Process dailynotes
        self.process_dailynotes(dailynotes_data)

    def init_firebase(self, credentials_file, database_url):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if credentials file exists
            import os
            if not os.path.exists(credentials_file):
                raise Exception(f'Credentials file not found: {credentials_file}')
            
            # Check if it's a valid JSON file
            with open(credentials_file, 'r') as f:
                json.load(f)
            
            cred = credentials.Certificate(credentials_file)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
            self.stdout.write(self.style.SUCCESS('Firebase initialized successfully'))
        except json.JSONDecodeError as e:
            raise Exception(f'Invalid JSON in credentials file: {e}')
        except Exception as e:
            raise Exception(f'Firebase initialization failed: {e}')

    def get_import_user(self, user_email):
        """Get user for imports"""
        if user_email:
            try:
                user = User.objects.get(email=user_email)
                return user
            except User.DoesNotExist:
                raise Exception(f'User with email {user_email} not found')
        else:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                raise Exception('No superuser found. Please create one or specify --user-email')
            return user

    def fetch_firebase_dailynotes(self, base_reference):
        """Fetch all dailynotes from Firebase"""
        try:
            ref = db.reference(base_reference)
            data = ref.get()
            
            if not data:
                return {}
            
            if isinstance(data, dict):
                return data
            else:
                raise Exception(f'Unexpected data format: {type(data)}')
                
        except Exception as e:
            raise Exception(f'Failed to fetch Firebase data: {e}')

    def process_dailynotes(self, dailynotes_data):
        """Process and import dailynotes"""
        total_count = len(dailynotes_data)
        imported_count = 0
        skipped_count = 0
        patient_not_found_count = 0
        error_count = 0
        
        # Apply limit if specified
        if self.limit:
            items = list(dailynotes_data.items())[:self.limit]
            self.stdout.write(f'Processing limited set: {len(items)} dailynotes')
        else:
            items = dailynotes_data.items()

        # Track unmatched patients for reporting
        unmatched_patients = set()
        errors = []

        for firebase_key, dailynote_data in items:
            try:
                result = self.process_single_dailynote(firebase_key, dailynote_data)
                if result == 'imported':
                    imported_count += 1
                elif result == 'patient_not_found':
                    patient_not_found_count += 1
                    patient_key = dailynote_data.get('patient', 'unknown')
                    unmatched_patients.add(patient_key)
                elif result == 'skipped':
                    skipped_count += 1
            except Exception as e:
                error_count += 1
                errors.append({
                    'firebase_key': firebase_key,
                    'patient_key': dailynote_data.get('patient', 'unknown'),
                    'error': str(e)
                })
                self.stdout.write(
                    self.style.ERROR(f'Error processing {firebase_key}: {e}')
                )

        # Final report
        self.display_final_report(
            total_count, imported_count, skipped_count, 
            patient_not_found_count, error_count, 
            unmatched_patients, errors
        )

    def process_single_dailynote(self, firebase_key, dailynote_data):
        """Process a single dailynote"""
        # Validate required fields
        if not dailynote_data.get('patient'):
            raise ValueError('Missing patient field')
        
        if not dailynote_data.get('datetime'):
            raise ValueError('Missing datetime field')

        if not dailynote_data.get('content'):
            raise ValueError('Missing content field')

        patient_key = dailynote_data['patient']
        
        # Find patient using PatientRecordNumber
        patient_record = PatientRecordNumber.objects.filter(
            record_number=patient_key
        ).first()
        
        if not patient_record:
            return 'patient_not_found'

        patient = patient_record.patient

        if self.dry_run:
            self.stdout.write(f'Would import dailynote for patient: {patient.name} (record: {patient_key})')
            return 'imported'

        # Convert Firebase datetime (epoch milliseconds) to Django datetime
        try:
            datetime_ms = int(dailynote_data['datetime'])
            event_datetime = datetime.fromtimestamp(datetime_ms / 1000, tz=timezone.utc)
            # Convert to Django's timezone-aware datetime
            event_datetime = django_timezone.make_aware(event_datetime, django_timezone.utc)
        except (ValueError, TypeError) as e:
            raise ValueError(f'Invalid datetime format: {e}')

        # Format content
        formatted_content = self.format_dailynote_content(
            dailynote_data['content'], 
            dailynote_data.get('username', 'Usuário não identificado')
        )

        # Create DailyNote
        dailynote = DailyNote.objects.create(
            patient=patient,
            event_datetime=event_datetime,
            description='Evolução importada do Firebase',
            content=formatted_content,
            created_by=self.import_user,
            updated_by=self.import_user,
        )

        self.stdout.write(f'  ✓ Imported dailynote for patient: {patient.name} (record: {patient_key})')
        return 'imported'

    def format_dailynote_content(self, content, username):
        """Format the dailynote content according to specifications"""
        header = "Evolução importada do Firebase"
        footer = f"Médico: {username}"
        
        # Extract content fields with fallbacks
        subjective = content.get('subjective', '').strip()
        objective = content.get('objective', '').strip()
        exams_list = content.get('examsList', '').strip()
        assess_plan = content.get('assessplan', '').strip()
        
        # Build formatted content
        sections = [header, '']
        
        if subjective:
            sections.append(subjective)
        
        if objective:
            sections.append('')
            sections.append(objective)
        
        if exams_list:
            sections.append('')
            sections.append(exams_list)
        
        if assess_plan:
            sections.append('')
            sections.append(assess_plan)
        
        sections.extend(['', footer])
        
        return '\n'.join(sections)

    def display_final_report(self, total_count, imported_count, skipped_count, 
                           patient_not_found_count, error_count, unmatched_patients, errors):
        """Display final import report"""
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('FIREBASE DAILYNOTES IMPORT COMPLETED'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No data was actually imported'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {imported_count} dailynotes'))
        
        if self.limit:
            self.stdout.write(f'Processed limited set of {len(list(total_count))} records')
        
        # Summary statistics
        self.stdout.write('')
        self.stdout.write('Summary:')
        self.stdout.write(f'  Total processed: {imported_count + skipped_count + patient_not_found_count + error_count}')
        self.stdout.write(f'  Successfully imported: {imported_count}')
        self.stdout.write(f'  Patient not found: {patient_not_found_count}')
        self.stdout.write(f'  Skipped: {skipped_count}')
        self.stdout.write(f'  Errors: {error_count}')
        
        # Report unmatched patients
        if unmatched_patients:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(f'Unmatched patient keys ({len(unmatched_patients)}):'))
            for patient_key in sorted(unmatched_patients):
                self.stdout.write(f'  - {patient_key}')
        
        # Report errors
        if errors:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('Errors encountered:'))
            for error in errors[:10]:  # Show first 10 errors
                self.stdout.write(f'  Firebase key: {error["firebase_key"]}')
                self.stdout.write(f'    Patient key: {error["patient_key"]}')
                self.stdout.write(f'    Error: {error["error"]}')
                self.stdout.write('')
            
            if len(errors) > 10:
                self.stdout.write(f'  ... and {len(errors) - 10} more errors')
        
        self.stdout.write(self.style.SUCCESS('='*60))