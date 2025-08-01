# Phase 3: IP Address Logging Implementation Plan

## Executive Summary

**Objective**: Implement comprehensive IP address logging for all critical operations to enable forensic analysis and detect suspicious access patterns.

**Timeline**: 1 day  
**Priority**: HIGH (Security forensics)  
**Risk Level**: LOW (Non-breaking addition)

## Problem Statement

Current system lacks:
- **IP address tracking** for database modifications
- **Geographic location** awareness for access attempts
- **Forensic capabilities** to trace malicious activity
- **Session correlation** for security investigations

Based on your experience with database poisoning, IP logging provides:
- **Attribution of malicious actions** to source locations
- **Detection of unusual access patterns** (geographic anomalies)
- **Correlation of attacks** across multiple accounts
- **Evidence for incident response**

## Solution: Comprehensive IP Logging

Integrate IP address capture with:
- Django Simple History (Phase 1)
- Soft delete operations (Phase 2)
- Critical user actions
- Authentication events

## Implementation Plan

### Step 1: IP Address Capture Infrastructure

#### 1.1: IP Utilities Module

```python
# apps/core/utils/ip_utils.py
import ipaddress
import requests
from django.core.cache import cache
from django.conf import settings
from django.http import HttpRequest

def get_client_ip(request: HttpRequest) -> str:
    """
    Get the real client IP address from request.
    Handles proxy headers and load balancers.
    """
    # Check for forwarded headers (load balancers, proxies)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP (original client)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        # Direct connection
        ip = request.META.get('REMOTE_ADDR', '')
    
    # Validate IP format
    try:
        ipaddress.ip_address(ip)
        return ip
    except ValueError:
        return '0.0.0.0'  # Fallback for invalid IPs

def get_user_agent(request: HttpRequest) -> str:
    """Get user agent string from request."""
    return request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit length

def get_ip_location(ip_address: str) -> dict:
    """
    Get geographic location for IP address.
    Uses ipapi.co API with caching.
    """
    if not ip_address or ip_address == '0.0.0.0':
        return {'country': 'Unknown', 'city': 'Unknown', 'region': 'Unknown'}
    
    # Check if private IP
    try:
        ip_obj = ipaddress.ip_address(ip_address)
        if ip_obj.is_private:
            return {'country': 'Private Network', 'city': 'Local', 'region': 'LAN'}
    except ValueError:
        return {'country': 'Invalid', 'city': 'Invalid', 'region': 'Invalid'}
    
    # Check cache first
    cache_key = f'ip_location_{ip_address}'
    location = cache.get(cache_key)
    if location:
        return location
    
    try:
        # Free IP geolocation API (1000 requests/month)
        response = requests.get(
            f'https://ipapi.co/{ip_address}/json/',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            location = {
                'country': data.get('country_name', 'Unknown'),
                'city': data.get('city', 'Unknown'),
                'region': data.get('region', 'Unknown'),
                'timezone': data.get('timezone', 'Unknown'),
            }
        else:
            location = {'country': 'API Error', 'city': 'Unknown', 'region': 'Unknown'}
    
    except requests.RequestException:
        location = {'country': 'Lookup Failed', 'city': 'Unknown', 'region': 'Unknown'}
    
    # Cache for 24 hours
    cache.set(cache_key, location, 86400)
    return location

def is_suspicious_ip(ip_address: str, user=None) -> tuple[bool, str]:
    """
    Check if IP address shows suspicious patterns.
    Returns (is_suspicious, reason)
    """
    if not ip_address or ip_address == '0.0.0.0':
        return False, ''
    
    # Check for known suspicious patterns
    suspicious_reasons = []
    
    # Check if user has accessed from multiple countries recently
    if user:
        from apps.core.models import UserSession
        recent_sessions = UserSession.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).values_list('ip_address', flat=True).distinct()
        
        if len(recent_sessions) > 1:
            countries = set()
            for session_ip in recent_sessions:
                location = get_ip_location(session_ip)
                countries.add(location['country'])
            
            if len(countries) > 2:  # More than 2 countries in a week
                suspicious_reasons.append(f'Multiple countries: {", ".join(countries)}')
    
    # TODO: Add more sophisticated checks
    # - Known malicious IP lists
    # - Unusual access hours
    # - High frequency from same IP
    
    return len(suspicious_reasons) > 0, '; '.join(suspicious_reasons)
```

#### 1.2: Session Tracking Model

