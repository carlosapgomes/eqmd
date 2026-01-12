# Phase 03 – Matrix Identity Binding

## Goal

Create the model and mechanisms to link Matrix user IDs to EQMD user accounts. This binding is essential for the bot to know which physician is issuing commands.

## Prerequisites

- Phase 02 completed (OIDC provider setup)
- All existing tests passing

## Context

When a physician interacts with the Matrix bot, the bot knows the Matrix ID (e.g., `@dr.silva:matrix.hospital.br`). The bot needs to map this to an EQMD user to request delegated tokens. This phase creates that mapping.

## Tasks

### Task 3.1: Create MatrixUserBinding Model

Edit `apps/botauth/models.py`:

```python
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class MatrixUserBinding(models.Model):
    """
    Links a Matrix user ID to an EQMD user account.
    
    This binding allows the Matrix bot to identify which EQMD physician
    is issuing commands and request delegated tokens on their behalf.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matrix_binding',
        verbose_name='EQMD User'
    )
    
    matrix_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Matrix User ID',
        help_text='Full Matrix ID (e.g., @username:server.com)'
    )
    
    # Verification tracking
    verified = models.BooleanField(
        default=False,
        help_text='Whether the binding has been verified by the user'
    )
    verified_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When the binding was verified'
    )
    
    # Verification token (for email/web verification flow)
    verification_token = models.CharField(
        max_length=64,
        blank=True,
        help_text='Token for verification process'
    )
    verification_token_expires = models.DateTimeField(
        null=True, blank=True,
        help_text='When the verification token expires'
    )
    
    # Delegation control
    delegation_enabled = models.BooleanField(
        default=True,
        help_text='Whether this binding can be used for bot delegation'
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Matrix User Binding'
        verbose_name_plural = 'Matrix User Bindings'
        indexes = [
            models.Index(fields=['matrix_id']),
            models.Index(fields=['verified', 'delegation_enabled']),
        ]
    
    def __str__(self):
        status = '✓' if self.verified else '?'
        return f"{self.user.email} ↔ {self.matrix_id} [{status}]"
    
    def is_valid_for_delegation(self):
        """Check if this binding can be used for bot delegation."""
        if not self.verified:
            return False
        if not self.delegation_enabled:
            return False
        if not self.user.is_active:
            return False
        if self.user.account_status not in ('active', 'expiring_soon'):
            return False
        return True
    
    def generate_verification_token(self):
        """Generate a new verification token."""
        import secrets
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_token_expires = timezone.now() + timezone.timedelta(hours=24)
        self.save(update_fields=['verification_token', 'verification_token_expires'])
        return self.verification_token
    
    def verify(self):
        """Mark this binding as verified."""
        self.verified = True
        self.verified_at = timezone.now()
        self.verification_token = ''
        self.verification_token_expires = None
        self.save()
    
    @classmethod
    def get_user_for_matrix_id(cls, matrix_id):
        """
        Get the EQMD user for a given Matrix ID.
        Returns None if no valid binding exists.
        """
        try:
            binding = cls.objects.select_related('user').get(
                matrix_id=matrix_id,
                verified=True,
                delegation_enabled=True
            )
            if binding.is_valid_for_delegation():
                return binding.user
            return None
        except cls.DoesNotExist:
            return None


class MatrixBindingAuditLog(models.Model):
    """
    Audit log for Matrix binding operations.
    Immutable record of all binding-related events.
    """
    
    class EventType(models.TextChoices):
        BINDING_CREATED = 'created', 'Binding Created'
        BINDING_VERIFIED = 'verified', 'Binding Verified'
        BINDING_REVOKED = 'revoked', 'Binding Revoked'
        DELEGATION_ENABLED = 'delegation_enabled', 'Delegation Enabled'
        DELEGATION_DISABLED = 'delegation_disabled', 'Delegation Disabled'
        VERIFICATION_FAILED = 'verification_failed', 'Verification Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    binding = models.ForeignKey(
        MatrixUserBinding,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    
    # Denormalized for when binding is deleted
    matrix_id = models.CharField(max_length=255)
    user_email = models.EmailField()
    
    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices
    )
    
    event_details = models.JSONField(
        default=dict,
        help_text='Additional event details'
    )
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Matrix Binding Audit Log'
        verbose_name_plural = 'Matrix Binding Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['matrix_id', '-created_at']),
            models.Index(fields=['user_email', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.matrix_id} @ {self.created_at}"
```

