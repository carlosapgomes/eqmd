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

from apps.patients.models import Patient, PatientRecordNumber, PatientAdmission
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class Command(BaseCommand):
    help = "Import discharge reports from Firebase Realtime Database"

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
            "--discharge-reports-reference",
            type=str,
            default="patientDischargeReports",
            help="Firebase database reference path for discharge reports (default: patientDischargeReports)",
        )
        parser.add_argument(
            "--user-email",
            type=str,
            help="Email of user to use as created_by/updated_by. If not provided, uses first admin user",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without actually importing",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of records to import (useful for testing)",
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

        # Import discharge reports
        try:
            imported_count = self.import_discharge_reports(
                options["discharge_reports_reference"]
            )
        except Exception as e:
            raise CommandError(f"Failed to import discharge reports: {e}")

        # Final report
        self.display_import_report(imported_count)

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
                    "No admin user found. Please create one or specify --user-email"
                )
            return user

    def import_discharge_reports(self, reports_reference):
        """Import discharge reports from Firebase"""
        self.stdout.write(f"\n=== IMPORTING DISCHARGE REPORTS ===")

        try:
            imported_count = 0
            error_count = 0
            skipped_count = 0

            # Get all discharge reports
            ref = db.reference(reports_reference)
            all_reports = ref.get()

            if not all_reports:
                self.stdout.write("No discharge reports found in Firebase")
                return 0

            total_reports = len(all_reports)
            self.stdout.write(f"Found {total_reports} discharge reports in Firebase")

            for firebase_key, report_data in all_reports.items():
                try:
                    result = self.process_firebase_discharge_report(
                        firebase_key, report_data
                    )
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
                        self.style.ERROR(
                            f"Error importing discharge report {firebase_key}: {e}"
                        )
                    )

            self.stdout.write(
                f"Discharge Reports: {imported_count} imported, {skipped_count} skipped, {error_count} errors"
            )
            return imported_count

        except Exception as e:
            raise Exception(f"Failed to import discharge reports: {e}")

    def process_firebase_discharge_report(self, firebase_key, report_data):
        """Process a single Firebase discharge report"""

        # Extract required fields
        content = report_data.get("content", {})
        patient_key = report_data.get("patient")
        datetime_ms = report_data.get("datetime")
        username = report_data.get("username", "Usuário não identificado")

        if not content:
            raise ValueError("Missing content field")
        if not patient_key:
            raise ValueError("Missing patient field")
        if not datetime_ms:
            raise ValueError("Missing datetime field")

        # Find patient using PatientRecordNumber
        patient_record = PatientRecordNumber.objects.filter(
            record_number=patient_key
        ).first()

        if not patient_record:
            return "skipped"  # Patient not found

        patient = patient_record.patient

        # Check if discharge report already exists
        existing_report = DischargeReport.objects.filter(
            patient=patient,
            description__icontains=f"Firebase ID: {firebase_key}",
        ).first()

        if existing_report:
            return "skipped"

        # Parse dates
        admission_date_str = content.get("admissionDate")
        discharge_date_str = content.get("dischargeDate")

        if not admission_date_str or not discharge_date_str:
            raise ValueError("Missing admission or discharge date")

        try:
            admission_date = datetime.strptime(admission_date_str, "%Y-%m-%d").date()
            discharge_date = datetime.strptime(discharge_date_str, "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(f"Invalid date format: {e}")

        # Parse event datetime
        try:
            event_datetime = datetime.fromtimestamp(int(datetime_ms) / 1000, tz=timezone.utc)
            event_datetime = event_datetime.astimezone(
                django_timezone.get_current_timezone()
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid datetime format: {e}")

        if self.dry_run:
            self.stdout.write(
                f"  Would import discharge report for: {patient.name} "
                f"({admission_date_str} -> {discharge_date_str})"
            )
            return "imported"

        # Create discharge report and admission record
        with transaction.atomic():
            # Create discharge report
            discharge_report = DischargeReport.objects.create(
                patient=patient,
                event_datetime=event_datetime,
                description=f"Relatório de alta importado - {content.get('specialty', 'N/A')}",
                admission_date=admission_date,
                discharge_date=discharge_date,
                medical_specialty=content.get("specialty", ""),
                admission_history=content.get("admissionHistory", ""),
                problems_and_diagnosis=content.get("problemsAndDiagnostics", ""),
                exams_list=content.get("examsList", ""),
                procedures_list=content.get("proceduresList", ""),
                inpatient_medical_history=content.get("inpatientMedicalHistory", ""),
                discharge_status=content.get("patientDischargeStatus", ""),
                discharge_recommendations=content.get("dischargeRecommendations", ""),
                is_draft=False,  # Imported reports are finalized
                created_by=self.import_user,
                updated_by=self.import_user,
            )

            # Add Firebase ID to description for tracking
            discharge_report.description += f"\n\nFirebase ID: {firebase_key}\nMédico: {username}"
            discharge_report.save()

            # Create PatientAdmission record
            stay_duration = (discharge_date - admission_date).days

            admission_datetime = django_timezone.datetime.combine(
                admission_date,
                django_timezone.datetime.min.time()
            ).replace(tzinfo=django_timezone.get_current_timezone())

            discharge_datetime = django_timezone.datetime.combine(
                discharge_date,
                django_timezone.datetime.min.time()
            ).replace(tzinfo=django_timezone.get_current_timezone())

            PatientAdmission.objects.create(
                patient=patient,
                admission_datetime=admission_datetime,
                discharge_datetime=discharge_datetime,
                admission_type=PatientAdmission.AdmissionType.SCHEDULED,
                discharge_type=PatientAdmission.DischargeType.MEDICAL,
                initial_bed="",
                final_bed="",
                ward=None,
                admission_diagnosis="",
                discharge_diagnosis="",
                stay_duration_days=stay_duration,
                is_active=False,
                created_by=self.import_user,
                updated_by=self.import_user,
            )

        self.stdout.write(
            f"  ✓ Imported discharge report: {patient.name} "
            f"({admission_date_str} -> {discharge_date_str})"
        )

        return "imported"

    def display_import_report(self, imported_count):
        """Display final import report"""
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("DISCHARGE REPORTS IMPORT COMPLETED"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - No data was actually imported")
            )

        self.stdout.write("")
        self.stdout.write("Summary:")
        self.stdout.write(f"  Discharge reports imported: {imported_count}")

        if self.limit:
            self.stdout.write(f"  Limited to: {self.limit} records")

        self.stdout.write(self.style.SUCCESS("=" * 60))