```python
# apps/core/models/session_tracking.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from simple_history.models import HistoricalRecords

User = get_user_model()

class UserSession(models.Model):
    """Track user sessions with IP and location data."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tracked_sessions')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    # Geographic data
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=50, blank=True)
    
    # Session data
    session_key = models.CharField(max_length=40, blank=True)
    is_suspicious = models.BooleanField(default=False)
    suspicious_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    # History tracking
    history = HistoricalRecords()
    
    class Meta:
        db_table = 'core_user_session'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['is_suspicious']),
        ]
    
    def __str__(self):
        return f"{self.user.username} from {self.ip_address} ({self.country})"

class UserAction(models.Model):
    """Log critical user actions with IP and context."""
    
    ACTION_TYPES = [
        ('patient_create', 'Patient Created'),
        ('patient_update', 'Patient Updated'),
        ('patient_delete', 'Patient Deleted'),
        ('patient_restore', 'Patient Restored'),
        ('event_create', 'Event Created'),
        ('event_update', 'Event Updated'),
        ('event_delete', 'Event Delete'),
        ('user_login', 'User Login'),
        ('user_logout', 'User Logout'),
        ('password_change', 'Password Changed'),
        ('permission_change', 'Permission Changed'),
        ('bulk_operation', 'Bulk Operation'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logged_actions')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    
    # Target information
    target_model = models.CharField(max_length=50, blank=True)  # 'Patient', 'Event', etc.
    target_id = models.CharField(max_length=36, blank=True)     # UUID of target object
    target_name = models.CharField(max_length=200, blank=True)  # Human readable name
    
    # Request context
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Action details
    description = models.TextField()
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    # Additional context
    session = models.ForeignKey(UserSession, on_delete=models.SET_NULL, null=True, blank=True)
    is_suspicious = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    # History tracking
    history = HistoricalRecords()
    
    class Meta:
        db_table = 'core_user_action'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['is_suspicious']),
            models.Index(fields=['target_model', 'target_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.get_action_type_display()} at {self.created_at}"
```

### Step 2: IP Logging Middleware

#### 2.1: Session Tracking Middleware

```python
# apps/core/middleware/ip_logging.py
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.core.utils.ip_utils import get_client_ip, get_user_agent, get_ip_location, is_suspicious_ip
from apps.core.models.session_tracking import UserSession
import logging

logger = logging.getLogger('security')
User = get_user_model()

class IPLoggingMiddleware(MiddlewareMixin):
    """Middleware to track user sessions and IP addresses."""
    
    def process_request(self, request):
        """Process incoming request and track session data."""
        
        # Skip for non-authenticated users and static files
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None
        
        # Get IP and user agent
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        # Store in request for use by other components
        request.client_ip = ip_address
        request.client_user_agent = user_agent
        
        # Get or create session tracking
        session_key = request.session.session_key or ''
        
        try:
            user_session, created = UserSession.objects.get_or_create(
                user=request.user,
                ip_address=ip_address,
                session_key=session_key,
                defaults={
                    'user_agent': user_agent,
                    'last_activity': timezone.now(),
                }
            )
            
            if created:
                # New session - get location data
                location = get_ip_location(ip_address)
                user_session.country = location['country']
                user_session.city = location['city']
                user_session.region = location['region']
                user_session.timezone = location.get('timezone', '')
                
                # Check for suspicious patterns
                is_suspicious, reason = is_suspicious_ip(ip_address, request.user)
                user_session.is_suspicious = is_suspicious
                user_session.suspicious_reason = reason
                
                user_session.save()
                
                # Log new session
                logger.info(
                    f"New session: {request.user.username} from {ip_address} "
                    f"({location['city']}, {location['country']})"
                )
                
                if is_suspicious:
                    logger.warning(
                        f"Suspicious session: {request.user.username} from {ip_address} "
                        f"- {reason}"
                    )
            
            else:
                # Existing session - update last activity
                user_session.last_activity = timezone.now()
                user_session.save(update_fields=['last_activity'])
            
            # Store session reference in request
            request.user_session = user_session
            
        except Exception as e:
            logger.error(f"Error tracking session for {request.user.username}: {e}")
            request.user_session = None
        
        return None
```

### Step 3: Integration with History and Actions

#### 3.1: Enhanced History Middleware

