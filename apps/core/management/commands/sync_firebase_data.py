import json
import sys
from datetime import datetime, timezone, date
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone
from django.db import transaction
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    firebase_admin = None

from apps.patients.models import Patient, PatientRecordNumber, PatientAdmission, Ward
from apps.dailynotes.models import DailyNote

User = get_user_model()


class Command(BaseCommand):
    help = "Incrementally sync patients and dailynotes from Firebase Realtime Database"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ward_map_file = "fixtures/firebase-ward-map.json"
        self.ward_source_file = "fixtures/sisphgrs-wards-export.json"
        self.ward_mapping_loaded = False
        self.firebase_ward_to_eqmd_ward_id = {}
        self.firebase_ward_name_to_key = {}
        self.ward_mapped_count = 0
        self.ward_mapped_to_none_count = 0
        self.ward_unresolved_count = 0
        self.ward_updated_count = 0

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
            "--no-sync-patients",
            action="store_true",
            help="Skip syncing patients (default: sync patients)",
        )
        parser.add_argument(
            "--no-sync-dailynotes",
            action="store_true",
            help="Skip syncing dailynotes (default: sync dailynotes)",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=1000,
            help="Number of records to fetch from Firebase in each chunk (default: 1000)",
        )
        parser.add_argument(
            "--email",
            type=str,
            help="Send sync report via email to this address",
        )
        parser.add_argument(
            "--ward-map-file",
            type=str,
            default="fixtures/firebase-ward-map.json",
            help=(
                "Path to Firebase ward mapping JSON "
                "(Firebase ward key -> EQMD Ward UUID or null)"
            ),
        )

    def handle(self, *args, **options):
        if firebase_admin is None:
            raise CommandError(
                "firebase-admin package is not installed. Please install it with: uv add firebase-admin"
            )

        # Validate email if provided
        if options.get("email"):
            try:
                validate_email(options["email"])
            except ValidationError:
                raise CommandError(f"Invalid email address: {options['email']}")

        self.dry_run = options["dry_run"]
        self.limit = options.get("limit")
        self.chunk_size = options.get("chunk_size", 1000)
        self.email = options.get("email")
        self.ward_map_file = options.get("ward_map_file") or self.ward_map_file

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be synced")
            )

        # Parse since date
        try:
            since_date = datetime.strptime(options["since_date"], "%Y-%m-%d")
            self.sync_since_timestamp = int(
                since_date.timestamp() * 1000
            )  # Firebase uses milliseconds
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
        self.stdout.write(
            f"Syncing data since: {since_date.date()} ({self.sync_since_timestamp})"
        )
        self.stdout.write(
            f"Using chunk size: {self.chunk_size} records per Firebase query"
        )

        # Sync patients first (so they exist for dailynotes)
        patients_synced = 0
        if not options.get("no_sync_patients", False):
            self.load_ward_mapping()
            try:
                patients_synced = self.sync_patients(options["patients_reference"])
            except Exception as e:
                raise CommandError(f"Failed to sync patients: {e}")
        else:
            self.stdout.write("Skipping patient sync (--no-sync-patients specified)")

        # Sync dailynotes
        dailynotes_synced = 0
        if not options.get("no_sync_dailynotes", False):
            try:
                dailynotes_synced = self.sync_dailynotes(
                    options["dailynotes_reference"]
                )
            except Exception as e:
                raise CommandError(f"Failed to sync dailynotes: {e}")
        else:
            self.stdout.write(
                "Skipping dailynote sync (--no-sync-dailynotes specified)"
            )

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
        """Sync new patients from Firebase using chunked queries"""
        self.stdout.write(f"\n=== SYNCING PATIENTS ===")
        self.stdout.write(f"Using chunk size: {self.chunk_size}")

        try:
            self._ensure_ward_mapping_loaded()
            imported_count = 0
            error_count = 0
            skipped_count = 0
            reconciled_count = 0
            total_processed = 0
            self.reconciled_patients_count = 0
            self.admissions_closed_count = 0
            self.admissions_created_count = 0
            self.ward_mapped_count = 0
            self.ward_mapped_to_none_count = 0
            self.ward_unresolved_count = 0
            self.ward_updated_count = 0

            # Use chunked querying to avoid payload limits
            ref = db.reference(patients_reference)

            # Get total count first (for progress reporting)
            try:
                # Quick count query - just get keys
                all_keys = ref.shallow().get()
                total_patients = len(all_keys) if all_keys else 0
                self.stdout.write(f"Total patients in Firebase: {total_patients}")
            except Exception as e:
                self.stdout.write(f"Could not get total count: {e}")
                total_patients = "unknown"

            last_key = None
            chunk_num = 0

            while True:
                chunk_num += 1
                self.stdout.write(f"\n--- Processing chunk {chunk_num} ---")

                # Query this chunk
                query = ref.order_by_key().limit_to_first(self.chunk_size)
                if last_key:
                    query = query.start_at(last_key)

                chunk_data = query.get()

                if not chunk_data:
                    self.stdout.write("No more data to process")
                    break

                # Filter patients by registrationDt and process
                chunk_new_patients = {}
                for firebase_key, patient_data in chunk_data.items():
                    if firebase_key == last_key:
                        continue  # Skip the overlap key

                    registration_timestamp = patient_data.get("registrationDt")
                    if (
                        registration_timestamp
                        and int(registration_timestamp) >= self.sync_since_timestamp
                    ):
                        chunk_new_patients[firebase_key] = patient_data

                self.stdout.write(
                    f"Found {len(chunk_new_patients)} new patients in this chunk (out of {len(chunk_data)})"
                )

                # Process patients in this chunk
                for firebase_key, patient_data in chunk_new_patients.items():
                    try:
                        result = self.process_firebase_patient(
                            firebase_key, patient_data
                        )
                        if result == "imported":
                            imported_count += 1
                        elif result == "reconciled":
                            reconciled_count += 1
                        elif result == "skipped":
                            skipped_count += 1

                        total_processed += 1

                        # Respect limit
                        if self.limit and imported_count >= self.limit:
                            self.stdout.write(f"Reached import limit of {self.limit}")
                            break

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"Error syncing patient {firebase_key}: {e}"
                            )
                        )

                # Check if we should continue
                if self.limit and imported_count >= self.limit:
                    break

                if len(chunk_data) < self.chunk_size:
                    self.stdout.write("Reached end of data")
                    break

                # Set up for next chunk
                last_key = max(chunk_data.keys())  # Get the last key for pagination

                # Progress report
                if isinstance(total_patients, int):
                    progress = (total_processed / total_patients) * 100
                    self.stdout.write(
                        f"Progress: {total_processed}/{total_patients} ({progress:.1f}%)"
                    )

            self.stdout.write(
                f"Patients: {imported_count} imported, {reconciled_count} reconciled, "
                f"{skipped_count} skipped, {error_count} errors"
            )
            if reconciled_count:
                self.stdout.write(
                    f"Admissions closed: {self.admissions_closed_count}, "
                    f"Admissions created: {self.admissions_created_count}"
                )
            self.stdout.write(
                f"Ward mapping: {self.ward_mapped_count} mapped, "
                f"{self.ward_mapped_to_none_count} mapped-to-none, "
                f"{self.ward_unresolved_count} unresolved, "
                f"{self.ward_updated_count} updated on active admissions"
            )
            return imported_count

        except Exception as e:
            raise Exception(f"Failed to sync patients: {e}")

    def _resolve_file_path(self, raw_path):
        path = Path(raw_path).expanduser()
        if path.is_absolute():
            return path

        cwd = Path.cwd()
        base_dir = Path(getattr(settings, "BASE_DIR", cwd))
        candidates = [cwd / path]
        if base_dir != cwd:
            candidates.append(base_dir / path)

        for candidate in candidates:
            if candidate.exists():
                return candidate

        # Prefer BASE_DIR fallback for clearer deployment error messages.
        return candidates[-1]

    def load_ward_mapping(self):
        """Load and validate Firebase ward to EQMD ward mapping."""
        map_path = self._resolve_file_path(self.ward_map_file)
        if not map_path.exists():
            raise CommandError(
                "Ward map file not found: "
                f"{map_path} (raw='{self.ward_map_file}', cwd='{Path.cwd()}', "
                f"base_dir='{getattr(settings, 'BASE_DIR', Path.cwd())}')"
            )

        try:
            with map_path.open("r", encoding="utf-8") as handle:
                raw_map = json.load(handle)
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid ward map JSON ({map_path}): {exc}")

        if not isinstance(raw_map, dict):
            raise CommandError("Ward map JSON must be an object/dictionary")

        normalized_map = {}
        for firebase_ward_key, eqmd_ward_id in raw_map.items():
            if not isinstance(firebase_ward_key, str) or not firebase_ward_key.strip():
                raise CommandError("Ward map keys must be non-empty strings")
            if eqmd_ward_id is not None and not isinstance(eqmd_ward_id, str):
                raise CommandError(
                    f"Ward map value for '{firebase_ward_key}' must be string UUID or null"
                )
            normalized_map[firebase_ward_key] = eqmd_ward_id

        # Optional validation against canonical Firebase ward export fixture.
        source_path = self._resolve_file_path(self.ward_source_file)
        name_to_key = {}
        if source_path.exists():
            try:
                with source_path.open("r", encoding="utf-8") as handle:
                    source_data = json.load(handle)
            except json.JSONDecodeError as exc:
                raise CommandError(f"Invalid Firebase ward source JSON ({source_path}): {exc}")

            if not isinstance(source_data, dict):
                raise CommandError("Firebase ward source JSON must be an object/dictionary")

            missing_keys = sorted(set(source_data.keys()) - set(normalized_map.keys()))
            if missing_keys:
                missing_preview = ", ".join(missing_keys[:5])
                suffix = "" if len(missing_keys) <= 5 else ", ..."
                raise CommandError(
                    f"Ward map is missing {len(missing_keys)} Firebase ward keys: "
                    f"{missing_preview}{suffix}"
                )

            for firebase_ward_key, ward_data in source_data.items():
                if not isinstance(ward_data, dict):
                    continue
                ward_name = (ward_data.get("name") or "").strip()
                if ward_name:
                    name_to_key[ward_name] = firebase_ward_key

        self.firebase_ward_to_eqmd_ward_id = normalized_map
        self.firebase_ward_name_to_key = name_to_key
        self.ward_mapping_loaded = True
        self.stdout.write(
            f"Loaded ward map: {len(normalized_map)} entries from {map_path}"
        )

    def _ensure_ward_mapping_loaded(self):
        if not self.ward_mapping_loaded:
            self.load_ward_mapping()

    def _extract_firebase_ward_reference(self, patient_data):
        """Extract a ward reference from known Firebase payload shapes."""
        for field_name in ("ward", "ptWard", "wardKey", "wardId"):
            raw_value = patient_data.get(field_name)
            if raw_value in (None, ""):
                continue
            if isinstance(raw_value, str):
                value = raw_value.strip()
                if value:
                    return value
                continue
            if isinstance(raw_value, dict):
                for nested_key in (
                    "key",
                    "id",
                    "ward",
                    "wardKey",
                    "wardId",
                    "firebaseKey",
                    "name",
                ):
                    nested_value = raw_value.get(nested_key)
                    if isinstance(nested_value, str) and nested_value.strip():
                        return nested_value.strip()
            value = str(raw_value).strip()
            if value:
                return value
        return None

    def _resolve_ward_from_patient_data(self, patient_data, firebase_key, patient_name):
        """
        Resolve Firebase ward reference into Ward instance.

        Returns (ward_instance_or_none, status) where status is one of:
        no_reference | mapped | mapped_to_none | unresolved
        """
        self._ensure_ward_mapping_loaded()
        raw_reference = self._extract_firebase_ward_reference(patient_data)
        if not raw_reference:
            return None, "no_reference"

        mapping_key = raw_reference
        if (
            mapping_key not in self.firebase_ward_to_eqmd_ward_id
            and raw_reference in self.firebase_ward_name_to_key
        ):
            mapping_key = self.firebase_ward_name_to_key[raw_reference]

        if mapping_key not in self.firebase_ward_to_eqmd_ward_id:
            self.ward_unresolved_count += 1
            self.stdout.write(
                self.style.WARNING(
                    f"  ! Unresolved ward for patient {patient_name} ({firebase_key}): '{raw_reference}'"
                )
            )
            return None, "unresolved"

        mapped_ward_id = self.firebase_ward_to_eqmd_ward_id[mapping_key]
        if mapped_ward_id is None:
            self.ward_mapped_to_none_count += 1
            return None, "mapped_to_none"

        ward = Ward.objects.filter(pk=mapped_ward_id).first()
        if ward is None:
            self.ward_unresolved_count += 1
            self.stdout.write(
                self.style.WARNING(
                    f"  ! Ward id '{mapped_ward_id}' not found in DB for patient "
                    f"{patient_name} ({firebase_key}); source '{raw_reference}'"
                )
            )
            return None, "unresolved"

        self.ward_mapped_count += 1
        return ward, "mapped"

    def _parse_firebase_status(self, patient_data):
        raw_status = (patient_data.get("status") or "").strip().lower()
        status_mapping = {
            "inpatient": Patient.Status.INPATIENT,
            "outpatient": Patient.Status.OUTPATIENT,
            "deceased": Patient.Status.DECEASED,
            "emergency": Patient.Status.EMERGENCY,
        }
        return raw_status, status_mapping.get(raw_status)

    def _parse_last_admission_date(self, patient_data):
        last_admission_timestamp = patient_data.get("lastAdmissionDate")
        if last_admission_timestamp:
            try:
                return datetime.fromtimestamp(
                    int(last_admission_timestamp) / 1000
                ).date()
            except (ValueError, TypeError):
                return None
        return None

    def _reconcile_existing_patient(
        self,
        patient,
        patient_data,
        last_admission_date,
        resolved_ward,
        ward_resolution_status,
    ):
        raw_status, desired_status = self._parse_firebase_status(patient_data)
        if not raw_status or desired_status is None:
            return "skipped"

        current_admission = patient.get_current_admission()
        changes_made = False
        has_explicit_ward_resolution = ward_resolution_status in {
            "mapped",
            "mapped_to_none",
        }

        if desired_status in [Patient.Status.OUTPATIENT, Patient.Status.DECEASED]:
            if current_admission:
                discharge_type = (
                    PatientAdmission.DischargeType.DEATH
                    if desired_status == Patient.Status.DECEASED
                    else PatientAdmission.DischargeType.MEDICAL
                )
                close_datetime = django_timezone.now()
                if self.dry_run:
                    self.stdout.write(
                        f"  Would close active admission for: {patient.name}"
                    )
                else:
                    patient.discharge_patient(
                        close_datetime,
                        discharge_type,
                        self.import_user,
                    )
                    if desired_status == Patient.Status.DECEASED and patient.status != Patient.Status.DECEASED:
                        patient.status = Patient.Status.DECEASED
                        patient.updated_by = self.import_user
                        patient.save(
                            update_fields=["status", "updated_by", "updated_at"]
                        )
                self.admissions_closed_count += 1
                changes_made = True

            if patient.status != desired_status:
                if self.dry_run:
                    self.stdout.write(
                        f"  Would update status for: {patient.name} -> {raw_status}"
                    )
                else:
                    patient.status = desired_status
                    patient.current_admission_id = None
                    patient.bed = ""
                    patient.ward = None
                    patient.updated_by = self.import_user
                    patient.save(
                        update_fields=[
                            "status",
                            "current_admission_id",
                            "bed",
                            "ward",
                            "updated_by",
                            "updated_at",
                        ]
                    )
                changes_made = True

        elif desired_status in [Patient.Status.INPATIENT, Patient.Status.EMERGENCY]:
            if not current_admission:
                admission_datetime = django_timezone.now()
                if last_admission_date:
                    admission_datetime = django_timezone.datetime.combine(
                        last_admission_date,
                        django_timezone.datetime.min.time(),
                    ).replace(tzinfo=django_timezone.get_current_timezone())

                admission_type = (
                    PatientAdmission.AdmissionType.EMERGENCY
                    if desired_status == Patient.Status.EMERGENCY
                    else PatientAdmission.AdmissionType.SCHEDULED
                )

                if self.dry_run:
                    self.stdout.write(
                        f"  Would create active admission for: {patient.name}"
                    )
                else:
                    patient.admit_patient(
                        admission_datetime,
                        admission_type,
                        self.import_user,
                        initial_bed="",
                        ward=resolved_ward,
                        admission_diagnosis="Admissão importada do sistema antigo",
                    )
                    if desired_status == Patient.Status.EMERGENCY and patient.status != Patient.Status.EMERGENCY:
                        patient.status = Patient.Status.EMERGENCY
                        patient.updated_by = self.import_user
                        patient.save(
                            update_fields=["status", "updated_by", "updated_at"]
                        )

                self.admissions_created_count += 1
                changes_made = True

            else:
                if (
                    has_explicit_ward_resolution
                    and current_admission.ward_id
                    != (resolved_ward.id if resolved_ward else None)
                ):
                    if self.dry_run:
                        self.stdout.write(
                            f"  Would update ward for active admission: {patient.name}"
                        )
                    else:
                        current_admission.ward = resolved_ward
                        current_admission.updated_by = self.import_user
                        current_admission.save(
                            update_fields=["ward", "updated_by", "updated_at"]
                        )
                        patient.ward = resolved_ward
                        patient.updated_by = self.import_user
                        patient.save(
                            update_fields=["ward", "updated_by", "updated_at"]
                        )
                    self.ward_updated_count += 1
                    changes_made = True

                if patient.status != desired_status:
                    if self.dry_run:
                        self.stdout.write(
                            f"  Would update status for: {patient.name} -> {raw_status}"
                        )
                    else:
                        patient.status = desired_status
                        patient.updated_by = self.import_user
                        patient.save(
                            update_fields=["status", "updated_by", "updated_at"]
                        )
                    changes_made = True

        if changes_made:
            self.reconciled_patients_count += 1
            return "reconciled"

        return "skipped"

    def process_firebase_patient(self, firebase_key, patient_data):
        """Process a single Firebase patient"""
        self._ensure_ward_mapping_loaded()
        # Extract required fields
        name = patient_data.get("name", "").strip()
        pt_rec_n = patient_data.get("ptRecN", "").strip()
        birth_dt_timestamp = patient_data.get("birthDt")

        if not name:
            raise ValueError("Patient name is required")
        if not pt_rec_n:
            raise ValueError("Patient ptRecN is required")
        if birth_dt_timestamp is None:
            raise ValueError("Patient birthDt is required")

        # Skip test patients
        if "teste" in name.lower() or "paciente" in name.lower():
            return "skipped"

        last_admission_date = self._parse_last_admission_date(patient_data)
        resolved_ward, ward_resolution_status = self._resolve_ward_from_patient_data(
            patient_data,
            firebase_key,
            name,
        )

        # Check if patient already exists by either firebase key or ptRecN
        existing_firebase_record = PatientRecordNumber.objects.filter(
            record_number=firebase_key
        ).first()

        existing_ptrecn_record = PatientRecordNumber.objects.filter(
            record_number=pt_rec_n
        ).first()

        if existing_firebase_record and existing_ptrecn_record:
            if existing_firebase_record.patient_id != existing_ptrecn_record.patient_id:
                self.stdout.write(
                    self.style.WARNING(
                        "Patient record mismatch between firebase key and ptRecN; skipping reconcile."
                    )
                )
                return "skipped"

        if existing_firebase_record or existing_ptrecn_record:
            existing_patient = (
                existing_firebase_record.patient
                if existing_firebase_record
                else existing_ptrecn_record.patient
            )
            return self._reconcile_existing_patient(
                existing_patient,
                patient_data,
                last_admission_date,
                resolved_ward,
                ward_resolution_status,
            )

        # Parse birthday from timestamp
        try:
            birthday = datetime.fromtimestamp(int(birth_dt_timestamp) / 1000).date()
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid birthDt format: {e}")

        # Parse gender
        gender_mapping = {
            "1": Patient.GenderChoices.MALE,
            "2": Patient.GenderChoices.FEMALE,
            "9": Patient.GenderChoices.OTHER,
            "": Patient.GenderChoices.NOT_INFORMED,
        }
        gender = gender_mapping.get(
            str(patient_data.get("gender", "")), Patient.GenderChoices.NOT_INFORMED
        )

        # Parse status with two-step logic for proper timeline event creation
        raw_status, mapped_status = self._parse_firebase_status(patient_data)
        original_status = mapped_status or Patient.Status.OUTPATIENT
        
        # Determine creation approach based on original status
        if original_status in [Patient.Status.INPATIENT, Patient.Status.EMERGENCY]:
            # Two-step process: create as outpatient, then admit via PatientAdmission
            status = Patient.Status.OUTPATIENT
            will_create_admission = True
        elif original_status == Patient.Status.DECEASED:
            # Deceased patients: create with final status, no admission needed
            status = Patient.Status.DECEASED
            will_create_admission = False
        else:
            # Outpatient, discharged, transferred: create with original status
            status = original_status
            will_create_admission = False

        # Parse registration date for created_at
        registration_timestamp = patient_data.get("registrationDt")
        created_at = None
        if registration_timestamp:
            try:
                created_at = datetime.fromtimestamp(
                    int(registration_timestamp) / 1000, tz=timezone.utc
                )
                created_at = created_at.astimezone(
                    django_timezone.get_current_timezone()
                )
            except (ValueError, TypeError):
                pass  # Use default created_at

        if self.dry_run:
            self.stdout.write(
                f"  Would import patient: {name} (ptRecN: {pt_rec_n}, firebase: {firebase_key})"
            )
            return "imported"

        # Create patient
        with transaction.atomic():
            patient = Patient.objects.create(
                name=name,
                birthday=birthday,
                gender=gender,
                status=status,
                healthcard_number=patient_data.get("unifiedHealthCareSystemNumber", ""),
                phone=patient_data.get("phone", ""),
                address=patient_data.get("address", ""),
                city=patient_data.get("city", ""),
                state=patient_data.get("state", ""),
                zip_code=patient_data.get("zip", ""),
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

            # Create PatientAdmission for patients who should have active admissions
            if will_create_admission and last_admission_date:
                # Convert last_admission_date to datetime for admission_datetime
                admission_datetime = django_timezone.datetime.combine(
                    last_admission_date,
                    django_timezone.datetime.min.time()
                ).replace(tzinfo=django_timezone.get_current_timezone())
                
                admission = PatientAdmission.objects.create(
                    patient=patient,
                    admission_datetime=admission_datetime,
                    admission_type=PatientAdmission.AdmissionType.EMERGENCY,
                    initial_bed="",  # Empty bed
                    ward=resolved_ward,
                    admission_diagnosis="Admissão importada do sistema antigo",
                    created_by=self.import_user,
                    updated_by=self.import_user,
                )
                if patient.ward_id != admission.ward_id:
                    patient.ward = admission.ward
                    patient.updated_by = self.import_user
                    patient.save(update_fields=["ward", "updated_by", "updated_at"])

            self.stdout.write(
                f"  ✓ Imported patient: {name} (ptRecN: {pt_rec_n}, firebase: {firebase_key})"
            )

        return "imported"

    def get_current_dailynote_keys(self):
        """Get all current dailynote keys from patients to exclude drafts"""
        try:
            # Get all patients to check for currentdailynotekey
            patients_ref = db.reference("patients")
            all_patients = patients_ref.get()
            
            current_keys = set()
            if all_patients:
                for patient_key, patient_data in all_patients.items():
                    current_dailynote_key = patient_data.get("currentdailynotekey")
                    if current_dailynote_key:
                        current_keys.add(current_dailynote_key)
            
            return current_keys
        except Exception as e:
            self.stdout.write(f"Warning: Could not fetch current dailynote keys: {e}")
            return set()

    def sync_dailynotes(self, dailynotes_reference):
        """Sync new dailynotes from Firebase using chunked queries"""
        self.stdout.write(f"\n=== SYNCING DAILYNOTES ===")
        self.stdout.write(f"Using chunk size: {self.chunk_size}")

        try:
            imported_count = 0
            error_count = 0
            skipped_count = 0
            patient_not_found_count = 0
            draft_skipped_count = 0
            total_processed = 0

            # Get all current dailynote keys from patients to exclude drafts
            current_dailynote_keys = self.get_current_dailynote_keys()
            self.stdout.write(f"Found {len(current_dailynote_keys)} current dailynote keys (drafts) to exclude")

            # Use chunked querying to avoid payload limits
            ref = db.reference(dailynotes_reference)

            # Get total count first (for progress reporting)
            try:
                # Quick count query - just get keys
                all_keys = ref.shallow().get()
                total_dailynotes = len(all_keys) if all_keys else 0
                self.stdout.write(f"Total dailynotes in Firebase: {total_dailynotes}")
            except Exception as e:
                self.stdout.write(f"Could not get total count: {e}")
                total_dailynotes = "unknown"

            last_key = None
            chunk_num = 0

            while True:
                chunk_num += 1
                self.stdout.write(f"\n--- Processing dailynotes chunk {chunk_num} ---")

                # Query this chunk
                query = ref.order_by_key().limit_to_first(self.chunk_size)
                if last_key:
                    query = query.start_at(last_key)

                chunk_data = query.get()

                if not chunk_data:
                    self.stdout.write("No more dailynotes data to process")
                    break

                # Filter dailynotes by datetime and process
                chunk_new_dailynotes = {}
                for note_key, note_data in chunk_data.items():
                    if note_key == last_key:
                        continue  # Skip the overlap key

                    note_timestamp = note_data.get("datetime")
                    if (
                        note_timestamp
                        and int(note_timestamp) >= self.sync_since_timestamp
                    ):
                        chunk_new_dailynotes[note_key] = note_data

                self.stdout.write(
                    f"Found {len(chunk_new_dailynotes)} new dailynotes in this chunk (out of {len(chunk_data)})"
                )

                # Process dailynotes in this chunk
                for note_key, note_data in chunk_new_dailynotes.items():
                    try:
                        # Skip if this is a current dailynote (draft)
                        if note_key in current_dailynote_keys:
                            if self.dry_run:
                                self.stdout.write(f"  Would skip draft dailynote: {note_key}")
                            draft_skipped_count += 1
                            total_processed += 1
                            continue
                        
                        result = self.process_firebase_dailynote(note_key, note_data)
                        if result == "imported":
                            imported_count += 1
                        elif result == "skipped":
                            skipped_count += 1
                        elif result == "patient_not_found":
                            patient_not_found_count += 1

                        total_processed += 1

                        # Respect limit
                        if self.limit and imported_count >= self.limit:
                            self.stdout.write(f"Reached import limit of {self.limit}")
                            break

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f"Error syncing dailynote {note_key}: {e}")
                        )

                # Check if we should continue
                if self.limit and imported_count >= self.limit:
                    break

                if len(chunk_data) < self.chunk_size:
                    self.stdout.write("Reached end of dailynotes data")
                    break

                # Set up for next chunk
                last_key = max(chunk_data.keys())  # Get the last key for pagination

                # Progress report
                if isinstance(total_dailynotes, int):
                    progress = (total_processed / total_dailynotes) * 100
                    self.stdout.write(
                        f"Progress: {total_processed}/{total_dailynotes} ({progress:.1f}%)"
                    )

            self.stdout.write(
                f"Dailynotes: {imported_count} imported, {patient_not_found_count} patient not found, {skipped_count} skipped, {draft_skipped_count} drafts skipped, {error_count} errors"
            )
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

        # Check if this dailynote already exists using Firebase key (more reliable than content matching)
        existing_note = DailyNote.objects.filter(
            patient=patient,
            content__icontains=f"Firebase ID: {firebase_key}",
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
            datetime_ms = int(dailynote_data["datetime"])
            event_datetime = datetime.fromtimestamp(datetime_ms / 1000, tz=timezone.utc)
            event_datetime = event_datetime.astimezone(
                django_timezone.get_current_timezone()
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid datetime format: {e}")

        # Format content (reusing format_dailynote_content logic from existing import command)
        formatted_content = self.format_dailynote_content(
            dailynote_data["content"],
            dailynote_data.get("username", "Usuário não identificado"),
            firebase_key,
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

    def _send_sync_report_email(self, patients_synced, dailynotes_synced, sync_date, next_cutoff_date):
        """Send sync report via email"""
        try:
            # Calculate total records
            total_synced = patients_synced + dailynotes_synced
            reconciled_patients = getattr(self, "reconciled_patients_count", 0)
            admissions_closed = getattr(self, "admissions_closed_count", 0)
            admissions_created = getattr(self, "admissions_created_count", 0)
            ward_mapped = getattr(self, "ward_mapped_count", 0)
            ward_mapped_to_none = getattr(self, "ward_mapped_to_none_count", 0)
            ward_unresolved = getattr(self, "ward_unresolved_count", 0)
            ward_updated = getattr(self, "ward_updated_count", 0)
            
            # Generate email subject
            subject = f"Firebase Sync Report - {sync_date.strftime('%d/%m/%Y')} - {patients_synced} patients, {dailynotes_synced} dailynotes"
            
            # Generate email body
            body = f"""Relatório de Sincronização Firebase - Sistema EquipeMed

📊 **Resumo da Sincronização:**
- **Data:** {sync_date.strftime('%d/%m/%Y às %H:%M:%S')}
- **Pacientes sincronizados:** {patients_synced}
- **Pacientes reconciliados:** {reconciled_patients}
- **Internações encerradas:** {admissions_closed}
- **Internações criadas:** {admissions_created}
- **Alas mapeadas:** {ward_mapped}
- **Alas aposentadas (mapa -> vazio):** {ward_mapped_to_none}
- **Alas não resolvidas:** {ward_unresolved}
- **Alas atualizadas em internações ativas:** {ward_updated}
- **Evoluções sincronizadas:** {dailynotes_synced}
- **Total de registros:** {total_synced}

📈 **Monitoramento de Adoção:**
Este relatório ajuda a acompanhar a migração do sistema antigo:
- Números decrescentes indicam maior adoção do novo sistema
- Números consistentemente baixos sugerem possibilidade de congelar o sistema antigo

⚙️ **Configurações da Sincronização:**
- **Tamanho do chunk:** {self.chunk_size} registros por consulta Firebase
- **Modo:** {"DRY RUN (sem alterações)" if self.dry_run else "PRODUÇÃO (dados sincronizados)"}"""

            if self.limit:
                body += f"\n- **Limite aplicado:** {self.limit} registros por tipo"

            body += f"""

📅 **Próxima Sincronização:**
Use --since-date {next_cutoff_date} para a próxima execução

⏰ **Automação Sugerida:**
Configure o cron job para executar diariamente e monitorar a tendência dos números.
Quando os números se mantiverem consistentemente baixos por várias semanas, 
considere congelar o sistema antigo.

---
Sistema EquipeMed - Sincronização Automática Firebase"""

            # Send email
            email = EmailMessage(
                subject=subject,
                body=body,
                to=[self.email],
            )
            email.send()
            
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to send sync report email: {str(e)}")
            )
            return False

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
        if hasattr(self, "reconciled_patients_count"):
            self.stdout.write(
                f"  Patients reconciled: {self.reconciled_patients_count}"
            )
        if hasattr(self, "admissions_closed_count"):
            self.stdout.write(
                f"  Admissions closed: {self.admissions_closed_count}"
            )
        if hasattr(self, "admissions_created_count"):
            self.stdout.write(
                f"  Admissions created: {self.admissions_created_count}"
            )
        if hasattr(self, "ward_mapped_count"):
            self.stdout.write(f"  Wards mapped: {self.ward_mapped_count}")
        if hasattr(self, "ward_mapped_to_none_count"):
            self.stdout.write(
                f"  Wards mapped-to-none: {self.ward_mapped_to_none_count}"
            )
        if hasattr(self, "ward_unresolved_count"):
            self.stdout.write(f"  Wards unresolved: {self.ward_unresolved_count}")
        if hasattr(self, "ward_updated_count"):
            self.stdout.write(
                f"  Active-admission ward updates: {self.ward_updated_count}"
            )
        self.stdout.write(f"  Dailynotes synced: {dailynotes_synced}")
        self.stdout.write(
            f"  Total records synced: {patients_synced + dailynotes_synced}"
        )

        if self.limit:
            self.stdout.write(f"  Limited to: {self.limit} records per type")

        self.stdout.write(f"  Chunk size: {self.chunk_size} records per Firebase query")

        # Calculate next cutoff date (today's date for next sync)
        next_cutoff = datetime.now().strftime("%Y-%m-%d")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Next sync cutoff date:"))
        self.stdout.write(f"  Use --since-date {next_cutoff} for the next sync")

        # Send email report if email is configured
        if self.email:
            self.stdout.write("")
            self.stdout.write("Sending sync report via email...")
            sync_date = datetime.now()
            if self._send_sync_report_email(patients_synced, dailynotes_synced, sync_date, next_cutoff):
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Sync report sent successfully to {self.email}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR("✗ Failed to send sync report email (check console for details)")
                )

        self.stdout.write(self.style.SUCCESS("=" * 60))