### Task 3.2: Create and Run Migration

```bash
uv run python manage.py makemigrations botauth
uv run python manage.py migrate botauth
```

### Task 3.3: Create Admin Interface

Edit `apps/botauth/admin.py`:

```python
from django.contrib import admin
from .models import MatrixUserBinding, MatrixBindingAuditLog


@admin.register(MatrixUserBinding)
class MatrixUserBindingAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'matrix_id', 'verified', 'delegation_enabled',
        'created_at', 'verified_at'
    ]
    list_filter = ['verified', 'delegation_enabled']
    search_fields = ['user__email', 'user__username', 'matrix_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'verified_at']
    
    fieldsets = [
        ('Binding', {
            'fields': ['id', 'user', 'matrix_id']
        }),
        ('Verification', {
            'fields': ['verified', 'verified_at', 'verification_token', 
                      'verification_token_expires']
        }),
        ('Delegation Control', {
            'fields': ['delegation_enabled']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ['user', 'matrix_id']
        return self.readonly_fields


@admin.register(MatrixBindingAuditLog)
class MatrixBindingAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'matrix_id', 'user_email', 'created_at', 'ip_address'
    ]
    list_filter = ['event_type', 'created_at']
    search_fields = ['matrix_id', 'user_email']
    readonly_fields = [
        'id', 'binding', 'matrix_id', 'user_email', 'event_type',
        'event_details', 'ip_address', 'user_agent', 'created_at'
    ]
    
    def has_add_permission(self, request):
        return False  # Audit logs are created programmatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Audit logs are immutable
    
    def has_delete_permission(self, request, obj=None):
        return False  # Audit logs should never be deleted
```

### Task 3.4: Create Binding Service

Create `apps/botauth/services.py`:

```python
"""
Services for Matrix user binding operations.
"""

import logging
from django.db import transaction
from django.utils import timezone

from .models import MatrixUserBinding, MatrixBindingAuditLog

logger = logging.getLogger('security.matrix_binding')


class MatrixBindingService:
    """Service for managing Matrix ↔ EQMD user bindings."""
    
    @classmethod
    @transaction.atomic
    def create_binding(cls, user, matrix_id, request=None):
        """
        Create a new Matrix binding for a user.
        Returns (binding, created) tuple.
        """
        # Check if user already has a binding
        existing = MatrixUserBinding.objects.filter(user=user).first()
        if existing:
            return existing, False
        
        # Check if matrix_id is already bound
        if MatrixUserBinding.objects.filter(matrix_id=matrix_id).exists():
            raise ValueError(f"Matrix ID {matrix_id} is already bound to another user")
        
        # Create binding
        binding = MatrixUserBinding.objects.create(
            user=user,
            matrix_id=matrix_id,
            verified=False
        )
        
        # Generate verification token
        binding.generate_verification_token()
        
        # Audit log
        cls._log_event(
            binding=binding,
            event_type=MatrixBindingAuditLog.EventType.BINDING_CREATED,
            request=request
        )
        
        logger.info(f"Matrix binding created: {user.email} ↔ {matrix_id}")
        
        return binding, True
    
    @classmethod
    @transaction.atomic
    def verify_binding(cls, binding_or_token, request=None):
        """
        Verify a Matrix binding using the binding object or verification token.
        """
        if isinstance(binding_or_token, str):
            # It's a token
            try:
                binding = MatrixUserBinding.objects.get(
                    verification_token=binding_or_token,
                    verification_token_expires__gt=timezone.now()
                )
            except MatrixUserBinding.DoesNotExist:
                cls._log_verification_failed(binding_or_token, request)
                raise ValueError("Invalid or expired verification token")
        else:
            binding = binding_or_token
        
        binding.verify()
        
        # Audit log
        cls._log_event(
            binding=binding,
            event_type=MatrixBindingAuditLog.EventType.BINDING_VERIFIED,
            request=request
        )
        
        logger.info(f"Matrix binding verified: {binding.user.email} ↔ {binding.matrix_id}")
        
        return binding
    
    @classmethod
    @transaction.atomic
    def revoke_binding(cls, binding, request=None, reason=''):
        """
        Revoke a Matrix binding.
        """
        matrix_id = binding.matrix_id
        user_email = binding.user.email
        
        # Audit log before deletion
        cls._log_event(
            binding=binding,
            event_type=MatrixBindingAuditLog.EventType.BINDING_REVOKED,
            request=request,
            details={'reason': reason}
        )
        
        binding.delete()
        
        logger.info(f"Matrix binding revoked: {user_email} ↔ {matrix_id}")
    
    @classmethod
    @transaction.atomic
    def set_delegation_enabled(cls, binding, enabled, request=None):
        """
        Enable or disable delegation for a binding.
        """
        binding.delegation_enabled = enabled
        binding.save(update_fields=['delegation_enabled', 'updated_at'])
        
        event_type = (
            MatrixBindingAuditLog.EventType.DELEGATION_ENABLED 
            if enabled else 
            MatrixBindingAuditLog.EventType.DELEGATION_DISABLED
        )
        
        cls._log_event(
            binding=binding,
            event_type=event_type,
            request=request
        )
        
        logger.info(
            f"Matrix binding delegation {'enabled' if enabled else 'disabled'}: "
            f"{binding.user.email} ↔ {binding.matrix_id}"
        )
    
    @classmethod
    def _log_event(cls, binding, event_type, request=None, details=None):
        """Create an audit log entry."""
        MatrixBindingAuditLog.objects.create(
            binding=binding,
            matrix_id=binding.matrix_id,
            user_email=binding.user.email,
            event_type=event_type,
            event_details=details or {},
            ip_address=cls._get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
        )
    
    @classmethod
    def _log_verification_failed(cls, token, request=None):
        """Log a failed verification attempt."""
        MatrixBindingAuditLog.objects.create(
            binding=None,
            matrix_id='unknown',
            user_email='unknown',
            event_type=MatrixBindingAuditLog.EventType.VERIFICATION_FAILED,
            event_details={'token_prefix': token[:8] + '...' if token else ''},
            ip_address=cls._get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
        )
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
```

### Task 3.5: Create Binding Views

Create `apps/botauth/views.py`:

```python
"""
Views for Matrix binding management.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, TemplateView
from django.http import HttpResponseBadRequest

from .models import MatrixUserBinding
from .services import MatrixBindingService
from .forms import MatrixBindingForm


class MatrixBindingCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new Matrix binding."""
    
    model = MatrixUserBinding
    form_class = MatrixBindingForm
    template_name = 'botauth/binding_create.html'
    success_url = reverse_lazy('botauth:binding_status')
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user already has a binding
        if MatrixUserBinding.objects.filter(user=request.user).exists():
            messages.info(request, 'Você já possui uma vinculação Matrix.')
            return redirect('botauth:binding_status')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        try:
            binding, created = MatrixBindingService.create_binding(
                user=self.request.user,
                matrix_id=form.cleaned_data['matrix_id'],
                request=self.request
            )
            if created:
                messages.success(
                    self.request, 
                    'Vinculação criada. Verifique seu email para confirmar.'
                )
                # TODO: Send verification email
            return redirect(self.success_url)
        except ValueError as e:
            form.add_error('matrix_id', str(e))
            return self.form_invalid(form)


class MatrixBindingStatusView(LoginRequiredMixin, TemplateView):
    """View for showing Matrix binding status."""
    
    template_name = 'botauth/binding_status.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['binding'] = MatrixUserBinding.objects.filter(
            user=self.request.user
        ).first()
        return context


class MatrixBindingVerifyView(TemplateView):
    """View for verifying a Matrix binding via token."""
    
    template_name = 'botauth/binding_verify.html'
    
    def get(self, request, token):
        try:
            binding = MatrixBindingService.verify_binding(token, request)
            messages.success(request, 'Vinculação Matrix verificada com sucesso!')
            return redirect('botauth:binding_status')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('core:dashboard')


class MatrixBindingDeleteView(LoginRequiredMixin, DeleteView):
    """View for revoking a Matrix binding."""
    
    model = MatrixUserBinding
    template_name = 'botauth/binding_confirm_delete.html'
    success_url = reverse_lazy('botauth:binding_status')
    
    def get_queryset(self):
        # Users can only delete their own binding
        return MatrixUserBinding.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        MatrixBindingService.revoke_binding(
            self.get_object(),
            request=self.request,
            reason='User requested revocation'
        )
        messages.success(self.request, 'Vinculação Matrix removida.')
        return redirect(self.success_url)
```

