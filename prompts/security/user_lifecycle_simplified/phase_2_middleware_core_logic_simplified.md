# Phase 2: Simplified Middleware and Core Logic

## Overview
**Timeline: 1-2 weeks**
**Priority: High**

Implement essential authentication flow integration and automated lifecycle checking. This simplified phase focuses on core user blocking functionality and basic renewal workflow without complex activity scoring or advanced features.

## Core Middleware Implementation (Simplified)

### UserLifecycleMiddleware (Essential Only)

```python
# apps/core/middleware.py - Add simplified lifecycle middleware

class UserLifecycleMiddleware:
    """
    Simplified middleware that enforces essential user lifecycle rules.
    
    Checks for:
    - Account expiration
    - Administrative suspension
    - Departed user status
    
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
        
        # Update simple activity tracking
        self._update_user_activity(request)
        
        # Check lifecycle status and enforce restrictions
        lifecycle_response = self._check_lifecycle_status(request)
        if lifecycle_response:
            return lifecycle_response
        
        return self.get_response(request)
    
    def _update_user_activity(self, request):
        """Update simple user activity tracking"""
        user = request.user
        
        # Only update for meaningful activities (not static files, etc.)
        if self._is_meaningful_activity(request):
            user.update_activity_timestamp()
            
            # Update status if user was previously inactive
            if user.account_status == 'inactive':
                user.account_status = 'active'
                user._change_reason = 'User reactivated due to activity'
                user.save(update_fields=['account_status', 'last_meaningful_activity'])
            else:
                user.save(update_fields=['last_meaningful_activity'])
    
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
    
    def _check_lifecycle_status(self, request):
        """Check user lifecycle status and return appropriate response"""
        user = request.user
        
        # Update user status if needed (simplified)
        self._update_user_status(user)
        
        # Check for blocking conditions
        if user.is_expired:
            return self._handle_expired_user(request, user)
        
        if user.account_status == 'suspended':
            return self._handle_suspended_user(request, user)
        
        if user.account_status == 'departed':
            return self._handle_departed_user(request, user)
        
        if user.account_status == 'renewal_required':
            return self._handle_renewal_required(request, user)
        
        # Allow lifecycle management URLs
        lifecycle_urls = [
            reverse('core:account_expired'),
            reverse('core:account_suspended'), 
            reverse('core:account_renewal_required'),
            reverse('account_logout'),
            '/admin/logout/',
        ]
        
        if request.path_info in lifecycle_urls:
            return None
        
        # No blocking conditions - allow access
        return None
    
    def _update_user_status(self, user):
        """Update user status based on current conditions (simplified)"""
        old_status = user.account_status
        new_status = None
        
        # Simple status updates based on expiration only
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
                f'from {old_status} to {new_status}'
            )
    
    def _handle_expired_user(self, request, user):
        """Handle expired user access attempt"""
        self.logger.warning(
            f'Expired user access attempt: {user.username} '
            f'(expired: {user.access_expires_at}) '
            f'accessing {request.path_info}'
        )
        
        try:
            messages.error(
                request,
                f'Sua conta expirou em {user.access_expires_at.strftime("%d/%m/%Y")}. '
                'Entre em contato com o administrador para renovar o acesso.'
            )
        except Exception:
            pass
        
        return redirect('core:account_expired')
    
    def _handle_suspended_user(self, request, user):
        """Handle suspended user access attempt"""
        self.logger.warning(
            f'Suspended user access attempt: {user.username} '
            f'accessing {request.path_info}'
        )
        
        try:
            messages.error(
                request,
                'Sua conta foi suspensa. Entre em contato com o administrador.'
            )
        except Exception:
            pass
        
        return redirect('core:account_suspended')
    
    def _handle_departed_user(self, request, user):
        """Handle departed user access attempt"""
        self.logger.error(
            f'Departed user access attempt: {user.username} '
            f'accessing {request.path_info}'
        )
        
        try:
            messages.error(
                request,
                'Esta conta foi desativada permanentemente.'
            )
        except Exception:
            pass
        
        return redirect('core:account_departed')
    
    def _handle_renewal_required(self, request, user):
        """Handle user requiring access renewal"""
        self.logger.info(
            f'User requiring renewal: {user.username} '
            f'accessing {request.path_info}'
        )
        
        try:
            messages.warning(
                request,
                'Seu acesso requer renovação. Confirme suas informações para continuar.'
            )
        except Exception:
            pass
        
        return redirect('core:account_renewal_required')
```

