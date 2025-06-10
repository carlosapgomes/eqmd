"""
Management command to assign existing users to hospitals.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from apps.hospitals.models import Hospital


class Command(BaseCommand):
    help = 'Assign users to hospitals'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            required=True,
            choices=['assign_all', 'assign_user', 'list_assignments', 'clear_assignments'],
            help='Action to perform: assign_all (assign all users to all hospitals), assign_user (assign specific user), list_assignments (show current assignments), clear_assignments (remove all assignments)'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username to assign (required for assign_user action)'
        )
        parser.add_argument(
            '--hospital',
            type=str,
            help='Hospital name or ID to assign user to (optional for assign_user, defaults to all hospitals)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        User = get_user_model()
        action = options['action']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        if action == 'assign_all':
            self.assign_all_users_to_all_hospitals(dry_run)
        elif action == 'assign_user':
            self.assign_user_to_hospitals(options, dry_run)
        elif action == 'list_assignments':
            self.list_assignments()
        elif action == 'clear_assignments':
            self.clear_assignments(dry_run)

    def assign_all_users_to_all_hospitals(self, dry_run=False):
        """Assign all users to all hospitals (useful for initial setup)."""
        User = get_user_model()
        users = User.objects.all()
        hospitals = Hospital.objects.all()

        if not hospitals.exists():
            raise CommandError('No hospitals found. Please create hospitals first.')

        self.stdout.write(f'Found {users.count()} users and {hospitals.count()} hospitals')

        for user in users:
            current_hospitals = list(user.hospitals.all()) if hasattr(user, 'hospitals') else []
            self.stdout.write(f'User: {user.username} ({user.get_full_name()})')
            self.stdout.write(f'  Current hospitals: {[h.name for h in current_hospitals]}')
            
            if not dry_run:
                # Add all hospitals to user
                user.hospitals.set(hospitals)
                # Set first hospital as last_hospital if not set
                if not user.last_hospital and hospitals.exists():
                    user.last_hospital = hospitals.first()
                    user.save(update_fields=['last_hospital'])
                
            self.stdout.write(f'  Would assign to: {[h.name for h in hospitals]}')

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully assigned {users.count()} users to all {hospitals.count()} hospitals')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Would assign {users.count()} users to all {hospitals.count()} hospitals')
            )

    def assign_user_to_hospitals(self, options, dry_run=False):
        """Assign a specific user to hospitals."""
        User = get_user_model()
        username = options.get('user')
        hospital_name = options.get('hospital')

        if not username:
            raise CommandError('--user is required for assign_user action')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" not found')

        # Get hospitals to assign
        if hospital_name:
            # Try to find hospital by name first, then by ID
            hospitals = Hospital.objects.filter(name__icontains=hospital_name)
            if not hospitals.exists():
                try:
                    hospitals = Hospital.objects.filter(id=hospital_name)
                except ValueError:
                    pass
            
            if not hospitals.exists():
                raise CommandError(f'Hospital "{hospital_name}" not found')
        else:
            # Assign to all hospitals
            hospitals = Hospital.objects.all()

        if not hospitals.exists():
            raise CommandError('No hospitals found to assign')

        current_hospitals = list(user.hospitals.all()) if hasattr(user, 'hospitals') else []
        self.stdout.write(f'User: {user.username} ({user.get_full_name()})')
        self.stdout.write(f'Current hospitals: {[h.name for h in current_hospitals]}')
        self.stdout.write(f'Will assign to: {[h.name for h in hospitals]}')

        if not dry_run:
            # Add hospitals to user (preserving existing ones)
            for hospital in hospitals:
                user.hospitals.add(hospital)
            
            # Set first assigned hospital as last_hospital if not set
            if not user.last_hospital:
                user.last_hospital = hospitals.first()
                user.save(update_fields=['last_hospital'])

            self.stdout.write(
                self.style.SUCCESS(f'Successfully assigned user "{username}" to {hospitals.count()} hospitals')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Would assign user "{username}" to {hospitals.count()} hospitals')
            )

    def list_assignments(self):
        """List current user-hospital assignments."""
        User = get_user_model()
        users = User.objects.prefetch_related('hospitals', 'last_hospital').all()

        self.stdout.write('Current user-hospital assignments:')
        self.stdout.write('-' * 60)

        for user in users:
            hospitals = list(user.hospitals.all()) if hasattr(user, 'hospitals') else []
            last_hospital = user.last_hospital if hasattr(user, 'last_hospital') else None
            
            self.stdout.write(f'User: {user.username} ({user.get_full_name()})')
            self.stdout.write(f'  Profession: {user.get_profession_type_display() if user.profession_type is not None else "Not set"}')
            self.stdout.write(f'  Hospitals: {[h.name for h in hospitals] if hospitals else "None"}')
            self.stdout.write(f'  Last Hospital: {last_hospital.name if last_hospital else "None"}')
            self.stdout.write('')

    def clear_assignments(self, dry_run=False):
        """Clear all user-hospital assignments."""
        User = get_user_model()
        users = User.objects.all()

        self.stdout.write(f'Found {users.count()} users')

        if not dry_run:
            for user in users:
                if hasattr(user, 'hospitals'):
                    user.hospitals.clear()
                if hasattr(user, 'last_hospital'):
                    user.last_hospital = None
                    user.save(update_fields=['last_hospital'])

            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleared hospital assignments for {users.count()} users')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Would clear hospital assignments for {users.count()} users')
            )