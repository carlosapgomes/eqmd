"""
Management command for user permission management.

This command provides tools for assigning permissions to users,
listing user permissions, and resetting permissions.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.core.permissions.constants import (
    MEDICAL_DOCTOR,
    RESIDENT,
    NURSE,
    PHYSIOTHERAPIST,
    STUDENT,
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Manage user permissions and group assignments'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['assign', 'remove', 'list', 'reset', 'sync'],
            required=True,
            help='Action to perform'
        )
        
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to manage'
        )
        
        parser.add_argument(
            '--user-email',
            type=str,
            help='User email to manage (alternative to user-id)'
        )
        
        parser.add_argument(
            '--group-name',
            type=str,
            help='Group name to assign/remove'
        )
        
        parser.add_argument(
            '--permission',
            type=str,
            help='Permission to assign/remove (format: app_label.codename)'
        )
        
        parser.add_argument(
            '--profession',
            type=str,
            choices=['medical_doctor', 'resident', 'nurse', 'physiotherapist', 'student'],
            help='Profession type for automatic group assignment'
        )
        
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Apply action to all users'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'assign':
            self.assign_permissions(options)
        elif action == 'remove':
            self.remove_permissions(options)
        elif action == 'list':
            self.list_user_permissions(options)
        elif action == 'reset':
            self.reset_user_permissions(options)
        elif action == 'sync':
            self.sync_user_groups(options)
    
    def assign_permissions(self, options):
        """Assign permissions or groups to users."""
        self.stdout.write(self.style.SUCCESS('Assigning Permissions'))
        self.stdout.write('=' * 40)
        
        users = self._get_users(options)
        if not users:
            return
        
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        
        with transaction.atomic():
            for user in users:
                self._assign_to_user(user, options, dry_run)
    
    def _assign_to_user(self, user, options, dry_run):
        """Assign permissions or groups to a specific user."""
        group_name = options.get('group_name')
        permission = options.get('permission')
        profession = options.get('profession')
        
        if group_name:
            self._assign_group(user, group_name, dry_run)
        
        if permission:
            self._assign_permission(user, permission, dry_run)
        
        if profession:
            self._assign_profession_group(user, profession, dry_run)
    
    def _assign_group(self, user, group_name, dry_run):
        """Assign a group to a user."""
        try:
            group = Group.objects.get(name=group_name)
            if not dry_run:
                user.groups.add(group)
            self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}✓ Added {user.email} to group '{group_name}'")
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ Group '{group_name}' does not exist"))
    
    def _assign_permission(self, user, permission, dry_run):
        """Assign a permission to a user."""
        try:
            app_label, codename = permission.split('.')
            perm = Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename
            )
            if not dry_run:
                user.user_permissions.add(perm)
            self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}✓ Added permission '{permission}' to {user.email}")
        except ValueError:
            self.stdout.write(self.style.ERROR(f"✗ Invalid permission format: {permission}"))
        except Permission.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ Permission '{permission}' does not exist"))
    
    def _assign_profession_group(self, user, profession, dry_run):
        """Assign profession-based group to a user."""
        profession_to_group = {
            'medical_doctor': 'Medical Doctors',
            'resident': 'Residents',
            'nurse': 'Nurses',
            'physiotherapist': 'Physiotherapists',
            'student': 'Students',
        }
        
        group_name = profession_to_group.get(profession)
        if group_name:
            self._assign_group(user, group_name, dry_run)
            
            # Also update user's profession type if it's different
            if hasattr(user, 'profession_type') and user.profession_type != profession:
                if not dry_run:
                    user.profession_type = profession
                    user.save()
                self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}✓ Updated {user.email} profession to '{profession}'")
    
    def remove_permissions(self, options):
        """Remove permissions or groups from users."""
        self.stdout.write(self.style.SUCCESS('Removing Permissions'))
        self.stdout.write('=' * 40)
        
        users = self._get_users(options)
        if not users:
            return
        
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        
        with transaction.atomic():
            for user in users:
                self._remove_from_user(user, options, dry_run)
    
    def _remove_from_user(self, user, options, dry_run):
        """Remove permissions or groups from a specific user."""
        group_name = options.get('group_name')
        permission = options.get('permission')
        
        if group_name:
            self._remove_group(user, group_name, dry_run)
        
        if permission:
            self._remove_permission(user, permission, dry_run)
    
    def _remove_group(self, user, group_name, dry_run):
        """Remove a group from a user."""
        try:
            group = Group.objects.get(name=group_name)
            if user.groups.filter(name=group_name).exists():
                if not dry_run:
                    user.groups.remove(group)
                self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}✓ Removed {user.email} from group '{group_name}'")
            else:
                self.stdout.write(f"⚠ {user.email} is not in group '{group_name}'")
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ Group '{group_name}' does not exist"))
    
    def _remove_permission(self, user, permission, dry_run):
        """Remove a permission from a user."""
        try:
            app_label, codename = permission.split('.')
            perm = Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename
            )
            if user.user_permissions.filter(id=perm.id).exists():
                if not dry_run:
                    user.user_permissions.remove(perm)
                self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}✓ Removed permission '{permission}' from {user.email}")
            else:
                self.stdout.write(f"⚠ {user.email} does not have permission '{permission}'")
        except ValueError:
            self.stdout.write(self.style.ERROR(f"✗ Invalid permission format: {permission}"))
        except Permission.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ Permission '{permission}' does not exist"))
    
    def list_user_permissions(self, options):
        """List permissions for users."""
        self.stdout.write(self.style.SUCCESS('User Permissions'))
        self.stdout.write('=' * 40)
        
        users = self._get_users(options)
        if not users:
            return
        
        for user in users:
            self._list_user_details(user)
    
    def _list_user_details(self, user):
        """List detailed permissions for a user."""
        self.stdout.write(f"\nUser: {user.email}")
        self.stdout.write(f"  ID: {user.id}")
        self.stdout.write(f"  Active: {user.is_active}")
        self.stdout.write(f"  Staff: {user.is_staff}")
        self.stdout.write(f"  Superuser: {user.is_superuser}")
        
        if hasattr(user, 'profession_type'):
            self.stdout.write(f"  Profession: {user.profession_type or 'Not set'}")
        
        # Groups
        groups = user.groups.all()
        self.stdout.write(f"  Groups ({groups.count()}):")
        for group in groups:
            self.stdout.write(f"    - {group.name}")
        
        # Direct permissions
        user_perms = user.user_permissions.all()
        self.stdout.write(f"  Direct Permissions ({user_perms.count()}):")
        for perm in user_perms:
            self.stdout.write(f"    - {perm.content_type.app_label}.{perm.codename}")
        
        # All effective permissions
        all_perms = user.get_all_permissions()
        self.stdout.write(f"  Total Effective Permissions: {len(all_perms)}")
    
    def reset_user_permissions(self, options):
        """Reset user permissions."""
        self.stdout.write(self.style.SUCCESS('Resetting User Permissions'))
        self.stdout.write('=' * 40)
        
        users = self._get_users(options)
        if not users:
            return
        
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        
        with transaction.atomic():
            for user in users:
                self._reset_user(user, dry_run)
    
    def _reset_user(self, user, dry_run):
        """Reset permissions for a specific user."""
        # Remove all groups
        group_count = user.groups.count()
        if not dry_run:
            user.groups.clear()
        
        # Remove all direct permissions
        perm_count = user.user_permissions.count()
        if not dry_run:
            user.user_permissions.clear()
        
        self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}✓ Reset {user.email}: removed {group_count} groups, {perm_count} permissions")
        
        # Re-assign based on profession if available
        if hasattr(user, 'profession_type') and user.profession_type:
            self._assign_profession_group(user, user.profession_type, dry_run)
    
    def sync_user_groups(self, options):
        """Sync user groups based on profession types."""
        self.stdout.write(self.style.SUCCESS('Syncing User Groups with Profession Types'))
        self.stdout.write('=' * 50)
        
        users = self._get_users(options)
        if not users:
            return
        
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        
        # Map numeric profession_type values to group names
        # Based on EqmdCustomUser model: MEDICAL_DOCTOR=0, RESIDENT=1, NURSE=2, PHYSIOTERAPIST=3, STUDENT=4
        profession_type_to_group = {
            0: 'Medical Doctors',      # MEDICAL_DOCTOR
            1: 'Residents',            # RESIDENT
            2: 'Nurses',               # NURSE  
            3: 'Physiotherapists',     # PHYSIOTERAPIST
            4: 'Students',             # STUDENT
        }
        
        with transaction.atomic():
            for user in users:
                if hasattr(user, 'profession_type') and user.profession_type is not None:
                    expected_group = profession_type_to_group.get(user.profession_type)
                    if expected_group:
                        current_groups = set(user.groups.values_list('name', flat=True))
                        
                        if expected_group not in current_groups:
                            self._assign_group(user, expected_group, dry_run)
                        else:
                            self.stdout.write(f"✓ {user.email} already in correct group '{expected_group}'")
                    else:
                        self.stdout.write(f"⚠ {user.email} has unknown profession type: {user.profession_type}")
                else:
                    self.stdout.write(f"⚠ {user.email} has no profession type set")
    
    def _get_users(self, options):
        """Get users based on options."""
        user_id = options.get('user_id')
        user_email = options.get('user_email')
        all_users = options.get('all_users', False)
        
        if all_users:
            users = User.objects.all()
            self.stdout.write(f"Processing {users.count()} users")
            return users
        elif user_id:
            try:
                return [User.objects.get(id=user_id)]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User with ID {user_id} does not exist"))
                return []
        elif user_email:
            try:
                return [User.objects.get(email=user_email)]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User with email {user_email} does not exist"))
                return []
        else:
            self.stdout.write(self.style.ERROR("Must specify --user-id, --user-email, or --all-users"))
            return []
