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
    help = "Import dailynotes from Firebase Realtime Database to EQMD"

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
            "--base-reference",
            type=str,
            default="dailynotes",
            help="Firebase database reference path (default: dailynotes)",
        )
        parser.add_argument(
            "--user-email",
            type=str,
            help="Email of user to use as created_by/updated_by. If not provided, uses first superuser",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without actually importing",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of dailynotes to import (useful for testing)",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=100,
            help="Number of records to fetch per Firebase request (default: 100, max: 1000)",
        )
        parser.add_argument(
            "--start-key",
            type=str,
            help="Firebase key to start from (useful for resuming interrupted imports)",
        )

    def handle(self, *args, **options):
        if firebase_admin is None:
            raise CommandError(
                "firebase-admin package is not installed. Please install it with: uv add firebase-admin"
            )

        self.dry_run = options["dry_run"]
        self.limit = options.get("limit")
        self.chunk_size = options.get("chunk_size", 100)
        self.start_key = options.get("start_key")

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be imported")
            )

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

        # Process dailynotes in chunks
        try:
            self.process_firebase_dailynotes_chunked(options["base_reference"])
        except Exception as e:
            raise CommandError(f"Failed to process dailynotes from Firebase: {e}")

    def init_firebase(self, credentials_file, database_url):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if credentials file exists
            import os

            if not os.path.exists(credentials_file):
                raise Exception(f"Credentials file not found: {credentials_file}")

            # Check if it's a valid JSON file
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

    def process_firebase_dailynotes_chunked(self, base_reference):
        """Process dailynotes in chunks to handle large datasets"""
        total_processed = 0
        total_imported = 0
        total_skipped = 0
        total_patient_not_found = 0
        total_errors = 0

        unmatched_patients = set()
        errors = []

        last_key = self.start_key
        chunk_count = 0

        self.stdout.write(f"Processing dailynotes in chunks of {self.chunk_size}...")
        if self.start_key:
            self.stdout.write(f"Starting from key: {self.start_key}")

        while True:
            chunk_count += 1

            try:
                # Fetch chunk of data
                chunk_data, next_key = self.fetch_firebase_chunk(
                    base_reference, last_key, self.chunk_size
                )

                if not chunk_data:
                    self.stdout.write("No more data to process")
                    break

                self.stdout.write(
                    f"Processing chunk {chunk_count}: {len(chunk_data)} records"
                )

                # Process this chunk
                (
                    chunk_imported,
                    chunk_skipped,
                    chunk_patient_not_found,
                    chunk_errors,
                    chunk_unmatched,
                    chunk_error_list,
                ) = self.process_dailynotes_chunk(chunk_data)

                # Update totals
                total_processed += len(chunk_data)
                total_imported += chunk_imported
                total_skipped += chunk_skipped
                total_patient_not_found += chunk_patient_not_found
                total_errors += chunk_errors
                unmatched_patients.update(chunk_unmatched)
                errors.extend(chunk_error_list)

                # Progress update
                self.stdout.write(
                    f"  Chunk {chunk_count} completed: {chunk_imported} imported, {chunk_patient_not_found} patient not found, {chunk_errors} errors"
                )

                # Check if we've reached our limit
                if self.limit and total_processed >= self.limit:
                    self.stdout.write(f"Reached limit of {self.limit} records")
                    break

                # Check if there's more data
                if not next_key:
                    self.stdout.write("Reached end of data")
                    break

                last_key = next_key

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing chunk {chunk_count}: {e}")
                )
                if self.dry_run:
                    break  # In dry run, don't continue after errors
                # In actual import, you might want to continue or stop based on error type
                total_errors += 1
                break

        # Final report
        self.display_final_report(
            total_processed,
            total_imported,
            total_skipped,
            total_patient_not_found,
            total_errors,
            unmatched_patients,
            errors,
            last_key,
        )

    def fetch_firebase_chunk(self, base_reference, start_key=None, limit=100):
        """Fetch a chunk of dailynotes from Firebase with pagination"""
        try:
            ref = db.reference(base_reference)

            # Build query with pagination
            query = ref.order_by_key()

            if start_key:
                query = query.start_at(start_key)

            query = query.limit_to_first(limit + 1)  # +1 to get next key for pagination

            data = query.get()

            if not data:
                return {}, None

            if not isinstance(data, dict):
                raise Exception(f"Unexpected data format: {type(data)}")

            # Convert to list for easier handling
            items = list(data.items())

            # If we got more items than requested, the last one is for getting the next key
            next_key = None
            if len(items) > limit:
                next_key = items[-1][0]  # Last item's key
                items = items[:-1]  # Remove the extra item

            # Convert back to dict
            chunk_data = dict(items)

            return chunk_data, next_key

        except Exception as e:
            raise Exception(f"Failed to fetch Firebase chunk: {e}")

    def process_dailynotes_chunk(self, dailynotes_data):
        """Process a chunk of dailynotes"""
        imported_count = 0
        skipped_count = 0
        patient_not_found_count = 0
        error_count = 0

        unmatched_patients = set()
        errors = []

        for firebase_key, dailynote_data in dailynotes_data.items():
            try:
                result = self.process_single_dailynote(firebase_key, dailynote_data)
                if result == "imported":
                    imported_count += 1
                elif result == "patient_not_found":
                    patient_not_found_count += 1
                    patient_key = dailynote_data.get("patient", "unknown")
                    unmatched_patients.add(patient_key)
                elif result == "skipped":
                    skipped_count += 1
            except Exception as e:
                error_count += 1
                errors.append(
                    {
                        "firebase_key": firebase_key,
                        "patient_key": dailynote_data.get("patient", "unknown"),
                        "error": str(e),
                    }
                )
                if not self.dry_run:  # In dry run, be more verbose about errors
                    self.stdout.write(
                        self.style.ERROR(f"Error processing {firebase_key}: {e}")
                    )

        return (
            imported_count,
            skipped_count,
            patient_not_found_count,
            error_count,
            unmatched_patients,
            errors,
        )

    def process_single_dailynote(self, firebase_key, dailynote_data):
        """Process a single dailynote"""
        # Validate required fields
        if not dailynote_data.get("patient"):
            raise ValueError("Missing patient field")

        if not dailynote_data.get("datetime"):
            raise ValueError("Missing datetime field")

        if not dailynote_data.get("content"):
            raise ValueError("Missing content field")

        patient_key = dailynote_data["patient"]

        # Find patient using PatientRecordNumber
        patient_record = PatientRecordNumber.objects.filter(
            record_number=patient_key
        ).first()

        if not patient_record:
            return "patient_not_found"

        patient = patient_record.patient

        if self.dry_run:
            self.stdout.write(
                f"Would import dailynote for patient: {patient.name} (record: {patient_key})"
            )
            return "imported"

        # Convert Firebase datetime (epoch milliseconds) to Django datetime
        try:
            datetime_ms = int(dailynote_data["datetime"])
            # Create timezone-aware datetime directly from timestamp
            event_datetime = datetime.fromtimestamp(datetime_ms / 1000, tz=timezone.utc)
            # Convert to Django's timezone
            event_datetime = event_datetime.astimezone(
                django_timezone.get_current_timezone()
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid datetime format: {e}")

        # Format content
        formatted_content = self.format_dailynote_content(
            dailynote_data["content"],
            dailynote_data.get("username", "Usuário não identificado"),
        )

        # Create DailyNote
        dailynote = DailyNote.objects.create(
            patient=patient,
            event_datetime=event_datetime,
            description="Evolução importada do sistema antigo",
            content=formatted_content,
            created_by=self.import_user,
            updated_by=self.import_user,
        )

        self.stdout.write(
            f"  ✓ Imported dailynote for patient: {patient.name} (record: {patient_key})"
        )
        return "imported"

    def format_dailynote_content(self, content, username):
        """Format the dailynote content according to specifications"""
        header = "Evolução importada do sistema antigo:"
        footer = f"Médico: {username}"

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

        sections.extend(["", footer])

        return "\n".join(sections)

    def display_final_report(
        self,
        total_count,
        imported_count,
        skipped_count,
        patient_not_found_count,
        error_count,
        unmatched_patients,
        errors,
        last_key=None,
    ):
        """Display final import report"""

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("FIREBASE DAILYNOTES IMPORT COMPLETED"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - No data was actually imported")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully imported {imported_count} dailynotes")
            )

        if self.limit:
            self.stdout.write(
                f"Processed limited set of {total_count} records (limit: {self.limit})"
            )

        # Summary statistics
        self.stdout.write("")
        self.stdout.write("Summary:")
        self.stdout.write(f"  Total processed: {total_count}")
        self.stdout.write(f"  Successfully imported: {imported_count}")
        self.stdout.write(f"  Patient not found: {patient_not_found_count}")
        self.stdout.write(f"  Skipped: {skipped_count}")
        self.stdout.write(f"  Errors: {error_count}")

        # Resume information
        if last_key and not self.dry_run:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Resume Information:"))
            self.stdout.write(f"  To resume from where this import stopped, use:")
            self.stdout.write(f'  --start-key "{last_key}"')

        # Report unmatched patients
        if unmatched_patients:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    f"Unmatched patient keys ({len(unmatched_patients)}):"
                )
            )
            unmatched_list = sorted(unmatched_patients)[:20]  # Show first 20
            for patient_key in unmatched_list:
                self.stdout.write(f"  - {patient_key}")
            if len(unmatched_patients) > 20:
                self.stdout.write(
                    f"  ... and {len(unmatched_patients) - 20} more unmatched patients"
                )

        # Report errors
        if errors:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("Errors encountered:"))
            for error in errors[:5]:  # Show first 5 errors
                self.stdout.write(f'  Firebase key: {error["firebase_key"]}')
                self.stdout.write(f'    Patient key: {error["patient_key"]}')
                self.stdout.write(f'    Error: {error["error"]}')
                self.stdout.write("")

            if len(errors) > 5:
                self.stdout.write(f"  ... and {len(errors) - 5} more errors")

        self.stdout.write(self.style.SUCCESS("=" * 60))