## Simplified Activity Tracking

### Basic Activity Service (No Complex Scoring)

```python
# apps/core/services/activity_tracking_simple.py

class SimpleUserActivityTracker:
    """Simplified service for basic user activity tracking"""
    
    @classmethod
    def track_activity(cls, user):
        """Track any meaningful user activity (simplified)"""
        user.update_activity_timestamp()
    
    @classmethod
    def track_patient_access(cls, user, patient):
        """Track patient-related activities"""
        cls.track_activity(user)
    
    @classmethod
    def track_note_creation(cls, user):
        """Track medical note creation"""
        cls.track_activity(user)
    
    @classmethod
    def track_form_completion(cls, user):
        """Track PDF form completions"""
        cls.track_activity(user)
```

### Integration with Existing Views (Simplified)

```python
# Example integrations in existing views (minimal changes)

# apps/patients/views.py - Patient access tracking
class PatientDetailView(DetailView):
    def get_object(self, queryset=None):
        patient = super().get_object(queryset)
        # Simple activity tracking
        SimpleUserActivityTracker.track_patient_access(self.request.user, patient)
        return patient

# apps/dailynotes/views.py - Note creation tracking  
class DailyNoteCreateView(CreateView):
    def form_valid(self, form):
        response = super().form_valid(form)
        # Simple activity tracking
        SimpleUserActivityTracker.track_note_creation(self.request.user)
        return response
```

## Status Management Views (Essential Only)

### Account Status Views (Simplified)

```python
# apps/core/views.py - Essential lifecycle status views

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
    """Handle account requiring renewal (simplified)"""
    if request.method == 'POST':
        form = SimplifiedAccountRenewalForm(request.POST, user=request.user)
        if form.is_valid():
            # Create renewal request
            renewal_request = form.save()
            
            # Send basic email notification to admin
            send_simple_renewal_notification(renewal_request)
            
            messages.success(
                request,
                'Solicitação de renovação enviada. Você receberá uma resposta em breve.'
            )
            return redirect('core:dashboard')
    else:
        form = SimplifiedAccountRenewalForm(user=request.user)
    
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

### Simplified Renewal Form

```python
# apps/core/forms.py - Simplified renewal form

