# Phase 2: Middleware and Core Logic

## Overview

**Timeline: 2-3 weeks**
**Priority: High**

Implement core authentication flow integration and automated lifecycle checking. This phase integrates user lifecycle management into the existing middleware stack, ensuring expired users are blocked while maintaining seamless operation for active users.

## Architecture Integration

### Middleware Stack Enhancement

The user lifecycle middleware integrates with the existing security middleware stack:

```
Django Security Middleware
↓
Session Middleware  
↓
Authentication Middleware
↓ 
Terms Acceptance Middleware (existing)
↓
**User Lifecycle Middleware** (new)
↓
Password Change Middleware (existing)
↓
Messages Middleware
```

### Core Middleware Implementation

#### UserLifecycleMiddleware

```python
# apps/core/middleware.py - Add to existing middleware file

class UserLifecycleMiddleware:
    """
    Middleware that enforces user lifecycle rules for authenticated users.
    
    Checks for:
    - Account expiration
    - Excessive inactivity  
    - Required renewal status
    - Administrative suspension
    
    Integrates with existing security flow (after terms, before password change).
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('security.user_lifecycle')
    
    def __call__(self, request):
        # Skip middleware for unauthenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip middleware for superusers (admin access)
        if request.user.is_superuser:
            return self.get_response(request)
        
        # Update user activity tracking
        self._update_user_activity(request)
        
        # Check lifecycle status and enforce restrictions
        lifecycle_response = self._check_lifecycle_status(request)
        if lifecycle_response:
            return lifecycle_response
        
        return self.get_response(request)
    
    def _update_user_activity(self, request):
        """Update user activity tracking based on request"""
        user = request.user
        
        # Only update for meaningful activities (not static files, etc.)
        if self._is_meaningful_activity(request):
            activity_type = self._determine_activity_type(request)
            user.update_activity_score(activity_type)
            
            # Update status if user was previously inactive
            if user.account_status == 'inactive':
                user.account_status = 'active'
                user._change_reason = 'User reactivated due to activity'
                user.save(update_fields=['account_status', 'last_meaningful_activity', 'activity_score'])
            else:
                user.save(update_fields=['last_meaningful_activity', 'activity_score'])
    
    def _is_meaningful_activity(self, request):
        """Determine if request represents meaningful user activity"""
        # Skip static files and basic endpoints
        if (request.path_info.startswith('/static/') or 
            request.path_info.startswith('/media/') or
            request.path_info in ['/health/', '/manifest.json']):
            return False
        
        # Skip AJAX polling requests
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            if request.path_info.endswith('/status/') or 'poll' in request.path_info:
                return False
        
        return True
    
    def _determine_activity_type(self, request):
        """Determine the type of activity for scoring"""
        path = request.path_info
        method = request.method
        
        # Patient-related activities
        if '/patients/' in path:
            if method == 'POST' or method == 'PUT':
                return 'patient_edit'
            return 'patient_access'
        
        # Note/event creation
        if '/dailynotes/' in path or '/events/' in path:
            if method == 'POST':
                return 'note_creation'
            elif method in ['PUT', 'PATCH']:
                return 'note_edit'
            return 'general'
        
        # Form completion
        if '/pdf-forms/' in path and method == 'POST':
            return 'form_completion'
        
        # Media uploads
        if '/media/' in path and method == 'POST':
            return 'media_upload'
        
        # Default activity
        return 'general'
    
    def _check_lifecycle_status(self, request):
        """Check user lifecycle status and return appropriate response"""
        user = request.user
        
        # Update user status if needed
        self._update_user_status(user)
        
        # Check for various blocking conditions
        if user.is_expired:
            return self._handle_expired_user(request, user)
        
        if user.account_status == 'suspended':
            return self._handle_suspended_user(request, user)
        
        if user.account_status == 'departed':
            return self._handle_departed_user(request, user)
        
        if user.account_status == 'renewal_required':
            return self._handle_renewal_required(request, user)
        
        # Allow expired URLs for lifecycle management
        lifecycle_urls = [
            reverse('core:account_expired'),
            reverse('core:account_suspended'), 
            reverse('core:account_renewal_required'),
            reverse('account_logout'),
            '/admin/logout/',
        ]
        
        # If user status requires special handling but they're accessing allowed URLs
        if request.path_info in lifecycle_urls:
            return None
        
        # No blocking conditions - allow access
        return None
    
    def _update_user_status(self, user):
        """Update user status based on current conditions"""
        old_status = user.account_status
        new_status = None
        
        # Check expiration status
        if user.is_expired and user.account_status != 'expired':
            new_status = 'expired'
        elif user.is_expiring_soon and user.account_status == 'active':
            new_status = 'expiring_soon'
        elif user.is_inactive and user.account_status in ['active', 'expiring_soon']:
            new_status = 'inactive'
        
        # Update status if changed
        if new_status and new_status != old_status:
            user.account_status = new_status
            user._change_reason = f'Status auto-updated from {old_status} to {new_status}'
            user.save(update_fields=['account_status'])
            
            # Log status change
            self.logger.info(
                f'User lifecycle status updated: {user.username} '
                f'from {old_status} to {new_status} '
                f'(IP: {get_client_ip(request)})'
            )
    
    def _handle_expired_user(self, request, user):
        """Handle expired user access attempt"""
        self.logger.warning(
            f'Expired user access attempt: {user.username} '
            f'(expired: {user.access_expires_at}) '
            f'from IP {get_client_ip(request)} '
            f'accessing {request.path_info}'
        )
        
        try:
            messages.error(
                request,
                _('Sua conta expirou em {}. Entre em contato com o administrador para renovar o acesso.').format(
                    user.access_expires_at.strftime('%d/%m/%Y')
                )
            )
        except Exception:
            pass
        
        return redirect('core:account_expired')
    
    def _handle_suspended_user(self, request, user):
        """Handle suspended user access attempt"""
        self.logger.warning(
            f'Suspended user access attempt: {user.username} '
            f'from IP {get_client_ip(request)} '
            f'accessing {request.path_info}'
        )
        
        try:
            messages.error(
                request,
                _('Sua conta foi suspensa. Entre em contato com o administrador.')
            )
        except Exception:
            pass
        
        return redirect('core:account_suspended')
    
    def _handle_departed_user(self, request, user):
        """Handle departed user access attempt"""
        self.logger.error(
            f'Departed user access attempt: {user.username} '
            f'from IP {get_client_ip(request)} '
            f'accessing {request.path_info}'
        )
        
        try:
            messages.error(
                request,
                _('Esta conta foi desativada permanentemente.')
            )
        except Exception:
            pass
        
        return redirect('core:account_departed')
    
    def _handle_renewal_required(self, request, user):
        """Handle user requiring access renewal"""
        self.logger.info(
            f'User requiring renewal: {user.username} '
            f'from IP {get_client_ip(request)} '
            f'accessing {request.path_info}'
        )
        
        try:
            messages.warning(
                request,
                _('Seu acesso requer renovação. Confirme suas informações para continuar.')
            )
        except Exception:
            pass
        
        return redirect('core:account_renewal_required')
```

