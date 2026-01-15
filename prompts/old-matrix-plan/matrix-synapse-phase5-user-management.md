# Phase 5: User Management Integration

## Overview
Implement comprehensive user lifecycle synchronization between EquipeMed and Matrix, including automatic user creation, profile updates, admin management, and deactivation handling.

## Prerequisites
- Phases 1-4 completed successfully
- Matrix Synapse and Element Web operational
- Django OIDC provider functional
- Admin access to both systems

## Step 1: Matrix User Management Commands

### 1.1 Create Matrix User Sync Management Command
Create `matrix_integration/management/commands/sync_matrix_users.py`:

```python
import asyncio
import aiohttp
import json
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from matrix_integration.models import MatrixUser, MatrixIntegration

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Synchronize EquipeMed users with Matrix server'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-missing',
            action='store_true',
            help='Create Matrix users for EquipeMed users without Matrix accounts',
        )
        parser.add_argument(
            '--update-profiles',
            action='store_true', 
            help='Update existing Matrix user profiles from EquipeMed data',
        )
        parser.add_argument(
            '--sync-admins',
            action='store_true',
            help='Sync admin status between EquipeMed and Matrix',
        )
        parser.add_argument(
            '--deactivate-disabled',
            action='store_true',
            help='Deactivate Matrix users for disabled EquipeMed users',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Sync specific user by username',
        )

    def handle(self, *args, **options):
        asyncio.run(self._async_handle(options))

    async def _async_handle(self, options):
        """Async handler for Matrix API operations."""
        
        # Get Matrix configuration
        try:
            matrix_config = MatrixIntegration.objects.first()
            if not matrix_config:
                self.stdout.write(self.style.ERROR('Matrix integration not configured'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading Matrix config: {e}'))
            return

        # Matrix API configuration
        homeserver_url = f"https://{matrix_config.matrix_server_name}"
        admin_token = self._get_admin_token()
        
        if not admin_token:
            self.stdout.write(self.style.ERROR('Matrix admin token not found in environment'))
            return

        # Determine users to process
        if options['user']:
            users = User.objects.filter(username=options['user'])
            if not users.exists():
                self.stdout.write(self.style.ERROR(f'User "{options["user"]}" not found'))
                return
        else:
            users = User.objects.all()

        async with aiohttp.ClientSession() as session:
            # Process each user
            for user in users:
                try:
                    await self._process_user(session, homeserver_url, admin_token, user, options)
                except Exception as e:
                    logger.error(f'Error processing user {user.username}: {e}')
                    self.stdout.write(
                        self.style.ERROR(f'Error processing user {user.username}: {e}')
                    )

        self.stdout.write(self.style.SUCCESS('User synchronization completed'))

    async def _process_user(self, session, homeserver_url, admin_token, user, options):
        """Process a single user for Matrix synchronization."""
        
        matrix_user_id = f"@{user.username}:matrix.yourhospital.com"
        
        # Get or create MatrixUser record
        matrix_user, created = MatrixUser.objects.get_or_create(
            user=user,
            defaults={
                'matrix_user_id': matrix_user_id,
                'matrix_localpart': user.username,
                'is_active': user.is_active
            }
        )
        
        if created:
            self.stdout.write(f'Created MatrixUser record for {user.username}')

        # Check if user should be processed
        should_create = options['create_missing'] and created
        should_update = options['update_profiles'] and not created
        should_sync_admin = options['sync_admins']
        should_deactivate = options['deactivate_disabled'] and not user.is_active
        
        if not (should_create or should_update or should_sync_admin or should_deactivate):
            return

        # Prepare user data for Matrix
        user_data = {
            'deactivated': not user.is_active,
            'admin': user.is_superuser,
            'displayname': user.get_full_name() or user.username,
            'user_type': None
        }
        
        # Add medical role information
        if hasattr(user, 'role'):
            user_data['external_ids'] = [
                {
                    'auth_provider': 'equipemed',
                    'external_id': str(user.pk),
                    'role': user.role
                }
            ]

        if options['dry_run']:
            action = 'CREATE' if created else 'UPDATE'
            self.stdout.write(f'[DRY RUN] {action} Matrix user: {matrix_user_id}')
            self.stdout.write(f'  Data: {json.dumps(user_data, indent=2)}')
            return

        # Make API request to Matrix
        await self._update_matrix_user(session, homeserver_url, admin_token, 
                                     matrix_user_id, user_data, matrix_user)

    async def _update_matrix_user(self, session, homeserver_url, admin_token, 
                                matrix_user_id, user_data, matrix_user):
        """Update user in Matrix via Admin API."""
        
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{homeserver_url}/_synapse/admin/v2/users/{matrix_user_id}"
        
        try:
            async with session.put(url, json=user_data, headers=headers) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    action = 'Created' if response.status == 201 else 'Updated'
                    self.stdout.write(
                        self.style.SUCCESS(f'{action} Matrix user: {matrix_user_id}')
                    )
                    
                    # Update MatrixUser record
                    with transaction.atomic():
                        matrix_user.is_active = not user_data['deactivated']
                        matrix_user.profile_synced_at = timezone.now()
                        if not user_data['deactivated']:
                            matrix_user.last_login_at = timezone.now()
                        matrix_user.save()
                        
                else:
                    error_text = await response.text()
                    self.stdout.write(
                        self.style.ERROR(f'Failed to update {matrix_user_id}: {error_text}')
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating Matrix user {matrix_user_id}: {e}')
            )

    def _get_admin_token(self):
        """Get Matrix admin token from environment or config."""
        import os
        return os.getenv('MATRIX_ADMIN_TOKEN')
```