```python
# apps/core/middleware/enhanced_history.py
from simple_history.middleware import HistoryRequestMiddleware
from apps.core.utils.ip_utils import get_client_ip
from apps.core.models.session_tracking import UserAction

class EnhancedHistoryMiddleware(HistoryRequestMiddleware):
    """Enhanced history middleware with IP and location tracking."""
    
    def process_request(self, request):
        # Call parent middleware
        super().process_request(request)
        
        # Add IP address to history context
        if hasattr(request, 'user') and request.user.is_authenticated:
            request._history_ip = getattr(request, 'client_ip', get_client_ip(request))
            request._history_user_agent = getattr(request, 'client_user_agent', '')
    
    def process_response(self, request, response):
        """Log completed actions."""
        
        # Check if this was a modifying operation
        if (hasattr(request, 'user') and 
            request.user.is_authenticated and 
            request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and
            response.status_code < 400):
            
            # Determine action type from URL pattern
            action_type = self._get_action_type(request)
            if action_type:
                self._log_user_action(request, action_type, success=True)
        
        return response
    
    def _get_action_type(self, request):
        """Determine action type from request."""
        path = request.path.lower()
        method = request.method
        
        if '/patients/' in path:
            if method == 'POST' and path.endswith('/create/'):
                return 'patient_create'
            elif method == 'POST' and '/update/' in path:
                return 'patient_update'
            elif method == 'POST' and '/delete/' in path:
                return 'patient_delete'
            elif method == 'POST' and '/restore/' in path:
                return 'patient_restore'
        
        elif '/events/' in path or '/dailynotes/' in path:
            if method == 'POST' and ('create' in path or path.endswith('/')):
                return 'event_create'
            elif method == 'POST' and 'update' in path:
                return 'event_update'
            elif method == 'POST' and 'delete' in path:
                return 'event_delete'
        
        return None
    
    def _log_user_action(self, request, action_type, success=True, error_message=''):
        """Log user action with IP and context."""
        try:
            ip_address = getattr(request, 'client_ip', get_client_ip(request))
            user_agent = getattr(request, 'client_user_agent', '')
            user_session = getattr(request, 'user_session', None)
            
            # Get location if not in session
            location = {'country': '', 'city': ''}
            if user_session:
                location['country'] = user_session.country
                location['city'] = user_session.city
            
            UserAction.objects.create(
                user=request.user,
                action_type=action_type,
                ip_address=ip_address,
                user_agent=user_agent,
                country=location['country'],
                city=location['city'],
                description=f"{action_type} via {request.method} {request.path}",
                success=success,
                error_message=error_message,
                session=user_session,
                is_suspicious=user_session.is_suspicious if user_session else False,
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger('security')
            logger.error(f"Error logging user action: {e}")
```

#### 3.2: Manual Action Logging Decorator

```python
# apps/core/decorators/logging.py
from functools import wraps
from apps.core.models.session_tracking import UserAction
from apps.core.utils.ip_utils import get_client_ip, get_user_agent

def log_user_action(action_type, target_model=None):
    """
    Decorator to manually log specific user actions.
    
    Usage:
    @log_user_action('patient_create', target_model='Patient')
    def create_patient(request, ...):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Execute the view
            try:
                result = view_func(request, *args, **kwargs)
                success = True
                error_message = ''
            except Exception as e:
                success = False
                error_message = str(e)
                result = None
            
            # Log the action if user is authenticated
            if hasattr(request, 'user') and request.user.is_authenticated:
                try:
                    ip_address = getattr(request, 'client_ip', get_client_ip(request))
                    user_agent = getattr(request, 'client_user_agent', get_user_agent(request))
                    user_session = getattr(request, 'user_session', None)
                    
                    location = {'country': '', 'city': ''}
                    if user_session:
                        location['country'] = user_session.country
                        location['city'] = user_session.city
                    
                    UserAction.objects.create(
                        user=request.user,
                        action_type=action_type,
                        target_model=target_model or '',
                        ip_address=ip_address,
                        user_agent=user_agent,
                        country=location['country'],
                        city=location['city'],
                        description=f"{action_type} at {request.path}",
                        success=success,
                        error_message=error_message,
                        session=user_session,
                        is_suspicious=user_session.is_suspicious if user_session else False,
                    )
                    
                except Exception as log_error:
                    import logging
                    logger = logging.getLogger('security')
                    logger.error(f"Error in log_user_action decorator: {log_error}")
            
            # Re-raise exception if view failed
            if not success:
                raise result
                
            return result
        return wrapper
    return decorator
```

### Step 4: Authentication Event Logging

#### 4.1: Login/Logout Signal Handlers