### Task 3.6: Create Forms

Create `apps/botauth/forms.py`:

```python
import re
from django import forms
from .models import MatrixUserBinding


class MatrixBindingForm(forms.ModelForm):
    """Form for creating Matrix bindings."""
    
    class Meta:
        model = MatrixUserBinding
        fields = ['matrix_id']
        widgets = {
            'matrix_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '@usuario:servidor.com'
            })
        }
    
    def clean_matrix_id(self):
        matrix_id = self.cleaned_data['matrix_id'].strip()
        
        # Validate Matrix ID format: @localpart:domain
        pattern = r'^@[a-zA-Z0-9._=\-/]+:[a-zA-Z0-9.\-]+$'
        if not re.match(pattern, matrix_id):
            raise forms.ValidationError(
                'ID Matrix inválido. Use o formato @usuario:servidor.com'
            )
        
        return matrix_id
```

### Task 3.7: Create URLs

Create `apps/botauth/urls.py`:

```python
from django.urls import path
from . import views

app_name = 'botauth'

urlpatterns = [
    path('matrix/bind/', 
         views.MatrixBindingCreateView.as_view(), 
         name='binding_create'),
    path('matrix/status/', 
         views.MatrixBindingStatusView.as_view(), 
         name='binding_status'),
    path('matrix/verify/<str:token>/', 
         views.MatrixBindingVerifyView.as_view(), 
         name='binding_verify'),
    path('matrix/revoke/<uuid:pk>/', 
         views.MatrixBindingDeleteView.as_view(), 
         name='binding_delete'),
]
```

Add to `config/urls.py`:

```python
urlpatterns = [
    # ... existing patterns ...
    path('auth/', include('apps.botauth.urls', namespace='botauth')),
]
```

### Task 3.8: Create Templates

Create template directory:
```bash
mkdir -p apps/botauth/templates/botauth
```

Create `apps/botauth/templates/botauth/binding_status.html`:

```html
{% extends "base_app.html" %}
{% load i18n %}

{% block title %}Vinculação Matrix{% endblock %}

{% block content %}
<div class="container mt-4">
    <h2>Vinculação Matrix</h2>
    
    {% if binding %}
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">Status da Vinculação</h5>
                <dl class="row">
                    <dt class="col-sm-3">ID Matrix</dt>
                    <dd class="col-sm-9"><code>{{ binding.matrix_id }}</code></dd>
                    
                    <dt class="col-sm-3">Verificado</dt>
                    <dd class="col-sm-9">
                        {% if binding.verified %}
                            <span class="badge bg-success">Sim</span>
                            <small class="text-muted">em {{ binding.verified_at|date:"d/m/Y H:i" }}</small>
                        {% else %}
                            <span class="badge bg-warning">Pendente</span>
                        {% endif %}
                    </dd>
                    
                    <dt class="col-sm-3">Delegação</dt>
                    <dd class="col-sm-9">
                        {% if binding.delegation_enabled %}
                            <span class="badge bg-success">Habilitada</span>
                        {% else %}
                            <span class="badge bg-secondary">Desabilitada</span>
                        {% endif %}
                    </dd>
                    
                    <dt class="col-sm-3">Criado em</dt>
                    <dd class="col-sm-9">{{ binding.created_at|date:"d/m/Y H:i" }}</dd>
                </dl>
                
                <div class="mt-3">
                    <a href="{% url 'botauth:binding_delete' binding.pk %}" 
                       class="btn btn-outline-danger">
                        Remover Vinculação
                    </a>
                </div>
            </div>
        </div>
    {% else %}
        <div class="alert alert-info">
            <p>Você ainda não vinculou uma conta Matrix.</p>
            <p>A vinculação permite que o bot Matrix crie rascunhos de documentos em seu nome.</p>
        </div>
        <a href="{% url 'botauth:binding_create' %}" class="btn btn-primary">
            Vincular Conta Matrix
        </a>
    {% endif %}
</div>
{% endblock %}
```

