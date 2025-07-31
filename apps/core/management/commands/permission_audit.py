"""
Management command for auditing the permission system.

This command provides tools for auditing permissions, checking consistency,
and fixing permission issues.
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

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
            choices=['list', 'check', 'fix', 'report', 'verify_medical_roles'],
            default='report',
            help='Action to perform'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Output file for JSON report (optional)'
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
            self.generate_report(options.get('user_id'), options.get('output'))
        elif action == 'verify_medical_roles':
            self.verify_medical_roles_security()
    
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
            0: 'Medical Doctors',  # MEDICAL_DOCTOR
            1: 'Residents',        # RESIDENT
            2: 'Nurses',           # NURSE
            3: 'Physiotherapists', # PHYSIOTERAPIST (note: typo in model)
            4: 'Students',         # STUDENT
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
            0: 'Medical Doctors',  # MEDICAL_DOCTOR
            1: 'Residents',        # RESIDENT
            2: 'Nurses',           # NURSE
            3: 'Physiotherapists', # PHYSIOTERAPIST (note: typo in model)
            4: 'Students',         # STUDENT
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
    
    def verify_medical_roles_security(self):
        """Verify medical roles have no administrative permissions."""
        self.stdout.write(self.style.SUCCESS('Permission System Audit - Medical Roles Security Verification'))
        self.stdout.write('=' * 60)
        
        medical_groups = ['Medical Doctors', 'Residents', 'Nurses', 'Physiotherapists', 'Students']
        issues_found = False
        
        for group_name in medical_groups:
            try:
                group = Group.objects.get(name=group_name)
                admin_perms = self._identify_admin_permissions(group.permissions.all())
                
                if admin_perms:
                    issues_found = True
                    self.stdout.write(
                        self.style.ERROR(f'❌ {group_name} has admin permissions:')
                    )
                    for perm in admin_perms:
                        self.stdout.write(f'   - {perm}')
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ {group_name} has no admin permissions')
                    )
                    
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Group "{group_name}" does not exist')
                )
        
        if issues_found:
            self.stdout.write(self.style.ERROR('\n🚨 SECURITY VERIFICATION FAILED'))
            self.stdout.write('Medical roles still have administrative permissions.')
            return False
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ SECURITY VERIFICATION PASSED'))
            self.stdout.write('Medical roles have no administrative permissions.')
            return True

    def _identify_admin_permissions(self, permissions_queryset):
        """Identify administrative permissions that medical staff shouldn't have."""
        admin_permission_patterns = [
            # User and group management
            ('auth', 'user'),
            ('auth', 'group'), 
            ('auth', 'permission'),
            
            # User account management
            ('accounts', None),  # Any accounts app permission
            
            # Django admin
            ('admin', None),
            
            # Content types (system level)
            ('contenttypes', None),
            
            # Sessions management
            ('sessions', None),
            
            # Sites framework
            ('sites', None),
            
            # Administrative tag templates
            ('patients', 'allowedtag'),
        ]
        
        admin_perms = []
        
        for perm in permissions_queryset.select_related('content_type'):
            app_label = perm.content_type.app_label
            model = perm.content_type.model
            
            for pattern_app, pattern_model in admin_permission_patterns:
                if app_label == pattern_app:
                    if pattern_model is None or model == pattern_model:
                        admin_perms.append(f'{app_label}.{perm.codename}')
                        break
        
        return admin_perms
    
    def generate_report(self, user_id=None, output_file=None):
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
        professions = [
            (0, 'Medical Doctor'),
            (1, 'Resident'), 
            (2, 'Nurse'),
            (3, 'Physiotherapist'),
            (4, 'Student')
        ]
        for profession_id, profession_name in professions:
            count = User.objects.filter(profession_type=profession_id).count()
            self.stdout.write(f"  {profession_name}: {count} users")
        
        # Users without profession
        no_profession = User.objects.filter(profession_type__isnull=True).count()
        if no_profession > 0:
            self.stdout.write(f"  No Profession Set: {no_profession} users")
        
        # Permission consistency check
        self.stdout.write(f"\nPermission Consistency:")
        self.check_consistency(fix_issues=False)
        
        # Security analysis for medical roles
        self.stdout.write(f"\nSecurity Analysis:")
        self.verify_medical_roles_security()
        
        # Generate JSON report if output file specified
        if output_file:
            self._generate_json_report(output_file)
        
        if user_id:
            self.stdout.write(f"\nDetailed User Report:")
            self._list_user_permissions(user_id)

    def _generate_json_report(self, output_file):
        """Generate JSON report for detailed analysis."""
        report = {
            'audit_timestamp': timezone.now().isoformat(),
            'groups': {},
            'admin_permissions_by_group': {},
            'security_issues': []
        }
        
        # Analyze each group
        for group in Group.objects.all():
            group_perms = list(group.permissions.values_list('codename', 'content_type__app_label', 'content_type__model'))
            report['groups'][group.name] = {
                'permission_count': len(group_perms),
                'permissions': [f'{app}.{codename}' for codename, app, model in group_perms],
                'user_count': group.user_set.count()
            }
            
            # Check for admin permissions
            admin_perms = self._identify_admin_permissions(group.permissions.all())
            if admin_perms:
                report['admin_permissions_by_group'][group.name] = admin_perms
                
                # Flag security issues for medical roles
                if group.name in ['Medical Doctors', 'Residents', 'Nurses', 'Physiotherapists', 'Students']:
                    report['security_issues'].append({
                        'type': 'medical_role_has_admin_permissions',
                        'group': group.name,
                        'admin_permissions': admin_perms,
                        'severity': 'HIGH',
                        'description': f'Medical role "{group.name}" has administrative permissions'
                    })
        
        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.stdout.write(f'JSON report saved to: {output_file}')
        
        # Summary
        self.stdout.write(f'Groups with admin permissions: {len(report["admin_permissions_by_group"])}')
        self.stdout.write(f'Security issues found: {len(report["security_issues"])}')
        
        if report['security_issues']:
            self.stdout.write(self.style.ERROR('⚠️  SECURITY ISSUES DETECTED'))
            for issue in report['security_issues']:
                self.stdout.write(self.style.ERROR(f'- {issue["description"]}'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ No security issues detected'))