```python
# apps/accounts/signals.py
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from apps.core.models.session_tracking import UserAction
from apps.core.utils.ip_utils import get_client_ip, get_user_agent, get_ip_location
import logging

logger = logging.getLogger('security')

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log user login with IP and location."""
    try:
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        location = get_ip_location(ip_address)
        
        UserAction.objects.create(
            user=user,
            action_type='user_login',
            ip_address=ip_address,
            user_agent=user_agent,
            country=location['country'],
            city=location['city'],
            description=f"User login from {location['city']}, {location['country']}",
            success=True,
        )
        
        logger.info(
            f"User login: {user.username} from {ip_address} "
            f"({location['city']}, {location['country']})"
        )
        
    except Exception as e:
        logger.error(f"Error logging user login: {e}")

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout."""
    if user:  # user can be None for anonymous logouts
        try:
            ip_address = get_client_ip(request)
            user_agent = get_user_agent(request)
            
            UserAction.objects.create(
                user=user,
                action_type='user_logout',
                ip_address=ip_address,
                user_agent=user_agent,
                description=f"User logout from {ip_address}",
                success=True,
            )
            
            logger.info(f"User logout: {user.username} from {ip_address}")
            
        except Exception as e:
            logger.error(f"Error logging user logout: {e}")
```

### Step 5: Admin Interface for IP Logs

#### 5.1: Session Admin

```python
# apps/core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from apps.core.models.session_tracking import UserSession, UserAction

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'ip_address', 'country', 'city', 
        'is_suspicious', 'created_at', 'last_activity'
    ]
    list_filter = [
        'is_suspicious', 'country', 'created_at'
    ]
    search_fields = ['user__username', 'ip_address', 'city', 'country']
    readonly_fields = ['created_at', 'last_activity']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(UserAction)  
class UserActionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'action_type', 'target_name', 'ip_address', 
        'country', 'success', 'is_suspicious', 'created_at'
    ]
    list_filter = [
        'action_type', 'success', 'is_suspicious', 
        'country', 'created_at'
    ]
    search_fields = [
        'user__username', 'ip_address', 'target_name', 
        'description', 'city', 'country'
    ]
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'session')
    
    def target_name(self, obj):
        if obj.target_name:
            return obj.target_name
        elif obj.target_model and obj.target_id:
            return f"{obj.target_model} ({obj.target_id[:8]}...)"
        return '-'
    target_name.short_description = 'Target'
```

### Step 6: IP Analysis Tools

#### 6.1: Suspicious Activity Detection

```python
# apps/core/management/commands/analyze_ip_activity.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
from apps.core.models.session_tracking import UserAction, UserSession

class Command(BaseCommand):
    help = 'Analyze IP activity for suspicious patterns'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Analyze activity from last N days'
        )
    
    def handle(self, *args, **options):
        cutoff_date = timezone.now() - timedelta(days=options['days'])
        
        self.stdout.write(f"Analyzing IP activity from last {options['days']} days...")
        
        # 1. Multiple users from same IP
        self._analyze_shared_ips(cutoff_date)
        
        # 2. Users accessing from multiple countries
        self._analyze_geographic_anomalies(cutoff_date)
        
        # 3. High activity IPs
        self._analyze_high_activity_ips(cutoff_date)
        
        # 4. Suspicious sessions
        self._analyze_suspicious_sessions(cutoff_date)
    
    def _analyze_shared_ips(self, cutoff_date):
        """Find IPs used by multiple users."""
        self.stdout.write("\n=== IPs Used by Multiple Users ===")
        
        ip_users = defaultdict(set)
        
        for action in UserAction.objects.filter(created_at__gte=cutoff_date):
            ip_users[action.ip_address].add(action.user.username)
        
        for ip, users in ip_users.items():
            if len(users) > 1:
                self.stdout.write(
                    f"🔍 IP {ip}: {len(users)} users - {', '.join(users)}"
                )
    
    def _analyze_geographic_anomalies(self, cutoff_date):
        """Find users accessing from multiple countries."""
        self.stdout.write("\n=== Geographic Anomalies ===")
        
        user_countries = defaultdict(set)
        
        for action in UserAction.objects.filter(
            created_at__gte=cutoff_date,
            country__isnull=False
        ).exclude(country=''):
            user_countries[action.user.username].add(action.country)
        
        for username, countries in user_countries.items():
            if len(countries) > 1:
                self.stdout.write(
                    f"🌍 User {username}: {len(countries)} countries - {', '.join(countries)}"
                )
    
    def _analyze_high_activity_ips(self, cutoff_date):
        """Find IPs with unusually high activity."""
        self.stdout.write("\n=== High Activity IPs ===")
        
        ip_activity = defaultdict(int)
        
        for action in UserAction.objects.filter(created_at__gte=cutoff_date):
            ip_activity[action.ip_address] += 1
        
        # Show IPs with more than 50 actions
        for ip, count in sorted(ip_activity.items(), key=lambda x: x[1], reverse=True):
            if count > 50:
                self.stdout.write(f"🔥 IP {ip}: {count} actions")
    
    def _analyze_suspicious_sessions(self, cutoff_date):
        """Show flagged suspicious sessions."""
        self.stdout.write("\n=== Suspicious Sessions ===")
        
        suspicious_sessions = UserSession.objects.filter(
            is_suspicious=True,
            created_at__gte=cutoff_date
        ).select_related('user')
        
        for session in suspicious_sessions:
            self.stdout.write(
                f"⚠️  {session.user.username} from {session.ip_address} "
                f"({session.city}, {session.country}) - {session.suspicious_reason}"
            )
```

