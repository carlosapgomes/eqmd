import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from apps.patients.models import Ward

User = get_user_model()


class Command(BaseCommand):
    help = "Backup and restore ward data to/from JSON files"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Available actions')
        
        # Backup subcommand
        backup_parser = subparsers.add_parser('backup', help='Backup wards to JSON file')
        backup_parser.add_argument(
            '--output',
            type=str,
            default='ward_backup.json',
            help='Output file path (default: ward_backup.json)'
        )
        backup_parser.add_argument(
            '--active-only',
            action='store_true',
            help='Backup only active wards'
        )
        
        # Restore subcommand
        restore_parser = subparsers.add_parser('restore', help='Restore wards from JSON file')
        restore_parser.add_argument(
            '--input',
            type=str,
            default='ward_backup.json',
            help='Input file path (default: ward_backup.json)'
        )
        restore_parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Delete all existing wards before restoring'
        )
        restore_parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing wards with same abbreviation'
        )

    def handle(self, *args, **options):
        action = options.get('action')
        
        if action == 'backup':
            self.backup_wards(options)
        elif action == 'restore':
            self.restore_wards(options)
        else:
            self.stdout.write(
                self.style.ERROR('Please specify an action: backup or restore')
            )
            self.stdout.write('Usage: python manage.py ward_backup backup --output wards.json')
            self.stdout.write('       python manage.py ward_backup restore --input wards.json')

    def backup_wards(self, options):
        """Backup wards to JSON file"""
        output_file = options['output']
        active_only = options['active_only']
        
        try:
            # Get wards to backup
            queryset = Ward.objects.all()
            if active_only:
                queryset = queryset.filter(is_active=True)
            
            wards = queryset.order_by('name')
            
            if not wards.exists():
                self.stdout.write(
                    self.style.WARNING('No wards found to backup')
                )
                return
            
            # Prepare data for export
            ward_data = []
            for ward in wards:
                ward_dict = {
                    'name': ward.name,
                    'abbreviation': ward.abbreviation,
                    'description': ward.description,
                    'is_active': ward.is_active,
                    'floor': ward.floor,
                    'capacity_estimate': ward.capacity_estimate,
                }
                ward_data.append(ward_dict)
            
            # Create backup metadata
            backup_data = {
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'total_wards': len(ward_data),
                    'active_only': active_only,
                    'version': '1.0'
                },
                'wards': ward_data
            }
            
            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully backed up {len(ward_data)} wards to {output_file}'
                )
            )
            
        except Exception as e:
            raise CommandError(f'Failed to backup wards: {str(e)}')

    def restore_wards(self, options):
        """Restore wards from JSON file"""
        input_file = options['input']
        clear_existing = options['clear_existing']
        update_existing = options['update_existing']
        
        # Check if file exists
        if not os.path.exists(input_file):
            raise CommandError(f'Input file does not exist: {input_file}')
        
        # Get user for created_by/updated_by fields
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.filter(is_staff=True).first()
        if not admin_user:
            admin_user = User.objects.first()
        
        if not admin_user:
            raise CommandError('No users found. Create a user first.')
        
        try:
            # Load backup data
            with open(input_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Validate backup structure
            if 'wards' not in backup_data:
                raise CommandError('Invalid backup file: missing "wards" key')
            
            ward_data = backup_data['wards']
            
            if not ward_data:
                self.stdout.write(
                    self.style.WARNING('No wards found in backup file')
                )
                return
            
            # Show metadata if available
            if 'metadata' in backup_data:
                metadata = backup_data['metadata']
                self.stdout.write(f"Backup created: {metadata.get('created_at', 'Unknown')}")
                self.stdout.write(f"Total wards in backup: {metadata.get('total_wards', len(ward_data))}")
            
            # Clear existing wards if requested
            if clear_existing:
                deleted_count = Ward.objects.count()
                Ward.objects.all().delete()
                self.stdout.write(f"Deleted {deleted_count} existing wards")
            
            # Restore wards
            created_count = 0
            updated_count = 0
            skipped_count = 0
            
            for ward_info in ward_data:
                try:
                    abbreviation = ward_info.get('abbreviation')
                    if not abbreviation:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Skipping ward with missing abbreviation: {ward_info}'
                            )
                        )
                        skipped_count += 1
                        continue
                    
                    # Check if ward already exists
                    existing_ward = Ward.objects.filter(abbreviation=abbreviation).first()
                    
                    if existing_ward:
                        if update_existing:
                            # Update existing ward
                            for field, value in ward_info.items():
                                if field != 'abbreviation':  # Don't update the key field
                                    setattr(existing_ward, field, value)
                            existing_ward.updated_by = admin_user
                            existing_ward.save()
                            updated_count += 1
                            self.stdout.write(f"Updated ward: {existing_ward}")
                        else:
                            self.stdout.write(f"Ward already exists (skipped): {existing_ward}")
                            skipped_count += 1
                    else:
                        # Create new ward
                        ward = Ward.objects.create(
                            name=ward_info.get('name', ''),
                            abbreviation=abbreviation,
                            description=ward_info.get('description', ''),
                            is_active=ward_info.get('is_active', True),
                            floor=ward_info.get('floor', ''),
                            capacity_estimate=ward_info.get('capacity_estimate'),
                            created_by=admin_user,
                            updated_by=admin_user,
                        )
                        created_count += 1
                        self.stdout.write(f"Created ward: {ward}")
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to process ward {ward_info.get("abbreviation", "Unknown")}: {str(e)}'
                        )
                    )
                    skipped_count += 1
            
            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f'Restore completed: {created_count} created, '
                    f'{updated_count} updated, {skipped_count} skipped'
                )
            )
            
        except json.JSONDecodeError:
            raise CommandError(f'Invalid JSON format in file: {input_file}')
        except Exception as e:
            raise CommandError(f'Failed to restore wards: {str(e)}')