# Phase 1: Audit History Implementation Plan

## Executive Summary

**Objective**: Implement comprehensive audit logging using Django Simple History to track all changes to critical models, preventing database poisoning and enabling forensic analysis.

**Timeline**: 2-3 days  
**Priority**: HIGH (Critical security vulnerability)  
**Risk Level**: LOW (Non-breaking addition)

## Problem Statement

Based on your previous experience with bad actors poisoning the database by:
- Changing patient personal data
- Attempting to delete patients
- Making unauthorized modifications

The current system has **NO audit trail** to detect or investigate such abuse.

## Solution: Django Simple History

Django Simple History automatically tracks:
- Who made changes (user)
- When changes occurred (timestamp)
- What fields changed (before/after values)
- Complete change history for forensic analysis

## Implementation Plan

### Step 1: Install and Configure Django Simple History

#### 1.1: Add Dependency

```bash
# Add to project
uv add django-simple-history

# Update requirements if using separate file
echo "django-simple-history>=3.5.0" >> requirements.txt
```

#### 1.2: Update Django Settings

```python
# config/settings.py
INSTALLED_APPS = [
    # ... existing apps ...
    'simple_history',
]

# Middleware for user tracking
MIDDLEWARE = [
    # ... existing middleware ...
    'simple_history.middleware.HistoryRequestMiddleware',
]

# Optional: Configure history manager
SIMPLE_HISTORY_HISTORY_ID_USE_UUID = True
SIMPLE_HISTORY_EDIT = True
```

### Step 2: Add History to Critical Models

#### 2.1: Patient Model (CRITICAL)

```python
# apps/patients/models.py
from simple_history.models import HistoricalRecords

class Patient(models.Model):
    # ... existing fields ...
    
    # Add history tracking
    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
        custom_model_name=lambda x: f'Historical{x}',
        cascade_delete_history=False,  # Keep history even if patient deleted
    )
    
    class Meta:
        # ... existing meta ...
        pass
```

#### 2.2: AllowedTag Model (System Configuration)

```python
# apps/patients/models.py
class AllowedTag(models.Model):
    # ... existing fields ...
    
    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
    )
```

#### 2.3: User Model (Account Changes)

```python
# apps/accounts/models.py
class EQMDCustomUser(AbstractUser):
    # ... existing fields ...
    
    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
        excluded_fields=['last_login', 'password'],  # Exclude sensitive/noisy fields
    )
```

#### 2.4: Critical Event Models

```python
# apps/events/models.py
class Event(models.Model):
    # ... existing fields ...
    
    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
    )

# apps/dailynotes/models.py  
class DailyNote(Event):
    # Inherits history from Event automatically
    pass
```

### Step 3: Database Setup

#### 3.1: Create Initial Database Tables

```bash
# Generate initial database schema with history tables
uv run python manage.py makemigrations

# Apply migrations to create all tables (including historical tables)
uv run python manage.py migrate

# Verify history tables created
uv run python manage.py dbshell
\dt historical*
```

**Note**: Since this is a greenfield project, history tables will be created as part of the initial database setup rather than added via migrations.

### Step 4: Implement History Management

#### 4.1: Custom History Manager

```python
# apps/core/history.py
from simple_history.models import HistoricalRecords
from django.conf import settings

class AuditHistoricalRecords(HistoricalRecords):
    """Custom historical records with enhanced audit capabilities."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('cascade_delete_history', False)
        kwargs.setdefault('history_change_reason_field', models.TextField(null=True))
        super().__init__(*args, **kwargs)

def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

#### 4.2: History Context Middleware

```python
# apps/core/middleware.py
from simple_history.middleware import HistoryRequestMiddleware
from .history import get_client_ip

class EnhancedHistoryMiddleware(HistoryRequestMiddleware):
    """Enhanced history middleware with IP tracking."""
    
    def process_request(self, request):
        super().process_request(request)
        # Store IP address for history records
        if hasattr(request, 'user') and request.user.is_authenticated:
            request._history_ip = get_client_ip(request)
```

### Step 5: History Views and Admin Integration

#### 5.1: Admin History Integration

```python
# apps/patients/admin.py
from simple_history.admin import SimpleHistoryAdmin

@admin.register(Patient)
class PatientAdmin(SimpleHistoryAdmin):
    list_display = ['name', 'fiscal_number', 'status', 'created_at']
    history_list_display = ['name', 'status', 'history_change_reason']
    
    def save_model(self, request, obj, form, change):
        # Add change reason for admin modifications
        if change:
            obj._change_reason = f"Admin change by {request.user.username}"
        super().save_model(request, obj, form, change)
```

#### 5.2: History API Views

```python
# apps/core/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from simple_history.models import HistoricalRecords