### Step 7: Testing Implementation

#### 7.1: IP Logging Tests

```python
# apps/core/tests/test_ip_logging.py
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from apps.core.models.session_tracking import UserSession, UserAction
from apps.core.middleware.ip_logging import IPLoggingMiddleware
from apps.core.utils.ip_utils import get_client_ip, get_ip_location

User = get_user_model()

class TestIPLogging(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser')
        self.middleware = IPLoggingMiddleware()
    
    def test_ip_capture(self):
        """Test that IP address is captured correctly."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.100')
    
    def test_forwarded_ip_capture(self):
        """Test IP capture through proxy headers."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1, 192.168.1.100'
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        ip = get_client_ip(request)
        self.assertEqual(ip, '203.0.113.1')  # Should get original IP
    
    def test_session_tracking(self):
        """Test that user sessions are tracked."""
        request = self.factory.get('/')
        request.user = self.user
        request.session = self.client.session
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        # Process request
        self.middleware.process_request(request)
        
        # Check session was created
        session = UserSession.objects.filter(user=self.user).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.ip_address, '192.168.1.100')
    
    def test_action_logging(self):
        """Test that user actions are logged."""
        # This would be tested through actual views
        # that use the logging decorator or middleware
        pass
    
    @patch('apps.core.utils.ip_utils.requests.get')
    def test_ip_location_lookup(self, mock_get):
        """Test IP location lookup."""
        mock_response = {
            'country_name': 'United States',
            'city': 'New York',
            'region': 'New York',
            'timezone': 'America/New_York'
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response
        
        location = get_ip_location('203.0.113.1')
        
        self.assertEqual(location['country'], 'United States')
        self.assertEqual(location['city'], 'New York')
```

## Implementation Checklist

### Development Phase
- [ ] Create IP utilities module
- [ ] Create session tracking models
- [ ] Implement IP logging middleware
- [ ] Enhance history middleware with IP data
- [ ] Create manual logging decorator
- [ ] Add authentication event logging
- [ ] Create admin interfaces
- [ ] Build analysis tools
- [ ] Write comprehensive tests

### Configuration Phase
- [ ] Update Django settings with middleware
- [ ] Configure IP geolocation API
- [ ] Set up security logging
- [ ] Create initial database schema with IP logging tables
- [ ] Configure caching for IP lookups

### Testing Phase
- [ ] Test IP capture accuracy
- [ ] Test session tracking
- [ ] Test action logging
- [ ] Test geographic lookups
- [ ] Test suspicious activity detection
- [ ] Test admin interfaces
- [ ] Performance test with logging overhead

### Deployment Phase
- [ ] Review privacy implications
- [ ] Deploy to staging environment
- [ ] Verify IP logging in staging
- [ ] Monitor performance impact
- [ ] Deploy to production
- [ ] Set up log monitoring alerts

## Expected Benefits

### Forensic Capabilities
- **Complete IP attribution** for all critical actions
- **Geographic tracking** of access patterns
- **Session correlation** for investigation
- **Evidence collection** for incident response

### Security Detection
- **Unusual geographic access** patterns
- **Shared IP usage** across accounts
- **High-frequency attacks** from specific IPs
- **Credential compromise** indicators

### Compliance Support
- **Access logging** for audit requirements
- **Geographic compliance** (data residency)
- **Incident documentation** capabilities
- **Regulatory reporting** support

## Success Metrics

- [ ] 100% of critical actions logged with IP address
- [ ] Geographic location captured for 95%+ of sessions
- [ ] Suspicious activity detection working
- [ ] Admin interface provides useful forensic data
- [ ] Performance impact < 2% on normal operations
- [ ] Log retention meets compliance requirements

This phase provides the IP tracking foundation needed to investigate and prevent the type of database abuse you experienced, with geographic context and pattern detection capabilities.