### 1.2 Create Matrix Room Management Command
Create `matrix_integration/management/commands/manage_matrix_rooms.py`:

```python
import asyncio
import aiohttp
import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from matrix_integration.models import MatrixUser

User = get_user_model()

class Command(BaseCommand):
    help = 'Manage Matrix rooms for medical teams'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-bot-user',
            action='store_true',
            help='Create dedicated bot user for room management',
        )
        parser.add_argument(
            '--list-rooms',
            action='store_true',
            help='List all rooms on the Matrix server',
        )
        parser.add_argument(
            '--room-stats',
            action='store_true',
            help='Show room statistics',
        )
        parser.add_argument(
            '--cleanup-empty',
            action='store_true',
            help='Remove empty rooms (admin only)',
        )

    def handle(self, *args, **options):
        asyncio.run(self._async_handle(options))

    async def _async_handle(self, options):
        """Async handler for Matrix room operations."""
        
        homeserver_url = "https://matrix.yourhospital.com"
        admin_token = self._get_admin_token()
        
        if not admin_token:
            self.stdout.write(self.style.ERROR('Matrix admin token not found'))
            return

        async with aiohttp.ClientSession() as session:
            if options['create_bot_user']:
                await self._create_bot_user(session, homeserver_url, admin_token)
            
            if options['list_rooms']:
                await self._list_rooms(session, homeserver_url, admin_token)
                
            if options['room_stats']:
                await self._room_statistics(session, homeserver_url, admin_token)
                
            if options['cleanup_empty']:
                await self._cleanup_empty_rooms(session, homeserver_url, admin_token)

    async def _create_bot_user(self, session, homeserver_url, admin_token):
        """Create dedicated bot user for future automation."""
        
        bot_user_id = "@equipemed_bot:matrix.yourhospital.com"
        
        bot_data = {
            'admin': False,
            'deactivated': False,
            'displayname': 'EquipeMed Assistant Bot',
            'user_type': None,
            'external_ids': [
                {
                    'auth_provider': 'equipemed_system',
                    'external_id': 'bot_001',
                    'role': 'bot'
                }
            ]
        }
        
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{homeserver_url}/_synapse/admin/v2/users/{bot_user_id}"
        
        try:
            async with session.put(url, json=bot_data, headers=headers) as response:
                if response.status in [200, 201]:
                    self.stdout.write(
                        self.style.SUCCESS(f'Bot user created: {bot_user_id}')
                    )
                    
                    # Get access token for bot
                    await self._create_bot_access_token(session, homeserver_url, 
                                                      admin_token, bot_user_id)
                else:
                    error = await response.text()
                    self.stdout.write(
                        self.style.ERROR(f'Failed to create bot user: {error}')
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating bot user: {e}')
            )

    async def _create_bot_access_token(self, session, homeserver_url, admin_token, bot_user_id):
        """Create access token for bot user."""
        
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }
        
        token_data = {
            'user_id': bot_user_id,
            'device_id': 'EQUIPEMED_BOT_DEVICE'
        }
        
        url = f"{homeserver_url}/_synapse/admin/v1/users/{bot_user_id}/login"
        
        try:
            async with session.post(url, json=token_data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    access_token = result.get('access_token')
                    
                    self.stdout.write(
                        self.style.SUCCESS('Bot access token created')
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            f'IMPORTANT: Save this bot access token: {access_token}'
                        )
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            'Add MATRIX_BOT_TOKEN={} to your .env file'.format(access_token)
                        )
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating bot access token: {e}')
            )

    async def _list_rooms(self, session, homeserver_url, admin_token):
        """List all rooms on the Matrix server."""
        
        headers = {
            'Authorization': f'Bearer {admin_token}',
        }
        
        url = f"{homeserver_url}/_synapse/admin/v1/rooms"
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    rooms = result.get('rooms', [])
                    
                    self.stdout.write(f"Found {len(rooms)} rooms:")
                    for room in rooms:
                        self.stdout.write(
                            f"  {room['room_id']} - {room.get('name', 'Unnamed')} "
                            f"({room.get('joined_members', 0)} members)"
                        )
                        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error listing rooms: {e}')
            )

    async def _room_statistics(self, session, homeserver_url, admin_token):
        """Show room statistics."""
        
        headers = {
            'Authorization': f'Bearer {admin_token}',
        }
        
        # Get room count
        rooms_url = f"{homeserver_url}/_synapse/admin/v1/rooms"
        users_url = f"{homeserver_url}/_synapse/admin/v2/users"
        
        try:
            async with session.get(rooms_url, headers=headers) as response:
                if response.status == 200:
                    rooms_data = await response.json()
                    total_rooms = len(rooms_data.get('rooms', []))
                    
            async with session.get(users_url, headers=headers) as response:
                if response.status == 200:
                    users_data = await response.json()
                    total_users = len(users_data.get('users', []))
                    
            self.stdout.write("Matrix Server Statistics:")
            self.stdout.write(f"  Total Rooms: {total_rooms}")
            self.stdout.write(f"  Total Users: {total_users}")
            self.stdout.write(f"  Active Matrix Users: {MatrixUser.objects.filter(is_active=True).count()}")
            self.stdout.write(f"  EquipeMed Users: {User.objects.filter(is_active=True).count()}")
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error getting statistics: {e}')
            )

    def _get_admin_token(self):
        import os
        return os.getenv('MATRIX_ADMIN_TOKEN')
```