class SimplifiedAccountRenewalForm(forms.Form):
    """Simplified form for users to request account renewal"""
    
    current_position = forms.CharField(
        max_length=200,
        label="Posição/Cargo Atual",
        help_text="Seu cargo ou posição atual na instituição"
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
    
    def save(self):
        """Create renewal request record"""
        from .models import AccountRenewalRequest
        
        return AccountRenewalRequest.objects.create(
            user=self.user,
            current_position=self.cleaned_data['current_position'],
            supervisor_name=self.cleaned_data['supervisor_name'],
            supervisor_email=self.cleaned_data['supervisor_email'],
            renewal_reason=self.cleaned_data['renewal_reason'],
            expected_duration_months=int(self.cleaned_data['expected_duration']),
            status='pending',
        )
```

## Settings Configuration (Simplified)

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
    "apps.core.middleware.UserLifecycleMiddleware",  # New simplified middleware
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

### Simplified Lifecycle Configuration

```python
# config/settings.py - Add essential lifecycle settings

# User Lifecycle Management (Simplified)
USER_LIFECYCLE_CONFIG = {
    'ENABLE_ACTIVITY_TRACKING': True,
    'ENABLE_AUTO_STATUS_UPDATES': True,
    'INACTIVITY_THRESHOLD_DAYS': 90,
    'EXPIRATION_WARNING_DAYS': [30, 14, 7, 3, 1],
}

# Logging for lifecycle events
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

## URL Configuration

### Essential URL Patterns

```python
# apps/core/urls.py - Add essential lifecycle URLs

urlpatterns = [
    # ... existing URLs ...
    
    # Essential user lifecycle status pages
    path("account/expired/", views.account_expired, name="account_expired"),
    path("account/suspended/", views.account_suspended, name="account_suspended"),
    path("account/renewal-required/", views.account_renewal_required, name="account_renewal_required"),
    path("account/departed/", views.account_departed, name="account_departed"),
]
```

## Simple Email Notifications

### Basic Notification Service

```python
# apps/core/services/simple_notifications.py

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

def send_simple_renewal_notification(renewal_request):
    """Send basic renewal request notification to admin"""
    subject = f'EquipeMed: Nova solicitação de renovação - {renewal_request.user.username}'
    
    context = {
        'renewal_request': renewal_request,
        'user': renewal_request.user,
        'admin_url': f"{settings.SITE_URL}/admin/core/accountrenewalrequest/{renewal_request.id}/change/",
    }
    
    message = render_to_string('emails/renewal_request_admin.txt', context)
    
    # Send to all admin users
    admin_emails = list(
        get_user_model().objects.filter(
            is_staff=True, is_active=True
        ).values_list('email', flat=True)
    )
    
    if admin_emails:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=True
        )

def send_expiration_warning_email(user, days_left):
    """Send basic expiration warning email"""
    subject = f'EquipeMD: Seu acesso expira em {days_left} dias'
    
    context = {
        'user': user,
        'days_left': days_left,
        'expiration_date': user.access_expires_at,
        'renewal_url': f"{settings.SITE_URL}/account/renewal-required/",
        'contact_email': getattr(settings, 'ADMIN_EMAIL', 'admin@equipemd.com'),
    }
    
    message = render_to_string('emails/expiration_warning_simple.txt', context)
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True
    )
```

## Testing Strategy (Simplified)

### Essential Middleware Tests

```python
# apps/core/tests/test_simplified_lifecycle_middleware.py

class SimplifiedLifecycleMiddlewareTests(TestCase):
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
    
    def test_simple_activity_tracking(self):
        """Test that activities update timestamp only"""
        request = self.factory.post('/patients/1/edit/')
        request.user = self.active_user
        
        old_activity = self.active_user.last_meaningful_activity
        
        self.middleware(request)
        
        self.active_user.refresh_from_db()
        self.assertIsNotNone(self.active_user.last_meaningful_activity)
        # No complex scoring - just timestamp updates
    
    def test_status_auto_update(self):
        """Test automatic status updates (simplified)"""
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

### Integration Tests (Essential Only)

```python
# apps/core/tests/test_simplified_integration.py

class SimplifiedIntegrationTests(TestCase):
    def test_renewal_request_workflow(self):
        """Test simplified renewal request workflow"""
        # Create user requiring renewal
        user = EqmdCustomUserFactory(account_status='renewal_required')
        self.client.force_login(user)
        
        # Submit renewal request
        response = self.client.post('/account/renewal-required/', {
            'current_position': 'Resident Doctor',
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
        """Test middleware works with existing security middleware"""
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

## Error Handling (Simplified)

### Graceful Degradation

```python
# Error handling in simplified middleware
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

## What Was Simplified

### ❌ Removed from Original:
- **Complex Activity Scoring**: No activity score calculations or decay algorithms
- **Advanced Status Logic**: Simplified to basic time-based status updates
- **Detailed Activity Categorization**: All activities treated equally (simple timestamp)
- **Performance Optimization Classes**: Basic implementation without caching or batching
- **Advanced Error Handling**: Simplified error handling and monitoring

### ✅ Kept (Essential):
- Core middleware for blocking expired users
- Simple activity timestamp tracking
- Basic renewal request workflow
- Essential status views and redirects
- Integration with existing middleware stack
- Simple email notifications

## Success Metrics (Simplified)

### Technical Metrics
- ✅ **Middleware Performance**: No significant impact on request processing
- ✅ **Database Impact**: Minimal increase in query volume
- ✅ **Error Rate**: Graceful degradation on errors

### Functional Metrics
- ✅ **Automated Blocking**: 100% of expired users blocked from access
- ✅ **Activity Tracking**: Basic activity timestamps recorded
- ✅ **Status Updates**: Essential status transitions working correctly

---

**Next Phase**: [Phase 3: Simplified Management Commands](phase_3_management_commands_simplified.md)