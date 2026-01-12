"""
Management command to import medical procedures from CSV/JSON files.
Supports both initial import and incremental updates.
"""

import csv
import json
import logging
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, IntegrityError
from django.contrib.postgres.search import SearchVector
from apps.core.models import MedicalProcedure

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import medical procedures from CSV or JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to CSV or JSON file containing procedures data'
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
            help='Number of procedures to process in each batch (default: 1000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate data without saving to database'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing procedures instead of skipping them'
        )
        parser.add_argument(
            '--deactivate-missing',
            action='store_true',
            help='Mark procedures as inactive if not present in import file'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )

    def handle(self, *args, **options):
        """Main command handler."""
        
        file_path = Path(options['file'])
        
        # Validate file exists
        if not file_path.exists():
            raise CommandError(f"File does not exist: {file_path}")
        
        # Auto-detect format if not specified
        file_format = options['format']
        if not file_format:
            file_format = 'json' if file_path.suffix.lower() == '.json' else 'csv'
        
        self.stdout.write(f"Importing procedures from: {file_path}")
        self.stdout.write(f"File format: {file_format}")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be saved"))
        
        try:
            # Load data from file
            if file_format == 'csv':
                procedures_data = self._load_csv(file_path)
            else:
                procedures_data = self._load_json(file_path)
            
            # Process the data
            self._process_procedures(
                procedures_data,
                batch_size=options['batch_size'],
                dry_run=options['dry_run'],
                update=options['update'],
                verbose=options['verbose']
            )
            
            if options['deactivate_missing'] and not options['dry_run']:
                self._deactivate_missing_procedures(procedures_data, options['verbose'])
                
        except Exception as e:
            logger.exception("Error importing procedures")
            raise CommandError(f"Import failed: {str(e)}")

    def _load_csv(self, file_path):
        """Load procedures from CSV file."""
        procedures = []
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # Try to detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            # Validate required columns
            required_cols = ['code', 'description']
            if not all(col in reader.fieldnames for col in required_cols):
                raise CommandError(
                    f"CSV must contain columns: {', '.join(required_cols)}. "
                    f"Found: {', '.join(reader.fieldnames)}"
                )
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header
                try:
                    # Clean and validate data
                    code = str(row['code']).strip().upper()
                    description = str(row['description']).strip()
                    
                    if not code or not description:
                        self.stdout.write(
                            self.style.WARNING(f"Row {row_num}: Skipping empty code or description")
                        )
                        continue
                    
                    procedures.append({
                        'code': code,
                        'description': description,
                        'is_active': str(row.get('is_active', 'true')).lower() in ['true', '1', 'yes']
                    })
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Row {row_num}: Error processing - {str(e)}")
                    )
        
        return procedures

    def _load_json(self, file_path):
        """Load procedures from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
        
        # Handle different JSON structures
        if isinstance(data, list):
            procedures = data
        elif isinstance(data, dict) and 'procedures' in data:
            procedures = data['procedures']
        else:
            raise CommandError("JSON must be a list or contain a 'procedures' key with a list")
        
        # Validate and clean data
        cleaned_procedures = []
        for i, proc in enumerate(procedures):
            if not isinstance(proc, dict):
                self.stdout.write(
                    self.style.WARNING(f"Item {i}: Not a dictionary, skipping")
                )
                continue
            
            if 'code' not in proc or 'description' not in proc:
                self.stdout.write(
                    self.style.WARNING(f"Item {i}: Missing code or description, skipping")
                )
                continue
            
            code = str(proc['code']).strip().upper()
            description = str(proc['description']).strip()
            
            if not code or not description:
                self.stdout.write(
                    self.style.WARNING(f"Item {i}: Empty code or description, skipping")
                )
                continue
            
            cleaned_procedures.append({
                'code': code,
                'description': description,
                'is_active': proc.get('is_active', True)
            })
        
        return cleaned_procedures

    def _process_procedures(self, procedures_data, batch_size, dry_run, update, verbose):
        """Process procedures in batches."""
        
        total_count = len(procedures_data)
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        self.stdout.write(f"Processing {total_count} procedures...")
        
        # Process in batches
        for i in range(0, total_count, batch_size):
            batch = procedures_data[i:i + batch_size]
            
            if verbose:
                self.stdout.write(f"Processing batch {i//batch_size + 1}: items {i+1}-{min(i+batch_size, total_count)}")
            
            if not dry_run:
                batch_created, batch_updated, batch_skipped, batch_errors = self._process_batch(
                    batch, update, verbose
                )
            else:
                # In dry run, just validate the data
                batch_created, batch_updated, batch_skipped, batch_errors = self._validate_batch(
                    batch, update, verbose
                )
            
            created_count += batch_created
            updated_count += batch_updated
            skipped_count += batch_skipped
            error_count += batch_errors
        
        # Update search vectors if not dry run
        if not dry_run and (created_count > 0 or updated_count > 0):
            self.stdout.write("Updating search vectors...")
            self._update_search_vectors()
        
        # Summary
        self.stdout.write(self.style.SUCCESS(
            f"\nImport completed:\n"
            f"  Created: {created_count}\n"
            f"  Updated: {updated_count}\n"
            f"  Skipped: {skipped_count}\n"
            f"  Errors: {error_count}\n"
            f"  Total processed: {total_count}"
        ))

    def _process_batch(self, batch, update, verbose):
        """Process a single batch of procedures."""
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        with transaction.atomic():
            for proc_data in batch:
                try:
                    procedure, created = MedicalProcedure.objects.get_or_create(
                        code=proc_data['code'],
                        defaults={
                            'description': proc_data['description'],
                            'is_active': proc_data['is_active']
                        }
                    )
                    
                    if created:
                        created_count += 1
                        if verbose:
                            self.stdout.write(f"  Created: {proc_data['code']}")
                    elif update:
                        # Update existing procedure
                        updated = False
                        if procedure.description != proc_data['description']:
                            procedure.description = proc_data['description']
                            updated = True
                        if procedure.is_active != proc_data['is_active']:
                            procedure.is_active = proc_data['is_active']
                            updated = True
                        
                        if updated:
                            procedure.save()
                            updated_count += 1
                            if verbose:
                                self.stdout.write(f"  Updated: {proc_data['code']}")
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1
                        if verbose:
                            self.stdout.write(f"  Skipped (exists): {proc_data['code']}")
                
                except IntegrityError as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"  Error with {proc_data['code']}: {str(e)}")
                    )
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"  Unexpected error with {proc_data['code']}: {str(e)}")
                    )
        
        return created_count, updated_count, skipped_count, error_count

    def _validate_batch(self, batch, update, verbose):
        """Validate a batch without saving (for dry run)."""
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for proc_data in batch:
            try:
                # Check if procedure exists
                exists = MedicalProcedure.objects.filter(code=proc_data['code']).exists()
                
                if not exists:
                    created_count += 1
                    if verbose:
                        self.stdout.write(f"  Would create: {proc_data['code']}")
                elif update:
                    updated_count += 1
                    if verbose:
                        self.stdout.write(f"  Would update: {proc_data['code']}")
                else:
                    skipped_count += 1
                    if verbose:
                        self.stdout.write(f"  Would skip: {proc_data['code']}")
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  Validation error with {proc_data['code']}: {str(e)}")
                )
        
        return created_count, updated_count, skipped_count, error_count

    def _update_search_vectors(self):
        """Update search vectors for full-text search."""
        try:
            # Update search vectors for all procedures
            MedicalProcedure.objects.update(
                search_vector=SearchVector('code', 'description')
            )
            self.stdout.write(self.style.SUCCESS("Search vectors updated successfully"))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error updating search vectors: {str(e)}")
            )

    def _deactivate_missing_procedures(self, procedures_data, verbose):
        """Mark procedures as inactive if not present in import file."""
        imported_codes = {proc['code'] for proc in procedures_data}
        
        missing_procedures = MedicalProcedure.objects.filter(
            is_active=True
        ).exclude(
            code__in=imported_codes
        )
        
        deactivated_count = missing_procedures.update(is_active=False)
        
        if deactivated_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Deactivated {deactivated_count} procedures not found in import file")
            )
            
            if verbose:
                for procedure in missing_procedures:
                    self.stdout.write(f"  Deactivated: {procedure.code}")
        else:
            self.stdout.write("No procedures to deactivate")