## Step 2: User Lifecycle Signal Handlers

### 2.1 Create Django Signal Handlers
Create `matrix_integration/signals.py`:

```python
from django.db.models.signals import post_save, post_delete, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import MatrixUser
from .tasks import sync_matrix_user_async, deactivate_matrix_user_async
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@receiver(post_save, sender=User)
def handle_user_created_or_updated(sender, instance, created, **kwargs):
    """Handle EquipeMed user creation or updates."""
    
    if created:
        # New user created - create Matrix user record
        logger.info(f'Creating Matrix user record for new user: {instance.username}')
        
        matrix_user, matrix_created = MatrixUser.objects.get_or_create(
            user=instance,
            defaults={
                'matrix_user_id': f'@{instance.username}:matrix.yourhospital.com',
                'matrix_localpart': instance.username,
                'is_active': instance.is_active
            }
        )
        
        if matrix_created:
            # Schedule async Matrix user creation
            sync_matrix_user_async.delay(instance.pk)
            
    else:
        # User updated - sync changes to Matrix
        logger.info(f'Syncing Matrix user updates for: {instance.username}')
        
        try:
            matrix_user = MatrixUser.objects.get(user=instance)
            
            # Check if activation status changed
            if matrix_user.is_active != instance.is_active:
                matrix_user.is_active = instance.is_active
                matrix_user.save()
                
                if instance.is_active:
                    # User reactivated
                    sync_matrix_user_async.delay(instance.pk)
                else:
                    # User deactivated
                    deactivate_matrix_user_async.delay(instance.pk)
            else:
                # Regular profile update
                sync_matrix_user_async.delay(instance.pk)
                
        except MatrixUser.DoesNotExist:
            # Matrix user doesn't exist, create it
            MatrixUser.objects.create(
                user=instance,
                matrix_user_id=f'@{instance.username}:matrix.yourhospital.com',
                matrix_localpart=instance.username,
                is_active=instance.is_active
            )
            sync_matrix_user_async.delay(instance.pk)

@receiver(user_logged_in)
def handle_user_login(sender, request, user, **kwargs):
    """Handle user login to update last login time."""
    
    try:
        matrix_user = MatrixUser.objects.get(user=user)
        matrix_user.last_login_at = timezone.now()
        matrix_user.save(update_fields=['last_login_at'])
        
    except MatrixUser.DoesNotExist:
        # Create Matrix user record if it doesn't exist
        MatrixUser.objects.create(
            user=user,
            matrix_user_id=f'@{user.username}:matrix.yourhospital.com',
            matrix_localpart=user.username,
            is_active=user.is_active,
            last_login_at=timezone.now()
        )
        sync_matrix_user_async.delay(user.pk)

@receiver(post_delete, sender=User)
def handle_user_deleted(sender, instance, **kwargs):
    """Handle EquipeMed user deletion."""
    
    logger.info(f'Handling deletion of user: {instance.username}')
    
    try:
        matrix_user = MatrixUser.objects.get(user=instance)
        # Deactivate Matrix user before deleting record
        deactivate_matrix_user_async.delay(instance.pk)
        matrix_user.delete()
        
    except MatrixUser.DoesNotExist:
        pass  # Matrix user didn't exist

# Prevent superuser changes without Matrix sync
@receiver(pre_save, sender=User)
def handle_superuser_change(sender, instance, **kwargs):
    """Track superuser status changes for admin sync."""
    
    if instance.pk:  # Existing user
        try:
            old_instance = User.objects.get(pk=instance.pk)
            if old_instance.is_superuser != instance.is_superuser:
                logger.info(f'Superuser status changed for {instance.username}: {instance.is_superuser}')
                # This will be handled by post_save signal
                
        except User.DoesNotExist:
            pass  # New user, will be handled by post_save
```