### Activity Tracking Integration

#### Activity Tracking Service

```python
# apps/core/services/activity_tracking.py

class UserActivityTracker:
    """Service for tracking meaningful user activities across the application"""
    
    @classmethod
    def track_patient_access(cls, user, patient, access_type='view'):
        """Track patient-related activities"""
        if access_type == 'edit':
            user.update_activity_score('patient_edit')
        else:
            user.update_activity_score('patient_access')
    
    @classmethod
    def track_note_creation(cls, user, note_type='dailynote'):
        """Track medical note creation"""
        user.update_activity_score('note_creation')
    
    @classmethod
    def track_form_completion(cls, user, form_type):
        """Track PDF form completions"""
        user.update_activity_score('form_completion')
    
    @classmethod
    def track_media_activity(cls, user, activity_type):
        """Track media upload/viewing activities"""
        if activity_type == 'upload':
            user.update_activity_score('media_upload')
        else:
            user.update_activity_score('media_view')
    
    @classmethod
    def track_search_activity(cls, user, search_type):
        """Track search and filtering activities"""
        user.update_activity_score('search')
    
    @classmethod
    def track_admin_activity(cls, user, admin_action):
        """Track administrative activities"""
        user.update_activity_score('admin_action')
```

#### Integration with Existing Views

```python
# Example integrations in existing views

# apps/patients/views.py - Patient access tracking
class PatientDetailView(DetailView):
    def get_object(self, queryset=None):
        patient = super().get_object(queryset)
        # Track patient access
        UserActivityTracker.track_patient_access(
            self.request.user, 
            patient, 
            'view'
        )
        return patient

# apps/dailynotes/views.py - Note creation tracking  
class DailyNoteCreateView(CreateView):
    def form_valid(self, form):
        response = super().form_valid(form)
        # Track note creation
        UserActivityTracker.track_note_creation(
            self.request.user,
            'dailynote'
        )
        return response

# apps/pdf_forms/views.py - Form completion tracking
def process_form_submission(request, form_id):
    # ... existing form processing ...
    
    # Track form completion
    UserActivityTracker.track_form_completion(
        request.user,
        form_template.name
    )
```

