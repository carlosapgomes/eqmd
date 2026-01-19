"""
Management command to import medications from CSV file.
Supports the CSV format with columns: DCB, Concentração/Composição, Forma Farmacêutica
"""

import csv
import re
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.drugtemplates.models import DrugTemplate

User = get_user_model()


class Command(BaseCommand):
    help = 'Import medications from CSV file into DrugTemplate model'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file to import')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving data',
        )
        parser.add_argument(
            '--source',
            type=str,
            default='CSV Import',
            help='Import source description (default: "CSV Import")',
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        import_source = options['source']

        # Validate file exists
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                pass
        except FileNotFoundError:
            raise CommandError(f'CSV file not found: {csv_file}')
        except Exception as e:
            raise CommandError(f'Error accessing CSV file: {e}')

        self.stdout.write(f'Starting medication import from: {csv_file}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))

        # Get or create system user
        system_user, created = User.objects.get_or_create(
            username='system',
            defaults={
                'email': 'system@hospital.internal',
                'first_name': 'Sistema',
                'last_name': 'Importação',
                'is_active': True,
                'is_staff': False,
            }
        )
        
        if created:
            self.stdout.write(f'Created system user: {system_user.username}')

        # Import statistics
        total_processed = 0
        imported_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                # Try to detect CSV dialect
                sample = f.read(1024)
                f.seek(0)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)
                
                reader = csv.DictReader(f, dialect=dialect)
                
                # Validate expected columns
                expected_columns = [
                    'Denominação Comum Brasileira (DCB)',
                    'Concentração/Composição', 
                    'Forma Farmacêutica'
                ]
                
                if not all(col in reader.fieldnames for col in expected_columns):
                    raise CommandError(
                        f'CSV file missing expected columns. Expected: {expected_columns}, '
                        f'Found: {list(reader.fieldnames)}'
                    )

                # Process each row individually to avoid transaction rollback on errors
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    total_processed += 1
                    
                    try:
                        # Extract and clean data
                        name = self._clean_field(row['Denominação Comum Brasileira (DCB)'])
                        concentration = self._clean_field(row['Concentração/Composição'])
                        pharmaceutical_form = self._clean_field(row['Forma Farmacêutica'])
                        
                        # Validate required fields
                        if not name:
                            errors.append(f'Row {row_num}: Nome do medicamento é obrigatório')
                            error_count += 1
                            continue
                            
                        if not concentration:
                            errors.append(f'Row {row_num}: Concentração é obrigatória')
                            error_count += 1
                            continue
                            
                        if not pharmaceutical_form:
                            errors.append(f'Row {row_num}: Forma farmacêutica é obrigatória')
                            error_count += 1
                            continue

                        # Normalize concentration (fix decimal separators)
                        concentration = self._normalize_concentration(concentration)
                        
                        # Normalize pharmaceutical form (lowercase)
                        pharmaceutical_form = pharmaceutical_form.lower()

                        # Check for true duplicates (same name + concentration + pharmaceutical form)
                        existing = DrugTemplate.objects.filter(
                            name__iexact=name,
                            concentration__iexact=concentration,
                            pharmaceutical_form__iexact=pharmaceutical_form
                        ).first()
                        
                        if existing:
                            skipped_count += 1
                            continue

                        if not dry_run:
                            # Create new drug template in individual transaction
                            try:
                                with transaction.atomic():
                                    drug_template = DrugTemplate.objects.create(
                                        name=name,
                                        concentration=concentration,
                                        pharmaceutical_form=pharmaceutical_form,
                                        usage_instructions='',  # Empty for imported drugs
                                        creator=system_user,
                                        is_public=True,  # Imported drugs are public by default
                                        is_imported=True,
                                        import_source=import_source
                                    )
                                    imported_count += 1
                                    
                                    if imported_count % 100 == 0:
                                        self.stdout.write(f'Imported {imported_count} medications...')
                            except Exception as create_error:
                                error_count += 1
                                errors.append(f'Row {row_num}: Error creating record - {str(create_error)}')
                        else:
                            imported_count += 1
                            if imported_count % 100 == 0:
                                self.stdout.write(f'Would import {imported_count} medications...')

                    except Exception as e:
                        error_count += 1
                        errors.append(f'Row {row_num}: Error processing record - {str(e)}')

        except Exception as e:
            raise CommandError(f'Error reading CSV file: {e}')

        # Print statistics
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Import Statistics:')
        self.stdout.write(f'Total processed: {total_processed}')
        self.stdout.write(f'Successfully imported: {imported_count}')
        self.stdout.write(f'Skipped (duplicates): {skipped_count}')
        self.stdout.write(f'Errors: {error_count}')
        
        if errors:
            self.stdout.write('\nErrors encountered:')
            for error in errors[:10]:  # Show first 10 errors
                self.stdout.write(f'  - {error}')
            if len(errors) > 10:
                self.stdout.write(f'  ... and {len(errors) - 10} more errors')

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN completed - no data was saved'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nImport completed successfully!'))
            
        return f'Processed: {total_processed}, Imported: {imported_count}, Skipped: {skipped_count}, Errors: {error_count}'

    def _clean_field(self, value):
        """Clean and normalize field value."""
        if not value:
            return ''
        return value.strip()

    def _normalize_concentration(self, concentration):
        """Normalize concentration field - fix decimal separators."""
        if not concentration:
            return concentration
            
        # Replace comma with dot for decimal separator
        normalized = concentration.replace(',', '.')
        
        # Remove extra spaces around units
        normalized = re.sub(r'\s+(mg|g|mL|L|%)\b', r' \1', normalized, flags=re.IGNORECASE)
        
        return normalized.strip()