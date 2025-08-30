# apps/accounts/management/commands/bulk_user_operations.py

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import csv

class Command(BaseCommand):
    help = 'Perform essential bulk operations on users (simplified)'
    
    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='operation', help='Bulk operation to perform')
        
        # Bulk extend operation
        extend_parser = subparsers.add_parser('extend', help='Bulk extend user access')
        extend_parser.add_argument('--csv-file', required=True, help='CSV file with usernames and extension data')
        extend_parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
        
        # Bulk expiration set (simplified)
        expiration_parser = subparsers.add_parser('set-expiration', help='Bulk set expiration dates')
        expiration_parser.add_argument('--role', choices=['resident', 'student'], required=True)
        expiration_parser.add_argument('--months', type=int, required=True, help='Months from now to expire')
        expiration_parser.add_argument('--reason', default='Bulk expiration update')
    
    def handle(self, *args, **options):
        operation = options['operation']
        
        if operation == 'extend':
            self._handle_bulk_extend(options)
        elif operation == 'set-expiration':
            self._handle_bulk_set_expiration(options)
        else:
            raise CommandError('No operation specified')
    
    def _handle_bulk_extend(self, options):
        """Handle bulk user access extension"""
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        
        self.stdout.write(f'Processing bulk extension from {csv_file}')
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                required_fields = ['username', 'days', 'reason']
                
                if not all(field in reader.fieldnames for field in required_fields):
                    raise CommandError(f'CSV must contain columns: {", ".join(required_fields)}')
                
                results = {'success': 0, 'errors': []}
                
                for row in reader:
                    try:
                        username = row['username'].strip()
                        days = int(row['days'])
                        reason = row['reason'].strip()
                        
                        if not dry_run:
                            self._extend_single_user(username, days, reason)
                        
                        results['success'] += 1
                        self.stdout.write(f'  ✓ {username}: +{days} days')
                        
                    except Exception as e:
                        results['errors'].append((row.get('username', 'Unknown'), str(e)))
                        self.stdout.write(f'  ✗ {username}: {e}')
                
                self.stdout.write(self.style.SUCCESS(
                    f"Success: {results['success']}, Errors: {len(results['errors'])}"
                ))
                
        except FileNotFoundError:
            raise CommandError(f'File not found: {csv_file}')
    
    def _extend_single_user(self, username, days, reason):
        """Extend access for a single user"""
        from apps.accounts.models import EqmdCustomUser
        
        user = EqmdCustomUser.objects.get(username=username)
        user.extend_access(days, reason, None)
    
    def _handle_bulk_set_expiration(self, options):
        """Set expiration dates for users by role (simplified)"""
        from apps.accounts.models import EqmdCustomUser
        
        role = options['role']
        months = options['months']
        reason = options['reason']
        
        # Map role names to profession types
        role_mapping = {
            'resident': 1,
            'student': 4
        }
        
        profession_type = role_mapping[role]
        expiration_date = timezone.now() + timedelta(days=months * 30)
        
        users = EqmdCustomUser.objects.filter(
            profession_type=profession_type,
            is_active=True
        )
        
        self.stdout.write(f'Found {users.count()} {role}s to update')
        
        confirm = input(f'Set expiration to {expiration_date.strftime("%d/%m/%Y")} for all {role}s? (y/N): ')
        if confirm.lower() != 'y':
            self.stdout.write('Operation cancelled.')
            return
        
        with transaction.atomic():
            updated_count = users.update(
                access_expires_at=expiration_date,
                expiration_reason='end_of_internship' if role == 'resident' else 'end_of_rotation'
            )
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully updated expiration for {updated_count} {role}s'
        ))