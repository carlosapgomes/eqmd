import json
import sys
from datetime import datetime, timezone, date
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone
from django.db import transaction

try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    firebase_admin = None

from apps.patients.models import Patient, PatientRecordNumber
from apps.dailynotes.models import DailyNote

User = get_user_model()


class Command(BaseCommand):
    help = "Incrementally sync patients and dailynotes from Firebase Realtime Database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--credentials-file",
            type=str,
            required=True,
            help="Path to Firebase service account credentials JSON file",
        )
        parser.add_argument(
            "--database-url",
            type=str,
            required=True,
            help="Firebase Realtime Database URL (e.g., https://your-project.firebaseio.com)",
        )
        parser.add_argument(
            "--project-name",
            type=str,
            required=True,
            help="Firebase project name",
        )
        parser.add_argument(
            "--patients-reference",
            type=str,
            default="patients",
            help="Firebase database reference path for patients (default: patients)",
        )
        parser.add_argument(
            "--dailynotes-reference",
            type=str,
            default="dailynotes",
            help="Firebase database reference path for dailynotes (default: dailynotes)",
        )
        parser.add_argument(
            "--user-email",
            type=str,
            help="Email of user to use as created_by/updated_by. If not provided, uses first superuser",
        )
        parser.add_argument(
            "--since-date",
            type=str,
            required=True,
            help="Sync data from this date (YYYY-MM-DD) based on registrationDt/datetime fields",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be synced without actually importing",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of records to sync (useful for testing)",
        )
        parser.add_argument(
            "--sync-patients",
            action="store_true",
            default=True,
            help="Sync new patients (default: True)",
        )
        parser.add_argument(
            "--sync-dailynotes",
            action="store_true", 
            default=True,
            help="Sync new dailynotes (default: True)",
        )

    def handle(self, *args, **options):
        if firebase_admin is None:
            raise CommandError(
                "firebase-admin package is not installed. Please install it with: uv add firebase-admin"
            )

        self.dry_run = options["dry_run"]
        self.limit = options.get("limit")

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be synced")
            )

        # Parse since date
        try:
            since_date = datetime.strptime(options["since_date"], "%Y-%m-%d")
            self.sync_since_timestamp = int(since_date.timestamp() * 1000)  # Firebase uses milliseconds
        except ValueError:
            raise CommandError("Invalid date format. Use YYYY-MM-DD")

        # Initialize Firebase
        try:
            self.init_firebase(options["credentials_file"], options["database_url"])
        except Exception as e:
            raise CommandError(f"Failed to initialize Firebase: {e}")

        # Get user for imports
        try:
            self.import_user = self.get_import_user(options.get("user_email"))
        except Exception as e:
            raise CommandError(f"Failed to get import user: {e}")

        self.stdout.write(
            f"Using import user: {self.import_user.username} ({self.import_user.email})"
        )
        self.stdout.write(f"Syncing data since: {since_date.date()} ({self.sync_since_timestamp})")

        # Sync patients first (so they exist for dailynotes)
        patients_synced = 0
        if options.get("sync_patients", True):
            try:
                patients_synced = self.sync_patients(options["patients_reference"])
            except Exception as e:
                raise CommandError(f"Failed to sync patients: {e}")

        # Sync dailynotes
        dailynotes_synced = 0
        if options.get("sync_dailynotes", True):
            try:
                dailynotes_synced = self.sync_dailynotes(options["dailynotes_reference"])
            except Exception as e:
                raise CommandError(f"Failed to sync dailynotes: {e}")

        # Final report with next cutoff date
        self.display_sync_report(patients_synced, dailynotes_synced)

    def init_firebase(self, credentials_file, database_url):
        """Initialize Firebase Admin SDK"""
        try:
            import os
            if not os.path.exists(credentials_file):
                raise Exception(f"Credentials file not found: {credentials_file}")

            with open(credentials_file, "r") as f:
                json.load(f)

            cred = credentials.Certificate(credentials_file)
            firebase_admin.initialize_app(cred, {"databaseURL": database_url})
            self.stdout.write(self.style.SUCCESS("Firebase initialized successfully"))
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in credentials file: {e}")
        except Exception as e:
            raise Exception(f"Firebase initialization failed: {e}")

    def get_import_user(self, user_email):
        """Get user for imports"""
        if user_email:
            try:
                user = User.objects.get(email=user_email)
                return user
            except User.DoesNotExist:
                raise Exception(f"User with email {user_email} not found")
        else:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                raise Exception(
                    "No superuser found. Please create one or specify --user-email"
                )
            return user

    def sync_patients(self, patients_reference):
        """Sync new patients from Firebase"""
        self.stdout.write(f"\n=== SYNCING PATIENTS ===")
        
        try:
            # Fetch all patients from Firebase
            ref = db.reference(patients_reference)
            patients_data = ref.get()
            
            if not patients_data:
                self.stdout.write("No patients data found in Firebase")
                return 0

            # Filter patients by registrationDt
            new_patients = {}
            for firebase_key, patient_data in patients_data.items():
                registration_timestamp = patient_data.get('registrationDt')
                
                if registration_timestamp and int(registration_timestamp) >= self.sync_since_timestamp:
                    new_patients[firebase_key] = patient_data

            self.stdout.write(f"Found {len(new_patients)} patients to sync (out of {len(patients_data)} total)")

            if not new_patients:
                return 0

            imported_count = 0
            error_count = 0
            skipped_count = 0

            for firebase_key, patient_data in new_patients.items():
                try:
                    result = self.process_firebase_patient(firebase_key, patient_data)
                    if result == "imported":
                        imported_count += 1
                    elif result == "skipped":
                        skipped_count += 1
                        
                    # Respect limit
                    if self.limit and imported_count >= self.limit:
                        self.stdout.write(f"Reached import limit of {self.limit}")
                        break
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"Error syncing patient {firebase_key}: {e}")
                    )

            self.stdout.write(f"Patients: {imported_count} imported, {skipped_count} skipped, {error_count} errors")
            return imported_count

        except Exception as e:
            raise Exception(f"Failed to sync patients: {e}")

    def process_firebase_patient(self, firebase_key, patient_data):
        """Process a single Firebase patient"""
        # Extract required fields
        name = patient_data.get('name', '').strip()
        pt_rec_n = patient_data.get('ptRecN', '').strip()
        birth_dt_timestamp = patient_data.get('birthDt')
        
        if not name:
            raise ValueError("Patient name is required")
        if not pt_rec_n:
            raise ValueError("Patient ptRecN is required")
        if birth_dt_timestamp is None:
            raise ValueError("Patient birthDt is required")

        # Skip test patients
        if 'teste' in name.lower() or 'paciente' in name.lower():
            return "skipped"

        # Check if patient already exists by either firebase key or ptRecN
        existing_firebase_record = PatientRecordNumber.objects.filter(
            record_number=firebase_key
        ).first()
        
        existing_ptrecn_record = PatientRecordNumber.objects.filter(
            record_number=pt_rec_n
        ).first()

        if existing_firebase_record or existing_ptrecn_record:
            return "skipped"

        # Parse birthday from timestamp
        try:
            birthday = datetime.fromtimestamp(int(birth_dt_timestamp) / 1000).date()
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid birthDt format: {e}")

        # Parse gender
        gender_mapping = {
            '1': Patient.GenderChoices.MALE,
            '2': Patient.GenderChoices.FEMALE,
            '9': Patient.GenderChoices.OTHER,
            '': Patient.GenderChoices.NOT_INFORMED
        }
        gender = gender_mapping.get(str(patient_data.get('gender', '')), Patient.GenderChoices.NOT_INFORMED)

        # Parse status
        status_mapping = {
            'inpatient': Patient.Status.INPATIENT,
            'outpatient': Patient.Status.OUTPATIENT,
            'deceased': Patient.Status.DECEASED
        }
        status = status_mapping.get(patient_data.get('status'), Patient.Status.OUTPATIENT)

        # Parse registration date for created_at
        registration_timestamp = patient_data.get('registrationDt')
        created_at = None
        if registration_timestamp:
            try:
                created_at = datetime.fromtimestamp(int(registration_timestamp) / 1000, tz=timezone.utc)
                created_at = created_at.astimezone(django_timezone.get_current_timezone())
            except (ValueError, TypeError):
                pass  # Use default created_at

        # Parse last admission date
        last_admission_date = None
        last_admission_timestamp = patient_data.get('lastAdmissionDate')
        if last_admission_timestamp:
            try:
                last_admission_date = datetime.fromtimestamp(int(last_admission_timestamp) / 1000).date()
            except (ValueError, TypeError):
                pass

        if self.dry_run:
            self.stdout.write(f"  Would import patient: {name} (ptRecN: {pt_rec_n}, firebase: {firebase_key})")
            return "imported"

        # Create patient
        with transaction.atomic():
            patient = Patient.objects.create(
                name=name,
                birthday=birthday,
                gender=gender,
                status=status,
                healthcard_number=patient_data.get('unifiedHealthCareSystemNumber', ''),
                phone=patient_data.get('phone', ''),
                address=patient_data.get('address', ''),
                city=patient_data.get('city', ''),
                state=patient_data.get('state', ''),
                zip_code=patient_data.get('zip', ''),
                last_admission_date=last_admission_date,
                current_record_number=pt_rec_n,  # Denormalized field
                created_by=self.import_user,
                updated_by=self.import_user,
            )

            # Override created_at if we have registrationDt
            if created_at:
                Patient.objects.filter(pk=patient.pk).update(created_at=created_at)

            # Create Firebase key record number (old registration)
            PatientRecordNumber.objects.create(
                patient=patient,
                record_number=firebase_key,
                is_current=False,
                change_reason="Firebase key (old registration number)",
                created_by=self.import_user,
                updated_by=self.import_user,
            )

            # Create ptRecN record number (current hospital number)
            PatientRecordNumber.objects.create(
                patient=patient,
                record_number=pt_rec_n,
                is_current=True,
                change_reason="Current hospital record number",
                created_by=self.import_user,
                updated_by=self.import_user,
            )

            self.stdout.write(f"  ✓ Imported patient: {name} (ptRecN: {pt_rec_n}, firebase: {firebase_key})")

        return "imported"

    def sync_dailynotes(self, dailynotes_reference):
        """Sync new dailynotes from Firebase"""
        self.stdout.write(f"\n=== SYNCING DAILYNOTES ===")
        
        try:
            # Query Firebase for dailynotes
            ref = db.reference(dailynotes_reference)
            dailynotes_data = ref.get()
            
            if not dailynotes_data:
                self.stdout.write("No dailynotes data found in Firebase")
                return 0

            # Filter dailynotes by datetime
            new_dailynotes = {}
            for note_key, note_data in dailynotes_data.items():
                note_timestamp = note_data.get('datetime')
                
                if note_timestamp and int(note_timestamp) >= self.sync_since_timestamp:
                    new_dailynotes[note_key] = note_data

            self.stdout.write(f"Found {len(new_dailynotes)} dailynotes to sync (out of {len(dailynotes_data)} total)")

            if not new_dailynotes:
                return 0

            imported_count = 0
            error_count = 0
            skipped_count = 0
            patient_not_found_count = 0

            for note_key, note_data in new_dailynotes.items():
                try:
                    result = self.process_firebase_dailynote(note_key, note_data)
                    if result == "imported":
                        imported_count += 1
                    elif result == "skipped":
                        skipped_count += 1
                    elif result == "patient_not_found":
                        patient_not_found_count += 1
                        
                    # Respect limit
                    if self.limit and imported_count >= self.limit:
                        self.stdout.write(f"Reached import limit of {self.limit}")
                        break
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"Error syncing dailynote {note_key}: {e}")
                    )

            self.stdout.write(f"Dailynotes: {imported_count} imported, {patient_not_found_count} patient not found, {skipped_count} skipped, {error_count} errors")
            return imported_count

        except Exception as e:
            raise Exception(f"Failed to sync dailynotes: {e}")

    def process_firebase_dailynote(self, firebase_key, dailynote_data):
        """Process a single Firebase dailynote (reusing logic from import command)"""
        # Validate required fields
        if not dailynote_data.get("patient"):
            raise ValueError("Missing patient field")
        if not dailynote_data.get("datetime"):
            raise ValueError("Missing datetime field")
        if not dailynote_data.get("content"):
            raise ValueError("Missing content field")

        patient_key = dailynote_data["patient"]

        # Find patient using PatientRecordNumber (check both firebase key and ptRecN)
        patient_record = PatientRecordNumber.objects.filter(
            record_number=patient_key
        ).first()

        if not patient_record:
            return "patient_not_found"

        patient = patient_record.patient

        # Check if this dailynote already exists (to avoid duplicates)
        datetime_ms = int(dailynote_data["datetime"])
        event_datetime = datetime.fromtimestamp(datetime_ms / 1000, tz=timezone.utc)
        
        existing_note = DailyNote.objects.filter(
            patient=patient,
            event_datetime=event_datetime,
            content__icontains=f"Firebase ID: {firebase_key}"
        ).first()
        
        if existing_note:
            return "skipped"

        if self.dry_run:
            self.stdout.write(
                f"  Would import dailynote for patient: {patient.name} (record: {patient_key})"
            )
            return "imported"

        # Convert Firebase datetime to Django datetime
        try:
            event_datetime = event_datetime.astimezone(
                django_timezone.get_current_timezone()
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid datetime format: {e}")

        # Format content (reusing format_dailynote_content logic from existing import command)
        formatted_content = self.format_dailynote_content(
            dailynote_data["content"],
            dailynote_data.get("username", "Usuário não identificado"),
            firebase_key
        )

        # Create DailyNote
        DailyNote.objects.create(
            patient=patient,
            event_datetime=event_datetime,
            description="Evolução sincronizada do sistema antigo",
            content=formatted_content,
            created_by=self.import_user,
            updated_by=self.import_user,
        )

        self.stdout.write(
            f"  ✓ Synced dailynote for patient: {patient.name} (record: {patient_key})"
        )
        return "imported"

    def format_dailynote_content(self, content, username, firebase_key):
        """Format the dailynote content according to specifications"""
        header = "Evolução sincronizada do sistema antigo:"
        footer = f"Médico: {username}"
        firebase_id = f"Firebase ID: {firebase_key}"

        # Extract content fields with fallbacks
        subjective = content.get("subjective", "").strip()
        objective = content.get("objective", "").strip()
        exams_list = content.get("examsList", "").strip()
        assess_plan = content.get("assessplan", "").strip()

        # Build formatted content
        sections = [header, ""]

        if subjective:
            sections.append(subjective)

        if objective:
            sections.append("")
            sections.append(objective)

        if exams_list:
            sections.append("")
            sections.append(exams_list)

        if assess_plan:
            sections.append("")
            sections.append(assess_plan)

        sections.extend(["", footer, "", firebase_id])

        return "\n".join(sections)

    def display_sync_report(self, patients_synced, dailynotes_synced):
        """Display final sync report with next cutoff date"""
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("FIREBASE INCREMENTAL SYNC COMPLETED"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - No data was actually synced")
            )

        self.stdout.write("")
        self.stdout.write("Summary:")
        self.stdout.write(f"  Patients synced: {patients_synced}")
        self.stdout.write(f"  Dailynotes synced: {dailynotes_synced}")
        self.stdout.write(f"  Total records synced: {patients_synced + dailynotes_synced}")

        if self.limit:
            self.stdout.write(f"  Limited to: {self.limit} records per type")

        # Calculate next cutoff date (today's date for next sync)
        next_cutoff = datetime.now().strftime("%Y-%m-%d")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Next sync cutoff date:"))
        self.stdout.write(f"  Use --since-date {next_cutoff} for the next sync")
        
        self.stdout.write(self.style.SUCCESS("=" * 60))