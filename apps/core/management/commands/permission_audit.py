"""
Management command for auditing the permission system.

This command provides tools for auditing permissions, checking consistency,
and fixing permission issues.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
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
    help = 'Audit permission system and check for consistency issues'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['list', 'check', 'fix', 'report'],
            default='report',
            help='Action to perform'
        )
        
        parser.add_argument(
            '--user-id',
            type=int,
            help='Specific user ID to audit (optional)'
        )
        
        parser.add_argument(
            '--group-name',
            type=str,
            help='Specific group name to audit (optional)'
        )
        
        parser.add_argument(
            '--fix-issues',
            action='store_true',
            help='Automatically fix detected issues'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'list':
            self.list_permissions(options.get('user_id'), options.get('group_name'))
        elif action == 'check':
            self.check_consistency(options.get('fix_issues'))
        elif action == 'fix':
            self.fix_permission_issues()
        elif action == 'report':
            self.generate_report(options.get('user_id'))
    
    def list_permissions(self, user_id=None, group_name=None):
        """List all permissions in the system."""
        self.stdout.write(self.style.SUCCESS('Permission System Audit - List Permissions'))
        self.stdout.write('=' * 60)
        
        if user_id:
            self._list_user_permissions(user_id)
        elif group_name:
            self._list_group_permissions(group_name)
        else:
            self._list_all_permissions()
    
    def _list_user_permissions(self, user_id):
        """List permissions for a specific user."""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError(f'User with ID {user_id} does not exist')
        
        self.stdout.write(f"\nUser: {user.email}")
        self.stdout.write(f"Profession: {getattr(user, 'profession_type', 'Not set')}")
        self.stdout.write(f"Active: {user.is_active}")
        self.stdout.write(f"Staff: {user.is_staff}")
        self.stdout.write(f"Superuser: {user.is_superuser}")
        
        # List groups
        groups = user.groups.all()
        self.stdout.write(f"\nGroups ({groups.count()}):")
        for group in groups:
            self.stdout.write(f"  - {group.name}")
        
        # List direct permissions
        user_perms = user.user_permissions.all()
        self.stdout.write(f"\nDirect Permissions ({user_perms.count()}):")
        for perm in user_perms:
            self.stdout.write(f"  - {perm.content_type.app_label}.{perm.codename}")
        
        # List all effective permissions
        all_perms = user.get_all_permissions()
        self.stdout.write(f"\nAll Effective Permissions ({len(all_perms)}):")
        for perm in sorted(all_perms):
            self.stdout.write(f"  - {perm}")
    
    def _list_group_permissions(self, group_name):
        """List permissions for a specific group."""
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            raise CommandError(f'Group "{group_name}" does not exist')
        
        self.stdout.write(f"\nGroup: {group.name}")
        
        # List group permissions
        group_perms = group.permissions.all()
        self.stdout.write(f"\nGroup Permissions ({group_perms.count()}):")
        for perm in group_perms:
            self.stdout.write(f"  - {perm.content_type.app_label}.{perm.codename}")
        
        # List users in group
        users = group.user_set.all()
        self.stdout.write(f"\nUsers in Group ({users.count()}):")
        for user in users:
            profession = getattr(user, 'profession_type', 'Not set')
            self.stdout.write(f"  - {user.email} ({profession})")
    
    def _list_all_permissions(self):
        """List all permissions in the system."""
        # List all groups
        groups = Group.objects.all()
        self.stdout.write(f"\nAll Groups ({groups.count()}):")
        for group in groups:
            perm_count = group.permissions.count()
            user_count = group.user_set.count()
            self.stdout.write(f"  - {group.name}: {perm_count} permissions, {user_count} users")
        
        # List all permissions by app
        self.stdout.write(f"\nPermissions by App:")
        apps = ContentType.objects.values_list('app_label', flat=True).distinct()
        for app in sorted(apps):
            perms = Permission.objects.filter(content_type__app_label=app)
            self.stdout.write(f"  - {app}: {perms.count()} permissions")
    
    def check_consistency(self, fix_issues=False):
        """Check permission system consistency."""
        self.stdout.write(self.style.SUCCESS('Permission System Audit - Consistency Check'))
        self.stdout.write('=' * 60)
        
        issues = []
        
        # Check for users without groups
        users_without_groups = User.objects.filter(groups__isnull=True, is_active=True)
        if users_without_groups.exists():
            issue = f"Found {users_without_groups.count()} active users without groups"
            issues.append(('users_without_groups', issue, users_without_groups))
            self.stdout.write(self.style.WARNING(f"⚠ {issue}"))
        
        # Check for users with incorrect group assignments
        incorrect_assignments = self._check_group_assignments()
        if incorrect_assignments:
            issue = f"Found {len(incorrect_assignments)} users with incorrect group assignments"
            issues.append(('incorrect_assignments', issue, incorrect_assignments))
            self.stdout.write(self.style.WARNING(f"⚠ {issue}"))
        
        # Check for missing profession-based groups
        missing_groups = self._check_missing_groups()
        if missing_groups:
            issue = f"Found {len(missing_groups)} missing profession-based groups"
            issues.append(('missing_groups', issue, missing_groups))
            self.stdout.write(self.style.WARNING(f"⚠ {issue}"))
        
        # Check for orphaned permissions
        orphaned_perms = self._check_orphaned_permissions()
        if orphaned_perms:
            issue = f"Found {len(orphaned_perms)} orphaned permissions"
            issues.append(('orphaned_permissions', issue, orphaned_perms))
            self.stdout.write(self.style.WARNING(f"⚠ {issue}"))
        
        if not issues:
            self.stdout.write(self.style.SUCCESS("✓ No consistency issues found"))
        else:
            self.stdout.write(f"\nFound {len(issues)} issue(s)")
            
            if fix_issues:
                self.stdout.write("\nAttempting to fix issues...")
                self._fix_issues(issues)
    
    def _check_group_assignments(self):
        """Check for users with incorrect group assignments."""
        incorrect = []
        
        profession_to_group = {
            'medical_doctor': 'Medical Doctors',
            'resident': 'Residents',
            'nurse': 'Nurses',
            'physiotherapist': 'Physiotherapists',
            'student': 'Students',
        }
        
        for user in User.objects.filter(is_active=True):
            profession = getattr(user, 'profession_type', None)
            if profession and profession in profession_to_group:
                expected_group = profession_to_group[profession]
                user_groups = list(user.groups.values_list('name', flat=True))
                
                if expected_group not in user_groups:
                    incorrect.append({
                        'user': user,
                        'profession': profession,
                        'expected_group': expected_group,
                        'current_groups': user_groups
                    })
        
        return incorrect
    
    def _check_missing_groups(self):
        """Check for missing profession-based groups."""
        expected_groups = [
            'Medical Doctors',
            'Residents',
            'Nurses',
            'Physiotherapists',
            'Students',
        ]
        
        existing_groups = set(Group.objects.values_list('name', flat=True))
        missing = [group for group in expected_groups if group not in existing_groups]
        
        return missing
    
    def _check_orphaned_permissions(self):
        """Check for permissions not assigned to any group or user."""
        # Get all permissions
        all_permissions = set(Permission.objects.values_list('id', flat=True))
        
        # Get permissions assigned to groups
        group_permissions = set(
            Permission.objects.filter(group__isnull=False).values_list('id', flat=True)
        )
        
        # Get permissions assigned directly to users
        user_permissions = set(
            Permission.objects.filter(user__isnull=False).values_list('id', flat=True)
        )
        
        # Find orphaned permissions
        assigned_permissions = group_permissions | user_permissions
        orphaned = all_permissions - assigned_permissions
        
        return list(Permission.objects.filter(id__in=orphaned))
    
    def _fix_issues(self, issues):
        """Fix detected issues."""
        with transaction.atomic():
            for issue_type, description, data in issues:
                if issue_type == 'users_without_groups':
                    self._fix_users_without_groups(data)
                elif issue_type == 'incorrect_assignments':
                    self._fix_incorrect_assignments(data)
                elif issue_type == 'missing_groups':
                    self._fix_missing_groups(data)
                # Note: We don't auto-fix orphaned permissions as they might be intentional
        
        self.stdout.write(self.style.SUCCESS("✓ Issues fixed"))
    
    def _fix_users_without_groups(self, users):
        """Fix users without groups by assigning them based on profession."""
        profession_to_group = {
            'medical_doctor': 'Medical Doctors',
            'resident': 'Residents',
            'nurse': 'Nurses',
            'physiotherapist': 'Physiotherapists',
            'student': 'Students',
        }
        
        for user in users:
            profession = getattr(user, 'profession_type', None)
            if profession and profession in profession_to_group:
                group_name = profession_to_group[profession]
                try:
                    group = Group.objects.get(name=group_name)
                    user.groups.add(group)
                    self.stdout.write(f"  ✓ Added {user.email} to {group_name}")
                except Group.DoesNotExist:
                    self.stdout.write(f"  ✗ Group {group_name} does not exist for {user.email}")
    
    def _fix_incorrect_assignments(self, incorrect_assignments):
        """Fix incorrect group assignments."""
        for assignment in incorrect_assignments:
            user = assignment['user']
            expected_group = assignment['expected_group']
            
            try:
                group = Group.objects.get(name=expected_group)
                user.groups.add(group)
                self.stdout.write(f"  ✓ Added {user.email} to {expected_group}")
            except Group.DoesNotExist:
                self.stdout.write(f"  ✗ Group {expected_group} does not exist")
    
    def _fix_missing_groups(self, missing_groups):
        """Fix missing groups by creating them."""
        for group_name in missing_groups:
            Group.objects.create(name=group_name)
            self.stdout.write(f"  ✓ Created group {group_name}")
    
    def fix_permission_issues(self):
        """Fix all detected permission issues."""
        self.stdout.write(self.style.SUCCESS('Permission System Audit - Fix Issues'))
        self.stdout.write('=' * 60)
        
        self.check_consistency(fix_issues=True)
    
    def generate_report(self, user_id=None):
        """Generate a comprehensive permission report."""
        self.stdout.write(self.style.SUCCESS('Permission System Audit - Comprehensive Report'))
        self.stdout.write('=' * 60)
        
        # System overview
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_groups = Group.objects.count()
        total_permissions = Permission.objects.count()
        
        self.stdout.write(f"\nSystem Overview:")
        self.stdout.write(f"  Total Users: {total_users}")
        self.stdout.write(f"  Active Users: {active_users}")
        self.stdout.write(f"  Total Groups: {total_groups}")
        self.stdout.write(f"  Total Permissions: {total_permissions}")
        
        # Group statistics
        self.stdout.write(f"\nGroup Statistics:")
        for group in Group.objects.all():
            user_count = group.user_set.count()
            perm_count = group.permissions.count()
            self.stdout.write(f"  {group.name}: {user_count} users, {perm_count} permissions")
        
        # Profession distribution
        self.stdout.write(f"\nProfession Distribution:")
        professions = ['medical_doctor', 'resident', 'nurse', 'physiotherapist', 'student']
        for profession in professions:
            count = User.objects.filter(profession_type=profession).count()
            self.stdout.write(f"  {profession.replace('_', ' ').title()}: {count} users")
        
        # Users without profession
        no_profession = User.objects.filter(profession_type__isnull=True).count()
        if no_profession > 0:
            self.stdout.write(f"  No Profession Set: {no_profession} users")
        
        # Permission consistency check
        self.stdout.write(f"\nPermission Consistency:")
        self.check_consistency(fix_issues=False)
        
        if user_id:
            self.stdout.write(f"\nDetailed User Report:")
            self._list_user_permissions(user_id)