### Status Update Views

#### Account Status Views

```python
# apps/core/views.py - Add lifecycle status views

@login_required
def account_expired(request):
    """Handle expired account access"""
    context = {
        'page_title': 'Conta Expirada',
        'user': request.user,
        'expiration_date': request.user.access_expires_at,
        'contact_admin': True,
    }
    return render(request, 'core/account_expired.html', context)

@login_required  
def account_suspended(request):
    """Handle suspended account access"""
    context = {
        'page_title': 'Conta Suspensa',
        'user': request.user,
        'contact_admin': True,
    }
    return render(request, 'core/account_suspended.html', context)

@login_required
def account_renewal_required(request):
    """Handle account requiring renewal"""
    if request.method == 'POST':
        # Process renewal request
        form = AccountRenewalForm(request.POST, user=request.user)
        if form.is_valid():
            # Create renewal request
            renewal_request = form.save()
            
            # Notify administrators
            send_renewal_request_notification(renewal_request)
            
            messages.success(
                request,
                _('Solicitação de renovação enviada. Você receberá uma resposta em breve.')
            )
            return redirect('core:dashboard')
    else:
        form = AccountRenewalForm(user=request.user)
    
    context = {
        'page_title': 'Renovação de Acesso',
        'form': form,
        'user': request.user,
    }
    return render(request, 'core/account_renewal_required.html', context)

def account_departed(request):
    """Handle departed user access attempt - force logout"""
    logout(request)
    
    context = {
        'page_title': 'Acesso Negado',
        'message': 'Esta conta foi desativada permanentemente.',
    }
    return render(request, 'core/account_departed.html', context)
```

#### Account Renewal Form

```python
# apps/core/forms.py

class AccountRenewalForm(forms.Form):
    """Form for users to request account renewal"""
    
    current_position = forms.CharField(
        max_length=200,
        label="Posição/Cargo Atual",
        help_text="Seu cargo ou posição atual na instituição"
    )
    
    department = forms.CharField(
        max_length=100,
        label="Departamento/Setor",
        help_text="Departamento ou setor onde trabalha atualmente"
    )
    
    supervisor_name = forms.CharField(
        max_length=200,
        label="Nome do Supervisor",
        help_text="Nome do seu supervisor direto"
    )
    
    supervisor_email = forms.EmailField(
        label="Email do Supervisor",
        help_text="Email do supervisor para confirmação"
    )
    
    renewal_reason = forms.CharField(
        widget=forms.Textarea(rows=4),
        label="Motivo da Renovação",
        help_text="Explique por que precisa renovar o acesso ao sistema"
    )
    
    expected_duration = forms.ChoiceField(
        choices=[
            ('3', '3 meses'),
            ('6', '6 meses'),
            ('12', '1 ano'),
            ('24', '2 anos'),
        ],
        label="Duração Esperada",
        help_text="Por quanto tempo espera precisar do acesso"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        
        # Pre-populate fields from user profile
        self.fields['department'].initial = getattr(self.user, 'department', '')
    
    def save(self):
        """Create renewal request record"""
        from .models import AccountRenewalRequest
        
        return AccountRenewalRequest.objects.create(
            user=self.user,
            current_position=self.cleaned_data['current_position'],
            department=self.cleaned_data['department'],
            supervisor_name=self.cleaned_data['supervisor_name'],
            supervisor_email=self.cleaned_data['supervisor_email'],
            renewal_reason=self.cleaned_data['renewal_reason'],
            expected_duration_months=int(self.cleaned_data['expected_duration']),
            status='pending',
        )
```