### 2.2 Create Async Task Functions
Create `matrix_integration/tasks.py`:

```python
from celery import shared_task
import asyncio
import aiohttp
import json
import logging
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import MatrixUser, MatrixIntegration

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task
def sync_matrix_user_async(user_id):
    """Async task to sync EquipeMed user with Matrix."""
    
    try:
        user = User.objects.get(pk=user_id)
        asyncio.run(_sync_matrix_user(user))
        
    except User.DoesNotExist:
        logger.error(f'User {user_id} not found for Matrix sync')
    except Exception as e:
        logger.error(f'Error syncing Matrix user {user_id}: {e}')

@shared_task 
def deactivate_matrix_user_async(user_id):
    """Async task to deactivate Matrix user."""
    
    try:
        user = User.objects.get(pk=user_id)
        asyncio.run(_deactivate_matrix_user(user))
        
    except User.DoesNotExist:
        logger.error(f'User {user_id} not found for Matrix deactivation')
    except Exception as e:
        logger.error(f'Error deactivating Matrix user {user_id}: {e}')

@shared_task
def bulk_sync_matrix_users():
    """Periodic task to sync all Matrix users."""
    
    logger.info('Starting bulk Matrix user sync')
    
    # Get users that need syncing (profile not synced recently)
    one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
    users_to_sync = User.objects.filter(
        is_active=True,
        matrix_profile__profile_synced_at__lt=one_hour_ago
    ).distinct()
    
    for user in users_to_sync:
        sync_matrix_user_async.delay(user.pk)
        
    logger.info(f'Queued {users_to_sync.count()} users for Matrix sync')

async def _sync_matrix_user(user):
    """Internal function to sync user with Matrix."""
    
    try:
        matrix_config = MatrixIntegration.objects.first()
        if not matrix_config:
            logger.error('Matrix integration not configured')
            return
            
        homeserver_url = f"https://{matrix_config.matrix_server_name}"
        admin_token = _get_admin_token()
        
        if not admin_token:
            logger.error('Matrix admin token not configured')
            return
            
        matrix_user_id = f"@{user.username}:matrix.yourhospital.com"
        
        user_data = {
            'deactivated': not user.is_active,
            'admin': user.is_superuser,
            'displayname': user.get_full_name() or user.username,
            'user_type': None
        }
        
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            url = f"{homeserver_url}/_synapse/admin/v2/users/{matrix_user_id}"
            
            async with session.put(url, json=user_data, headers=headers) as response:
                if response.status in [200, 201]:
                    logger.info(f'Synced Matrix user: {matrix_user_id}')
                    
                    # Update MatrixUser record
                    matrix_user, created = MatrixUser.objects.get_or_create(
                        user=user,
                        defaults={
                            'matrix_user_id': matrix_user_id,
                            'matrix_localpart': user.username,
                            'is_active': user.is_active
                        }
                    )
                    
                    matrix_user.is_active = user.is_active
                    matrix_user.profile_synced_at = timezone.now()
                    matrix_user.save()
                    
                else:
                    error = await response.text()
                    logger.error(f'Failed to sync Matrix user {matrix_user_id}: {error}')
                    
    except Exception as e:
        logger.error(f'Error in _sync_matrix_user for {user.username}: {e}')

async def _deactivate_matrix_user(user):
    """Internal function to deactivate Matrix user."""
    
    try:
        matrix_config = MatrixIntegration.objects.first()
        homeserver_url = f"https://{matrix_config.matrix_server_name}"
        admin_token = _get_admin_token()
        
        matrix_user_id = f"@{user.username}:matrix.yourhospital.com"
        
        user_data = {
            'deactivated': True,
            'admin': False
        }
        
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            url = f"{homeserver_url}/_synapse/admin/v2/users/{matrix_user_id}"
            
            async with session.put(url, json=user_data, headers=headers) as response:
                if response.status == 200:
                    logger.info(f'Deactivated Matrix user: {matrix_user_id}')
                    
                    # Update MatrixUser record
                    try:
                        matrix_user = MatrixUser.objects.get(user=user)
                        matrix_user.is_active = False
                        matrix_user.save()
                    except MatrixUser.DoesNotExist:
                        pass
                        
                else:
                    error = await response.text()
                    logger.error(f'Failed to deactivate Matrix user {matrix_user_id}: {error}')
                    
    except Exception as e:
        logger.error(f'Error in _deactivate_matrix_user for {user.username}: {e}')

def _get_admin_token():
    """Get Matrix admin token from environment."""
    import os
    return os.getenv('MATRIX_ADMIN_TOKEN')
```

