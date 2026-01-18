"""
Management command to import ICD-10 (CID) codes from CSV/JSON files.
Supports both initial import and incremental updates.
"""

import csv
import json
import logging
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, IntegrityError
from django.contrib.postgres.search import SearchVector
from apps.core.models import Icd10Code

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import ICD-10 codes from CSV or JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to CSV or JSON file containing ICD-10 data'
        )
        parser.add_argument(
            '--format',
            choices=['csv', 'json'],
            help='File format (auto-detected if not specified)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of codes to process in each batch (default: 1000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate data without saving to database'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing codes instead of skipping them'
        )
        parser.add_argument(
            '--deactivate-missing',
            action='store_true',
            help='Mark codes as inactive if not present in import file'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])

        if not file_path.exists():
            raise CommandError(f"File does not exist: {file_path}")

        file_format = options['format']
        if not file_format:
            file_format = 'json' if file_path.suffix.lower() == '.json' else 'csv'

        self.stdout.write(f"Importing ICD-10 codes from: {file_path}")
        self.stdout.write(f"File format: {file_format}")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be saved"))

        try:
            if file_format == 'csv':
                codes_data = self._load_csv(file_path)
            else:
                codes_data = self._load_json(file_path)

            self._process_codes(
                codes_data,
                batch_size=options['batch_size'],
                dry_run=options['dry_run'],
                update=options['update'],
                verbose=options['verbose']
            )

            if options['deactivate_missing'] and not options['dry_run']:
                self._deactivate_missing_codes(codes_data, options['verbose'])

        except Exception as e:
            logger.exception("Error importing ICD-10 codes")
            raise CommandError(f"Import failed: {str(e)}")

    def _load_csv(self, file_path):
        codes = []

        with open(file_path, 'r', encoding='utf-8') as csvfile:
            sample = csvfile.read(1024)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter

            reader = csv.DictReader(csvfile, delimiter=delimiter)

            fieldnames = reader.fieldnames or []
            has_portuguese = 'codigo' in fieldnames and 'descricao' in fieldnames
            has_english = 'code' in fieldnames and 'description' in fieldnames

            if not has_portuguese and not has_english:
                raise CommandError(
                    "CSV must contain columns: codigo/descricao or code/description. "
                    f"Found: {', '.join(fieldnames)}"
                )

            for row_num, row in enumerate(reader, start=2):
                try:
                    if has_portuguese:
                        code_raw = row.get('codigo')
                        description_raw = row.get('descricao')
                    else:
                        code_raw = row.get('code')
                        description_raw = row.get('description')

                    code = str(code_raw).strip().upper() if code_raw is not None else ''
                    description = str(description_raw).strip() if description_raw is not None else ''

                    if not code or not description:
                        self.stdout.write(
                            self.style.WARNING(f"Row {row_num}: Skipping empty code or description")
                        )
                        continue

                    codes.append({
                        'code': code,
                        'description': description,
                        'is_active': str(row.get('is_active', 'true')).lower() in ['true', '1', 'yes']
                    })

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Row {row_num}: Error processing - {str(e)}")
                    )

        return codes

    def _load_json(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)

        if isinstance(data, list):
            codes = data
        elif isinstance(data, dict) and 'codes' in data:
            codes = data['codes']
        else:
            raise CommandError("JSON must be a list or contain a 'codes' key with a list")

        cleaned_codes = []
        for i, item in enumerate(codes):
            if not isinstance(item, dict):
                self.stdout.write(
                    self.style.WARNING(f"Item {i}: Not a dictionary, skipping")
                )
                continue

            if 'code' not in item or 'description' not in item:
                self.stdout.write(
                    self.style.WARNING(f"Item {i}: Missing code or description, skipping")
                )
                continue

            code = str(item['code']).strip().upper()
            description = str(item['description']).strip()

            if not code or not description:
                self.stdout.write(
                    self.style.WARNING(f"Item {i}: Empty code or description, skipping")
                )
                continue

            cleaned_codes.append({
                'code': code,
                'description': description,
                'is_active': item.get('is_active', True)
            })

        return cleaned_codes

    def _process_codes(self, codes_data, batch_size, dry_run, update, verbose):
        total_count = len(codes_data)
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        self.stdout.write(f"Processing {total_count} ICD-10 codes...")

        for i in range(0, total_count, batch_size):
            batch = codes_data[i:i + batch_size]

            if verbose:
                self.stdout.write(f"Processing batch {i//batch_size + 1}: items {i+1}-{min(i+batch_size, total_count)}")

            if not dry_run:
                batch_created, batch_updated, batch_skipped, batch_errors = self._process_batch(
                    batch, update, verbose
                )
            else:
                batch_created, batch_updated, batch_skipped, batch_errors = self._validate_batch(
                    batch, update, verbose
                )

            created_count += batch_created
            updated_count += batch_updated
            skipped_count += batch_skipped
            error_count += batch_errors

        if not dry_run and (created_count > 0 or updated_count > 0):
            self.stdout.write("Updating search vectors...")
            self._update_search_vectors()

        self.stdout.write(self.style.SUCCESS(
            f"\nImport completed:\n"
            f"  Created: {created_count}\n"
            f"  Updated: {updated_count}\n"
            f"  Skipped: {skipped_count}\n"
            f"  Errors: {error_count}\n"
            f"  Total processed: {total_count}"
        ))

    def _process_batch(self, batch, update, verbose):
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        with transaction.atomic():
            for code_data in batch:
                try:
                    code, created = Icd10Code.objects.get_or_create(
                        code=code_data['code'],
                        defaults={
                            'description': code_data['description'],
                            'is_active': code_data['is_active']
                        }
                    )

                    if created:
                        created_count += 1
                        if verbose:
                            self.stdout.write(f"  Created: {code_data['code']}")
                    elif update:
                        updated = False
                        if code.description != code_data['description']:
                            code.description = code_data['description']
                            updated = True
                        if code.is_active != code_data['is_active']:
                            code.is_active = code_data['is_active']
                            updated = True

                        if updated:
                            code.save()
                            updated_count += 1
                            if verbose:
                                self.stdout.write(f"  Updated: {code_data['code']}")
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1
                        if verbose:
                            self.stdout.write(f"  Skipped (exists): {code_data['code']}")

                except IntegrityError as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"  Error with {code_data['code']}: {str(e)}")
                    )
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"  Unexpected error with {code_data['code']}: {str(e)}")
                    )

        return created_count, updated_count, skipped_count, error_count

    def _validate_batch(self, batch, update, verbose):
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        for code_data in batch:
            try:
                exists = Icd10Code.objects.filter(code=code_data['code']).exists()

                if not exists:
                    created_count += 1
                    if verbose:
                        self.stdout.write(f"  Would create: {code_data['code']}")
                elif update:
                    updated_count += 1
                    if verbose:
                        self.stdout.write(f"  Would update: {code_data['code']}")
                else:
                    skipped_count += 1
                    if verbose:
                        self.stdout.write(f"  Would skip: {code_data['code']}")

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  Validation error with {code_data['code']}: {str(e)}")
                )

        return created_count, updated_count, skipped_count, error_count

    def _update_search_vectors(self):
        from django.db import connection

        if connection.vendor != 'postgresql':
            self.stdout.write("Skipping search vector updates (PostgreSQL only).")
            return

        try:
            Icd10Code.objects.update(
                search_vector=SearchVector('code', 'description')
            )
            self.stdout.write(self.style.SUCCESS("Search vectors updated successfully"))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error updating search vectors: {str(e)}")
            )

    def _deactivate_missing_codes(self, codes_data, verbose):
        imported_codes = {code['code'] for code in codes_data}

        missing_codes = Icd10Code.objects.filter(
            is_active=True
        ).exclude(
            code__in=imported_codes
        )

        deactivated_count = missing_codes.update(is_active=False)

        if deactivated_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Deactivated {deactivated_count} ICD-10 code(s) not found in import file")
            )

            if verbose:
                for code in missing_codes:
                    self.stdout.write(f"  Deactivated: {code.code}")
        else:
            self.stdout.write("No ICD-10 codes to deactivate")