#### Renewal Request Model

```python
# apps/core/models.py - Add renewal request tracking

class AccountRenewalRequest(models.Model):
    """Track user account renewal requests"""
    
    user = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.CASCADE,
        related_name='renewal_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # User-provided information
    current_position = models.CharField(max_length=200)
    department = models.CharField(max_length=100)
    supervisor_name = models.CharField(max_length=200)
    supervisor_email = models.EmailField()
    renewal_reason = models.TextField()
    expected_duration_months = models.PositiveIntegerField()
    
    # Request status
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('more_info_required', 'More Information Required'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Administrative response
    reviewed_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_renewal_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    # Approval details
    approved_duration_months = models.PositiveIntegerField(null=True, blank=True)
    new_expiration_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Renewal request for {self.user.username} - {self.status}"
    
    def approve(self, reviewed_by_user, duration_months, admin_notes=''):
        """Approve renewal request and extend user access"""
        from django.utils import timezone
        from datetime import timedelta
        
        self.status = 'approved'
        self.reviewed_by = reviewed_by_user
        self.reviewed_at = timezone.now()
        self.admin_notes = admin_notes
        self.approved_duration_months = duration_months
        
        # Calculate new expiration date
        current_expiration = self.user.access_expires_at or timezone.now()
        extension = timedelta(days=duration_months * 30)  # Approximate months to days
        self.new_expiration_date = current_expiration + extension
        
        # Update user account
        self.user.access_expires_at = self.new_expiration_date
        self.user.account_status = 'active'
        self.user.last_access_review = timezone.now()
        self.user.reviewed_by = reviewed_by_user
        self.user._change_reason = f'Access renewed via request #{self.id}'
        
        # Save changes
        self.save()
        self.user.save()
        
        # Send approval notification
        self._send_approval_notification()
    
    def deny(self, reviewed_by_user, admin_notes):
        """Deny renewal request"""
        self.status = 'denied'
        self.reviewed_by = reviewed_by_user
        self.reviewed_at = timezone.now()
        self.admin_notes = admin_notes
        self.save()
        
        # Send denial notification
        self._send_denial_notification()
```

## URL Configuration

### New URL Patterns

```python
# apps/core/urls.py - Add lifecycle management URLs

urlpatterns = [
    # ... existing URLs ...
    
    # User lifecycle status pages
    path("account/expired/", views.account_expired, name="account_expired"),
    path("account/suspended/", views.account_suspended, name="account_suspended"),
    path("account/renewal-required/", views.account_renewal_required, name="account_renewal_required"),
    path("account/departed/", views.account_departed, name="account_departed"),
]
```

## Settings Configuration

### Middleware Registration

```python
# config/settings.py - Update middleware stack

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "apps.core.middleware.EnhancedHistoryMiddleware",
    "apps.core.middleware.PasswordChangeRequiredMiddleware",
    "apps.core.middleware.TermsAcceptanceRequiredMiddleware",
    "apps.core.middleware.UserLifecycleMiddleware",  # New middleware
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

### Lifecycle Configuration

```python
# config/settings.py - Add lifecycle settings

# User Lifecycle Management
USER_LIFECYCLE_CONFIG = {
    'ENABLE_ACTIVITY_TRACKING': True,
    'ENABLE_AUTO_STATUS_UPDATES': True,
    'INACTIVITY_THRESHOLD_DAYS': 90,
    'EXPIRATION_WARNING_DAYS': [30, 14, 7, 3, 1],
    'ACTIVITY_SCORE_DECAY_DAYS': 7,
    'MAX_RENEWAL_REQUESTS_PER_USER': 3,
}