## Step 3: Admin Interface Enhancements

### 3.1 Enhanced Admin Views
Update `matrix_integration/admin.py`:

```python
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import MatrixIntegration, MatrixUser
from .tasks import sync_matrix_user_async, bulk_sync_matrix_users

User = get_user_model()

@admin.register(MatrixIntegration)
class MatrixIntegrationAdmin(admin.ModelAdmin):
    list_display = ('matrix_server_name', 'matrix_client_id', 'auto_create_users', 
                    'sync_user_profiles', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'configuration_status')
    
    fieldsets = (
        ('Matrix Server', {
            'fields': ('matrix_server_name', 'matrix_client_id', 'matrix_client_secret')
        }),
        ('OIDC Endpoints', {
            'fields': ('oidc_issuer', 'oidc_authorization_endpoint', 'oidc_token_endpoint', 
                      'oidc_userinfo_endpoint', 'oidc_jwks_uri')
        }),
        ('Settings', {
            'fields': ('auto_create_users', 'sync_user_profiles')
        }),
        ('Status', {
            'fields': ('configuration_status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def configuration_status(self, obj):
        """Show configuration status with health checks."""
        # This will be a simple status for now
        # In production, you might want to add actual health checks
        return format_html(
            '<span style="color: green;">✓ Configured</span>'
        )
    configuration_status.short_description = 'Configuration Status'

@admin.register(MatrixUser)
class MatrixUserAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'matrix_localpart', 'is_active', 'last_login_at', 
                    'profile_synced_at', 'sync_status')
    list_filter = ('is_active', 'created_at', 'last_login_at', 'user__is_superuser')
    search_fields = ('user__username', 'user__email', 'user__first_name', 
                     'user__last_name', 'matrix_localpart')
    readonly_fields = ('matrix_user_id', 'created_at', 'updated_at', 
                       'profile_synced_at', 'sync_status')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'matrix_user_id', 'matrix_localpart')
        }),
        ('Status', {
            'fields': ('is_active', 'last_login_at', 'sync_status')
        }),
        ('Sync Information', {
            'fields': ('profile_synced_at',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['sync_selected_users', 'create_missing_matrix_users', 
               'deactivate_matrix_users']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-sync/', self.bulk_sync_view, name='matrix_user_bulk_sync'),
        ]
        return custom_urls + urls
    
    def user_link(self, obj):
        """Create link to user admin page."""
        url = reverse('admin:accounts_eqmdcustomuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'EquipeMed User'
    
    def sync_status(self, obj):
        """Show sync status with visual indicators."""
        if not obj.profile_synced_at:
            return format_html('<span style="color: orange;">⚠ Never synced</span>')
        
        from django.utils import timezone
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        
        if obj.profile_synced_at < one_hour_ago:
            return format_html('<span style="color: red;">⚠ Sync outdated</span>')
        else:
            return format_html('<span style="color: green;">✓ Recently synced</span>')
    sync_status.short_description = 'Sync Status'
    
    def sync_selected_users(self, request, queryset):
        """Sync selected Matrix users."""
        count = 0
        for matrix_user in queryset:
            sync_matrix_user_async.delay(matrix_user.user.pk)
            count += 1
            
        self.message_user(
            request, 
            f'Queued {count} users for Matrix synchronization.',
            messages.SUCCESS
        )
    sync_selected_users.short_description = "Sync selected users with Matrix"
    
    def create_missing_matrix_users(self, request, queryset):
        """Create Matrix users for EquipeMed users without Matrix accounts."""
        # Get EquipeMed users without MatrixUser records
        existing_user_ids = MatrixUser.objects.values_list('user_id', flat=True)
        missing_users = User.objects.filter(is_active=True).exclude(id__in=existing_user_ids)
        
        count = 0
        for user in missing_users:
            MatrixUser.objects.create(
                user=user,
                matrix_user_id=f'@{user.username}:matrix.yourhospital.com',
                matrix_localpart=user.username,
                is_active=user.is_active
            )
            sync_matrix_user_async.delay(user.pk)
            count += 1
            
        self.message_user(
            request,
            f'Created and queued {count} missing Matrix users for synchronization.',
            messages.SUCCESS
        )
    create_missing_matrix_users.short_description = "Create missing Matrix users"
    
    def deactivate_matrix_users(self, request, queryset):
        """Deactivate selected Matrix users."""
        count = queryset.update(is_active=False)
        for matrix_user in queryset:
            deactivate_matrix_user_async.delay(matrix_user.user.pk)
            
        self.message_user(
            request,
            f'Deactivated {count} Matrix users.',
            messages.WARNING
        )
    deactivate_matrix_users.short_description = "Deactivate selected Matrix users"
    
    def bulk_sync_view(self, request):
        """Trigger bulk sync of all Matrix users."""
        bulk_sync_matrix_users.delay()
        
        self.message_user(
            request,
            'Bulk Matrix user synchronization started. This may take a few minutes.',
            messages.INFO
        )
        
        return HttpResponseRedirect(reverse('admin:matrix_integration_matrixuser_changelist'))
```