class PatientHistoryView(LoginRequiredMixin, ListView):
    """View patient change history."""
    template_name = 'patients/patient_history.html'
    context_object_name = 'history'
    paginate_by = 50
    
    def get_queryset(self):
        patient_id = self.kwargs['patient_id']
        return Patient.history.filter(id=patient_id).select_related('history_user')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = Patient.objects.get(id=self.kwargs['patient_id'])
        return context
```

### Step 6: Testing Implementation

#### 6.1: History Tracking Tests

```python
# apps/patients/tests/test_history.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.patients.models import Patient

User = get_user_model()

class TestPatientHistory(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        
    def test_patient_creation_history(self):
        """Test that patient creation is tracked."""
        patient = Patient.objects.create(
            name='Test Patient',
            created_by=self.user
        )
        
        # Check history record created
        history = patient.history.first()
        self.assertEqual(history.history_type, '+')  # Creation
        self.assertEqual(history.history_user, self.user)
        
    def test_patient_modification_history(self):
        """Test that patient modifications are tracked."""
        patient = Patient.objects.create(
            name='Test Patient',
            created_by=self.user
        )
        
        # Modify patient
        patient.name = 'Modified Patient'
        patient._change_reason = 'Updated patient name'
        patient.save()
        
        # Check history records
        history_records = list(patient.history.all())
        self.assertEqual(len(history_records), 2)
        
        # Latest change
        latest = history_records[0]
        self.assertEqual(latest.history_type, '~')  # Change
        self.assertEqual(latest.name, 'Modified Patient')
        self.assertEqual(latest.history_change_reason, 'Updated patient name')
```

### Step 7: Security Monitoring Queries

#### 7.1: Suspicious Activity Detection

```python
# apps/core/management/commands/detect_suspicious_activity.py
from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from apps.patients.models import Patient

class Command(BaseCommand):
    help = 'Detect suspicious database activity'
    
    def handle(self, *args, **options):
        # Detect bulk changes by same user
        yesterday = datetime.now() - timedelta(days=1)
        
        suspicious_users = (
            Patient.history
            .filter(history_date__gte=yesterday)
            .values('history_user__username')
            .annotate(change_count=models.Count('id'))
            .filter(change_count__gt=10)  # More than 10 changes per day
        )
        
        for user_data in suspicious_users:
            self.stdout.write(
                f"⚠️  User {user_data['history_user__username']} made "
                f"{user_data['change_count']} patient changes in 24h"
            )
```

## Implementation Checklist

### Development Phase
- [ ] Install django-simple-history package
- [ ] Update settings.py configuration  
- [ ] Add history to Patient model
- [ ] Add history to AllowedTag model
- [ ] Add history to User model
- [ ] Add history to Event models
- [ ] Create initial database schema with history tables
- [ ] Implement custom history middleware
- [ ] Add admin interface integration
- [ ] Create history viewing interfaces
- [ ] Write comprehensive tests
- [ ] Create monitoring commands

### Testing Phase
- [ ] Test history tracking on model creation
- [ ] Test history tracking on model updates
- [ ] Test history tracking on model deletion attempts
- [ ] Test user association with changes
- [ ] Test change reason tracking
- [ ] Test admin interface history views
- [ ] Test suspicious activity detection
- [ ] Performance test with large datasets

### Deployment Phase
- [ ] Deploy to staging environment
- [ ] Verify history tracking works in staging
- [ ] Train admin users on history interface
- [ ] Deploy to production
- [ ] Monitor initial history collection

## Expected Benefits

### Immediate Security Improvements
- **Complete audit trail** of all patient changes
- **User accountability** for every modification
- **Forensic capability** to investigate abuse
- **Change reason tracking** for compliance

### Detection Capabilities
- Identify users making excessive changes
- Track unauthorized personal data modifications
- Monitor deletion attempts
- Detect unusual activity patterns

### Compliance Benefits
- Meet audit trail requirements
- Support regulatory compliance
- Enable incident investigation
- Provide change documentation

## Risk Mitigation

### Performance Impact
- **Risk**: History tables grow large over time
- **Mitigation**: Implement history cleanup policies, database indexing

### Storage Requirements  
- **Risk**: Increased database storage needs
- **Mitigation**: Monitor storage, implement archiving strategy

### Migration Complexity
- **Risk**: Large initial migration on existing data
- **Mitigation**: Test thoroughly in staging, plan maintenance window

## Success Metrics

- [ ] 100% of patient changes tracked with user attribution
- [ ] Zero data changes without audit trail
- [ ] Admin interface shows complete change history
- [ ] Suspicious activity detection alerts work
- [ ] Performance impact < 5% on normal operations
- [ ] History data available for incident investigation

## Next Phase Integration

Phase 1 provides the foundation for:
- **Phase 2**: Soft deletes (uses history for recovery)
- **Phase 3**: IP address logging (enhances history records)
- **Phase 4**: Monitoring dashboard (displays history data)
- **Phase 5**: Email alerts (triggered by history events)

This phase is **critical** and should be implemented first as it provides the audit foundation needed to detect and investigate the type of database abuse you experienced.