# Logging configuration for lifecycle events
LOGGING = {
    # ... existing logging config ...
    'loggers': {
        # ... existing loggers ...
        'security.user_lifecycle': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}
```

## Testing Strategy

### Middleware Tests

```python
# apps/core/tests/test_lifecycle_middleware.py

class UserLifecycleMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = UserLifecycleMiddleware(lambda r: HttpResponse())
        
        # Create test users with different statuses
        self.active_user = EqmdCustomUserFactory(account_status='active')
        self.expired_user = EqmdCustomUserFactory(
            account_status='expired',
            access_expires_at=timezone.now() - timedelta(days=1)
        )
        self.suspended_user = EqmdCustomUserFactory(account_status='suspended')
    
    def test_active_user_allowed(self):
        """Test that active users can access normally"""
        request = self.factory.get('/dashboard/')
        request.user = self.active_user
        
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
    
    def test_expired_user_blocked(self):
        """Test that expired users are redirected"""
        request = self.factory.get('/dashboard/')
        request.user = self.expired_user
        
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('account/expired', response.url)
    
    def test_activity_tracking(self):
        """Test that meaningful activities are tracked"""
        request = self.factory.post('/patients/1/edit/')
        request.user = self.active_user
        
        old_activity = self.active_user.last_meaningful_activity
        old_score = self.active_user.activity_score
        
        self.middleware(request)
        
        self.active_user.refresh_from_db()
        self.assertIsNotNone(self.active_user.last_meaningful_activity)
        self.assertGreater(self.active_user.activity_score, old_score)
    
    def test_status_auto_update(self):
        """Test automatic status updates"""
        # Create user that should be marked as expiring soon
        user = EqmdCustomUserFactory(
            account_status='active',
            access_expires_at=timezone.now() + timedelta(days=15)
        )
        
        request = self.factory.get('/dashboard/')
        request.user = user
        
        self.middleware(request)
        
        user.refresh_from_db()
        self.assertEqual(user.account_status, 'expiring_soon')
```

### Integration Tests

```python
# apps/core/tests/test_lifecycle_integration.py

class LifecycleIntegrationTests(TestCase):
    def test_renewal_request_workflow(self):
        """Test complete renewal request workflow"""
        # Create user requiring renewal
        user = EqmdCustomUserFactory(account_status='renewal_required')
        self.client.force_login(user)
        
        # Submit renewal request
        response = self.client.post('/account/renewal-required/', {
            'current_position': 'Resident Doctor',
            'department': 'Emergency Medicine',
            'supervisor_name': 'Dr. Smith',
            'supervisor_email': 'smith@hospital.com',
            'renewal_reason': 'Continuing residency program',
            'expected_duration': '12',
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify renewal request created
        renewal_request = AccountRenewalRequest.objects.filter(user=user).first()
        self.assertIsNotNone(renewal_request)
        self.assertEqual(renewal_request.status, 'pending')
    
    def test_middleware_order_integration(self):
        """Test middleware works correctly with existing security middleware"""
        # Test user with multiple requirements (terms + expiration)
        user = EqmdCustomUserFactory(
            terms_accepted=False,
            access_expires_at=timezone.now() - timedelta(days=1)
        )
        self.client.force_login(user)
        
        response = self.client.get('/dashboard/')
        
        # Should be redirected to terms acceptance first (middleware order)
        self.assertEqual(response.status_code, 302)
        self.assertIn('accept-terms', response.url)
```

## Performance Considerations

### Optimization Strategies

1. **Query Optimization**:
   - Use `update_fields` in save operations to minimize database writes
   - Batch activity score updates for high-frequency operations
   - Add database indexes on frequently queried fields

2. **Caching Strategy**:
   - Cache user lifecycle status for frequent checks
   - Use Redis for activity score calculations
   - Implement lazy loading for expensive property calculations

3. **Async Processing**:
   - Move activity score calculations to background tasks for high-volume operations
   - Queue status update notifications
   - Batch database updates during low-traffic periods

### Database Performance

```python
# apps/core/services/lifecycle_performance.py

class LifecyclePerformanceOptimizer:
    """Performance optimizations for lifecycle operations"""
    
    @classmethod
    def batch_update_statuses(cls, user_ids=None):
        """Efficiently update statuses for multiple users"""
        from django.db import transaction
        
        queryset = EqmdCustomUser.objects.all()
        if user_ids:
            queryset = queryset.filter(id__in=user_ids)
        
        # Use select_related to minimize queries
        users = queryset.select_related('supervisor', 'reviewed_by')
        
        updates = []
        for user in users:
            old_status = user.account_status
            new_status = cls._calculate_status(user)
            
            if new_status != old_status:
                updates.append((user.id, new_status))
        
        # Batch update statuses
        if updates:
            with transaction.atomic():
                for user_id, status in updates:
                    EqmdCustomUser.objects.filter(id=user_id).update(
                        account_status=status,
                        last_meaningful_activity=timezone.now()
                    )
    
    @classmethod
    def _calculate_status(cls, user):
        """Calculate appropriate status for user"""
        if user.is_expired:
            return 'expired'
        elif user.is_expiring_soon:
            return 'expiring_soon'
        elif user.is_inactive:
            return 'inactive'
        else:
            return 'active'
```

## Security Considerations

### Access Control

- **Middleware Order**: Lifecycle middleware runs after authentication but before content access
- **Admin Bypass**: Superusers bypass lifecycle restrictions for emergency access
- **Audit Logging**: All lifecycle events logged with IP addresses and timestamps

### Data Security

- **Sensitive Information**: Activity tracking avoids storing specific patient identifiers
- **Audit Trail**: All status changes tracked in history tables
- **Access Logs**: Failed access attempts logged for security monitoring

## Error Handling

### Graceful Degradation

```python
# Error handling in middleware
class UserLifecycleMiddleware:
    def __call__(self, request):
        try:
            # ... main middleware logic ...
        except Exception as e:
            # Log error but don't block user access
            self.logger.error(
                f'User lifecycle middleware error for {request.user.username}: {e}',
                exc_info=True
            )
            
            # Allow request to continue - don't break the application
            return self.get_response(request)
```

### Monitoring and Alerting

```python
# apps/core/monitoring/lifecycle_monitoring.py

class LifecycleMonitoring:
    """Monitor lifecycle system health and performance"""
    
    @classmethod
    def check_system_health(cls):
        """Check lifecycle system health metrics"""
        health_report = {
            'expired_users_count': EqmdCustomUser.objects.filter(account_status='expired').count(),
            'expiring_soon_count': EqmdCustomUser.objects.filter(account_status='expiring_soon').count(),
            'pending_renewals': AccountRenewalRequest.objects.filter(status='pending').count(),
            'middleware_errors_24h': cls._count_middleware_errors(),
        }
        return health_report
    
    @classmethod
    def alert_on_issues(cls):
        """Send alerts for critical issues"""
        health = cls.check_system_health()
        
        # Alert on high number of expired users
        if health['expired_users_count'] > 10:
            send_admin_alert('High number of expired users', health)
        
        # Alert on middleware errors
        if health['middleware_errors_24h'] > 100:
            send_admin_alert('Lifecycle middleware errors', health)
```

## Documentation Updates

### Admin Guide Updates

- **New middleware configuration instructions**
- **User lifecycle management procedures**
- **Renewal request processing workflow**

### Developer Integration Guide

- **Activity tracking integration examples**
- **Custom status transitions**
- **Performance optimization guidelines**

## Success Metrics

### Technical Metrics

- ✅ **Middleware Performance**: <50ms average execution time
- ✅ **Database Impact**: <10% increase in query volume
- ✅ **Error Rate**: <0.1% middleware errors

### Functional Metrics

- ✅ **Automated Blocking**: 100% of expired users blocked from access
- ✅ **Activity Tracking**: Meaningful activities properly scored
- ✅ **Status Accuracy**: User statuses accurately reflect lifecycle state

---

**Next Phase**: [Phase 3: Management Commands and Automation](phase_3_management_commands.md)