### 3.2 Add Matrix Management to User Admin
Update your existing user admin to include Matrix integration:

```python
# Add to your existing user admin (accounts/admin.py or wherever your user admin is)
from matrix_integration.models import MatrixUser

class MatrixUserInline(admin.StackedInline):
    model = MatrixUser
    extra = 0
    readonly_fields = ('matrix_user_id', 'created_at', 'updated_at', 'profile_synced_at')
    fields = ('matrix_user_id', 'matrix_localpart', 'is_active', 
              'last_login_at', 'profile_synced_at')

# Add to your existing UserAdmin class
class YourUserAdmin(admin.ModelAdmin):
    # ... existing configuration ...
    inlines = [MatrixUserInline]  # Add this line
```

## Step 4: Environment Configuration

### 4.1 Update Environment Variables
Add to `.env`:

```bash
# Matrix Admin Configuration
MATRIX_ADMIN_TOKEN=your_matrix_admin_token_here_very_secure
MATRIX_BOT_TOKEN=your_matrix_bot_token_will_be_generated

# Celery Configuration (if not already configured)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Matrix Sync Settings
MATRIX_SYNC_INTERVAL_MINUTES=60
MATRIX_BULK_SYNC_ENABLED=true
```

### 4.2 Update Django Settings
Add to `config/settings.py`:

```python
# ================================================================================
# MATRIX USER MANAGEMENT CONFIGURATION
# ================================================================================

# Matrix admin token (keep secure!)
MATRIX_ADMIN_TOKEN = os.getenv('MATRIX_ADMIN_TOKEN')
MATRIX_BOT_TOKEN = os.getenv('MATRIX_BOT_TOKEN')

# Matrix sync settings
MATRIX_SYNC_INTERVAL = int(os.getenv('MATRIX_SYNC_INTERVAL_MINUTES', '60'))
MATRIX_BULK_SYNC_ENABLED = os.getenv('MATRIX_BULK_SYNC_ENABLED', 'true').lower() == 'true'

# Celery configuration for async tasks
if 'CELERY_BROKER_URL' in os.environ:
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = TIME_ZONE
```

## Step 5: Initialize Apps Configuration

### 5.1 Update Apps Configuration
Add to `matrix_integration/apps.py`:

```python
from django.apps import AppConfig

class MatrixIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'matrix_integration'
    verbose_name = 'Matrix Integration'
    
    def ready(self):
        # Import signal handlers
        import matrix_integration.signals
```

### 5.2 Create Initial Data Migration
Create `matrix_integration/migrations/0002_initial_data.py`:

```python
from django.db import migrations
from django.conf import settings
import os

def create_initial_matrix_config(apps, schema_editor):
    """Create initial Matrix integration configuration."""
    MatrixIntegration = apps.get_model('matrix_integration', 'MatrixIntegration')
    
    # Get the first allowed host for OIDC issuer
    allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', ['localhost'])
    primary_host = allowed_hosts[0] if allowed_hosts else 'localhost'
    
    MatrixIntegration.objects.get_or_create(
        matrix_server_name="matrix.yourhospital.com",
        defaults={
            'matrix_client_id': os.getenv('OIDC_MATRIX_CLIENT_ID', 'matrix_synapse_client'),
            'matrix_client_secret': os.getenv('OIDC_MATRIX_CLIENT_SECRET', 'changeme'),
            'oidc_issuer': f"https://{primary_host}",
            'oidc_authorization_endpoint': f"https://{primary_host}/oauth2/authorize/",
            'oidc_token_endpoint': f"https://{primary_host}/oauth2/token/",
            'oidc_userinfo_endpoint': f"https://{primary_host}/oauth2/userinfo/",
            'oidc_jwks_uri': f"https://{primary_host}/.well-known/jwks.json",
            'auto_create_users': True,
            'sync_user_profiles': True,
        }
    )

def reverse_initial_matrix_config(apps, schema_editor):
    """Remove initial Matrix configuration."""
    MatrixIntegration = apps.get_model('matrix_integration', 'MatrixIntegration')
    MatrixIntegration.objects.filter(matrix_server_name="matrix.yourhospital.com").delete()

class Migration(migrations.Migration):
    dependencies = [
        ('matrix_integration', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_initial_matrix_config, reverse_initial_matrix_config),
    ]
```