Create `apps/botauth/templates/botauth/binding_create.html`:

```html
{% extends "base_app.html" %}
{% load i18n %}

{% block title %}Vincular Conta Matrix{% endblock %}

{% block content %}
<div class="container mt-4">
    <h2>Vincular Conta Matrix</h2>
    
    <div class="card">
        <div class="card-body">
            <p class="text-muted">
                Informe seu ID Matrix para habilitar a criação de rascunhos 
                de documentos via bot.
            </p>
            
            <form method="post">
                {% csrf_token %}
                
                <div class="mb-3">
                    <label for="id_matrix_id" class="form-label">ID Matrix</label>
                    {{ form.matrix_id }}
                    {% if form.matrix_id.errors %}
                        <div class="invalid-feedback d-block">
                            {{ form.matrix_id.errors.0 }}
                        </div>
                    {% endif %}
                    <div class="form-text">
                        Exemplo: @dr.silva:matrix.hospital.br
                    </div>
                </div>
                
                <button type="submit" class="btn btn-primary">Vincular</button>
                <a href="{% url 'botauth:binding_status' %}" class="btn btn-secondary">
                    Cancelar
                </a>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

Create `apps/botauth/templates/botauth/binding_confirm_delete.html`:

```html
{% extends "base_app.html" %}
{% load i18n %}

{% block title %}Remover Vinculação{% endblock %}

{% block content %}
<div class="container mt-4">
    <h2>Remover Vinculação Matrix</h2>
    
    <div class="card border-danger">
        <div class="card-body">
            <p>Tem certeza que deseja remover a vinculação com <code>{{ object.matrix_id }}</code>?</p>
            <p class="text-muted">
                Após remover, o bot Matrix não poderá mais criar rascunhos em seu nome.
            </p>
            
            <form method="post">
                {% csrf_token %}
                <button type="submit" class="btn btn-danger">Sim, Remover</button>
                <a href="{% url 'botauth:binding_status' %}" class="btn btn-secondary">
                    Cancelar
                </a>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

### Task 3.9: Add Tests

Create `apps/botauth/tests/__init__.py` and `apps/botauth/tests/test_matrix_binding.py`:

```python
import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from apps.botauth.models import MatrixUserBinding, MatrixBindingAuditLog
from apps.botauth.services import MatrixBindingService

User = get_user_model()


class MatrixUserBindingModelTest(TestCase):
    """Tests for MatrixUserBinding model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoctor',
            email='doctor@hospital.com',
            password='testpass123'
        )
    
    def test_create_binding(self):
        """Test creating a binding."""
        binding = MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        self.assertFalse(binding.verified)
        self.assertFalse(binding.is_valid_for_delegation())
    
    def test_verify_binding(self):
        """Test verifying a binding."""
        binding = MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        binding.verify()
        self.assertTrue(binding.verified)
        self.assertTrue(binding.is_valid_for_delegation())
    
    def test_inactive_user_invalid_for_delegation(self):
        """Test that inactive user binding is invalid."""
        binding = MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br',
            verified=True
        )
        self.user.is_active = False
        self.user.save()
        self.assertFalse(binding.is_valid_for_delegation())
    
    def test_get_user_for_matrix_id(self):
        """Test looking up user by Matrix ID."""
        binding = MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br',
            verified=True
        )
        
        found_user = MatrixUserBinding.get_user_for_matrix_id(
            '@doctor:matrix.hospital.br'
        )
        self.assertEqual(found_user, self.user)
        
        # Unverified binding should not return user
        binding.verified = False
        binding.save()
        self.assertIsNone(
            MatrixUserBinding.get_user_for_matrix_id('@doctor:matrix.hospital.br')
        )


class MatrixBindingServiceTest(TestCase):
    """Tests for MatrixBindingService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoctor',
            email='doctor@hospital.com',
            password='testpass123'
        )
        self.factory = RequestFactory()
    
    def test_create_binding_service(self):
        """Test creating binding via service."""
        binding, created = MatrixBindingService.create_binding(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        self.assertTrue(created)
        self.assertFalse(binding.verified)
        self.assertTrue(binding.verification_token)
        
        # Check audit log
        log = MatrixBindingAuditLog.objects.filter(
            matrix_id='@doctor:matrix.hospital.br'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.event_type, 'created')
    
    def test_verify_binding_service(self):
        """Test verifying binding via service."""
        binding, _ = MatrixBindingService.create_binding(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        token = binding.verification_token
        
        verified_binding = MatrixBindingService.verify_binding(token)
        self.assertTrue(verified_binding.verified)
        
        # Check audit log
        logs = MatrixBindingAuditLog.objects.filter(
            matrix_id='@doctor:matrix.hospital.br'
        ).order_by('created_at')
        self.assertEqual(logs.count(), 2)
        self.assertEqual(logs[1].event_type, 'verified')
    
    def test_duplicate_matrix_id_rejected(self):
        """Test that duplicate Matrix IDs are rejected."""
        MatrixBindingService.create_binding(
            user=self.user,
            matrix_id='@doctor:matrix.hospital.br'
        )
        
        user2 = User.objects.create_user(
            username='testdoctor2',
            email='doctor2@hospital.com',
            password='testpass123'
        )
        
        with self.assertRaises(ValueError):
            MatrixBindingService.create_binding(
                user=user2,
                matrix_id='@doctor:matrix.hospital.br'
            )
```

## Files to Create

1. `apps/botauth/models.py` - MatrixUserBinding, MatrixBindingAuditLog
2. `apps/botauth/services.py` - MatrixBindingService
3. `apps/botauth/views.py` - Binding management views
4. `apps/botauth/forms.py` - MatrixBindingForm
5. `apps/botauth/urls.py` - URL patterns
6. `apps/botauth/admin.py` - Admin interface
7. `apps/botauth/templates/botauth/binding_*.html` - Templates
8. `apps/botauth/tests/test_matrix_binding.py` - Tests

## Files to Modify

1. `config/urls.py` - Include botauth URLs

## Acceptance Criteria

- [ ] MatrixUserBinding model created with all fields
- [ ] MatrixBindingAuditLog model created for audit trail
- [ ] Migration applied successfully
- [ ] Admin interface allows managing bindings
- [ ] Users can create bindings via web interface
- [ ] Verification token flow works
- [ ] `is_valid_for_delegation()` correctly checks user status
- [ ] `get_user_for_matrix_id()` returns user for valid bindings
- [ ] All binding operations create audit log entries
- [ ] Tests pass for model and service

## Verification Commands

```bash
# Run migrations
uv run python manage.py migrate botauth

# Verify model creation
uv run python manage.py shell -c "from apps.botauth.models import MatrixUserBinding; print('OK')"

# Run tests
uv run pytest apps/botauth/tests/ -v

# Verify admin registration
uv run python manage.py shell -c "from django.contrib.admin.sites import site; print('MatrixUserBinding' in [m._meta.model_name for m in site._registry.keys()])"
```