## Verification Commands

### Test User Sync
```bash
# Create Matrix users for all EquipeMed users
uv run python manage.py sync_matrix_users --create-missing --dry-run

# Actually create missing users
uv run python manage.py sync_matrix_users --create-missing

# Sync admin users
uv run python manage.py sync_matrix_users --sync-admins

# Test specific user
uv run python manage.py sync_matrix_users --user username --update-profiles
```

### Test Room Management
```bash
# Create bot user
uv run python manage.py manage_matrix_rooms --create-bot-user

# List all rooms
uv run python manage.py manage_matrix_rooms --list-rooms

# Show statistics
uv run python manage.py manage_matrix_rooms --room-stats
```

### Test Signal Handlers
```bash
# Test in Django shell
uv run python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()

# Create test user (should trigger Matrix user creation)
user = User.objects.create_user('test_matrix', 'test@example.com', 'password')
print(f'Created user: {user.username}')

# Update user (should trigger Matrix sync)
user.first_name = 'Test'
user.save()
print('Updated user profile')

# Check Matrix user record
from matrix_integration.models import MatrixUser
matrix_user = MatrixUser.objects.get(user=user)
print(f'Matrix user: {matrix_user.matrix_user_id}')
"
```

## File Structure Check

After Phase 5, you should have:
```
├── matrix_integration/
│   ├── models.py               # Updated with enhanced models
│   ├── admin.py                # Enhanced admin interface
│   ├── signals.py              # User lifecycle signal handlers
│   ├── tasks.py                # Async task functions
│   ├── apps.py                 # App configuration with signal imports
│   ├── management/commands/
│   │   ├── sync_matrix_users.py    # User sync command
│   │   ├── manage_matrix_rooms.py  # Room management command
│   │   └── setup_matrix_oidc.py    # OIDC setup command
│   └── migrations/
│       ├── 0001_initial.py         # Initial models
│       └── 0002_initial_data.py    # Initial configuration
├── config/settings.py          # Updated with Matrix and Celery config
└── .env                        # Updated with Matrix admin tokens
```

## Next Steps

1. ✅ **Complete Phase 5** user management integration
2. ➡️ **Proceed to Phase 6** for testing and deployment
3. 🔄 **Test user lifecycle** - create, update, deactivate users
4. 🤖 **Verify bot user creation** for future automation

## Troubleshooting

### Common Issues
- **Signals not firing**: Ensure `matrix_integration.signals` is imported in `apps.py`
- **Celery tasks failing**: Verify Redis is running and CELERY_BROKER_URL is correct
- **Admin token issues**: Check MATRIX_ADMIN_TOKEN is set correctly

### Debug Commands
```bash
# Check signal handlers are loaded
uv run python manage.py shell -c "
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
print('Registered post_save signals for User:', post_save.disconnect_all)
"

# Test Matrix API connectivity
uv run python manage.py shell -c "
import asyncio
from matrix_integration.tasks import _sync_matrix_user
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.first()
if user:
    asyncio.run(_sync_matrix_user(user))
"

# Check MatrixUser records
uv run python manage.py shell -c "
from matrix_integration.models import MatrixUser
print(f'Total MatrixUser records: {MatrixUser.objects.count()}')
print(f'Active Matrix users: {MatrixUser.objects.filter(is_active=True).count()}')
"
```

---

**Status**: User management integration complete with automatic sync, admin interface, and lifecycle handling