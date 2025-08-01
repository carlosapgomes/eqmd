# Phase 2: Soft Deletes Implementation Plan

## Executive Summary

**Objective**: Implement soft deletes for critical models to prevent permanent data loss and enable recovery from malicious deletions.

**Timeline**: 1-2 days  
**Priority**: HIGH (Data protection)  
**Risk Level**: LOW-MEDIUM (Requires careful query updates)

## Problem Statement

Current system allows **permanent deletion** of:
- Patient records
- Medical events
- Critical system data

Based on your experience with bad actors attempting to delete patients, we need:
- Protection against permanent data loss
- Ability to recover "deleted" records
- Audit trail of deletion attempts
- Admin oversight of deletions

## Solution: Soft Delete Implementation

Instead of physically removing records from database:
- Mark records as `is_deleted=True`
- Filter out deleted records in normal queries
- Preserve all relationships and history
- Allow admin recovery of deleted records

## Implementation Plan

### Step 1: Create Soft Delete Base Classes

#### 1.1: Soft Delete Manager

```python
# apps/core/models/soft_delete.py
from django.db import models
from django.utils import timezone

class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that filters out soft-deleted objects by default."""
    
    def delete(self):
        """Soft delete all objects in queryset."""
        return super().update(
            is_deleted=True,
            deleted_at=timezone.now()
        )
    
    def hard_delete(self):
        """Actually delete objects from database (admin only)."""
        return super().delete()
    
    def active(self):
        """Return only non-deleted objects."""
        return self.filter(is_deleted=False)
    
    def deleted(self):
        """Return only deleted objects."""
        return self.filter(is_deleted=True)
    
    def with_deleted(self):
        """Return all objects including deleted ones."""
        return self.all()

class SoftDeleteManager(models.Manager):
    """Manager that filters out soft-deleted objects by default."""
    
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).active()
    
    def all_with_deleted(self):
        """Get all objects including soft-deleted ones."""
        return SoftDeleteQuerySet(self.model, using=self._db)
    
    def deleted_only(self):
        """Get only soft-deleted objects."""
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()

class SoftDeleteModel(models.Model):
    """Abstract base class for soft delete functionality."""
    
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'accounts.EQMDCustomUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='%(class)s_deleted_set'
    )
    deletion_reason = models.TextField(blank=True)
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access to all objects
    
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False, deleted_by=None, reason=''):
        """Soft delete this object."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.deletion_reason = reason
        self.save(using=using)
    
    def hard_delete(self, using=None, keep_parents=False):
        """Actually delete this object from database."""
        super().delete(using=using, keep_parents=keep_parents)
    
    def restore(self, restored_by=None):
        """Restore a soft-deleted object."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.deletion_reason = ''
        self.save()
        
        # Log restoration in history if available
        if hasattr(self, 'history'):
            self._change_reason = f"Restored by {restored_by.username if restored_by else 'system'}"
```

### Step 2: Update Critical Models

#### 2.1: Patient Model (CRITICAL)

```python
# apps/patients/models.py
from apps.core.models.soft_delete import SoftDeleteModel

class Patient(SoftDeleteModel):
    # ... existing fields ...
    
    class Meta:
        db_table = 'patients_patient'
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
        indexes = [
            models.Index(fields=['is_deleted', 'status']),
            models.Index(fields=['is_deleted', 'created_at']),
        ]
    
    def __str__(self):
        deleted_indicator = " [DELETED]" if self.is_deleted else ""
        return f"{self.name}{deleted_indicator}"
```

#### 2.2: Event Model (Medical Records)

```python
# apps/events/models.py
class Event(SoftDeleteModel):
    # ... existing fields ...
    
    class Meta:
        db_table = 'events_event'
        indexes = [
            models.Index(fields=['is_deleted', 'patient', 'event_datetime']),
            models.Index(fields=['is_deleted', 'created_by']),
        ]
```

#### 2.3: AllowedTag Model (System Configuration)

```python
# apps/patients/models.py
class AllowedTag(SoftDeleteModel):
    # ... existing fields ...
    
    class Meta:
        db_table = 'patients_allowedtag'
        indexes = [
            models.Index(fields=['is_deleted', 'name']),
        ]
```

### Step 3: Database Schema Setup

#### 3.1: Initial Database Creation

```bash
# Generate initial database schema with soft delete fields
uv run python manage.py makemigrations

# Apply migrations to create all tables (including soft delete fields)
uv run python manage.py migrate

# Verify soft delete fields are created
uv run python manage.py dbshell
\d patients_patient  # Should show is_deleted, deleted_at, deleted_by, deletion_reason fields
```

**Note**: Since this is a greenfield project, soft delete fields will be included in the initial database schema rather than added via migrations.

#### 3.2: Database Indexes for Performance

The model definitions include appropriate indexes:

```python
class Meta:
    db_table = 'patients_patient'
    indexes = [
        models.Index(fields=['is_deleted', 'status']),
        models.Index(fields=['is_deleted', 'created_at']),
    ]
```

These indexes are created automatically when the initial database schema is generated.

### Step 4: Update Views and Forms

#### 4.1: Patient Views Updates

```python
# apps/patients/views.py
from django.contrib import messages
from django.shortcuts import get_object_or_404
from apps.core.permissions.decorators import doctor_required

class PatientDeleteView(LoginRequiredMixin, View):
    """Soft delete patient with confirmation."""
    
    @doctor_required
    def post(self, request, patient_id):
        patient = get_object_or_404(Patient, id=patient_id)
        
        # Require deletion reason
        reason = request.POST.get('deletion_reason', '').strip()
        if not reason:
            messages.error(request, 'Deletion reason is required.')
            return redirect('patients:detail', patient_id=patient_id)
        
        # Soft delete
        patient.delete(
            deleted_by=request.user,
            reason=reason
        )
        
        messages.success(
            request, 
            f'Patient {patient.name} has been marked as deleted. '
            'This action can be reversed by an administrator.'
        )
        
        return redirect('patients:list')

class PatientRestoreView(LoginRequiredMixin, View):
    """Restore soft-deleted patient (admin only)."""
    
    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def post(self, request, patient_id):
        patient = get_object_or_404(
            Patient.all_objects.filter(is_deleted=True), 
            id=patient_id
        )
        
        patient.restore(restored_by=request.user)
        
        messages.success(
            request,
            f'Patient {patient.name} has been restored.'
        )
        
        return redirect('patients:detail', patient_id=patient_id)
```

#### 4.2: Update Existing Views

```python
# Update all existing views to handle soft deletes properly

class PatientListView(ListView):
    model = Patient
    # No changes needed - Patient.objects automatically filters out deleted
    
class PatientDetailView(DetailView):
    model = Patient
    
    def get_object(self):
        # Show deleted patients to admins only
        if self.request.user.is_superuser:
            return get_object_or_404(Patient.all_objects, id=self.kwargs['patient_id'])
        else:
            return get_object_or_404(Patient, id=self.kwargs['patient_id'])
```

### Step 5: Admin Interface Updates

#### 5.1: Enhanced Admin with Soft Delete Management

```python
# apps/patients/admin.py
from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'fiscal_number', 'status', 'is_deleted', 
        'deleted_at', 'deleted_by', 'created_at'
    ]
    list_filter = ['is_deleted', 'status', 'deleted_at']
    search_fields = ['name', 'fiscal_number']
    readonly_fields = ['deleted_at', 'deleted_by', 'deletion_reason']
    
    def get_queryset(self, request):
        # Show all patients including deleted ones in admin
        return Patient.all_objects.all()
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:patient_id>/restore/',
                self.admin_site.admin_view(self.restore_patient),
                name='patients_patient_restore',
            ),
        ]
        return custom_urls + urls
    
    def restore_patient(self, request, patient_id):
        """Restore a soft-deleted patient."""
        patient = Patient.all_objects.get(id=patient_id)
        patient.restore(restored_by=request.user)
        
        messages.success(
            request,
            f'Patient "{patient.name}" has been successfully restored.'
        )
        
        return HttpResponseRedirect(f'/admin/patients/patient/{patient_id}/change/')
    
    actions = ['soft_delete_selected', 'restore_selected']
    
    def soft_delete_selected(self, request, queryset):
        """Soft delete selected patients."""
        count = 0
        for patient in queryset:
            if not patient.is_deleted:
                patient.delete(
                    deleted_by=request.user,
                    reason=f'Bulk deletion by admin {request.user.username}'
                )
                count += 1
        
        messages.success(
            request,
            f'{count} patient(s) were soft deleted.'
        )
    soft_delete_selected.short_description = "Soft delete selected patients"
    
    def restore_selected(self, request, queryset):
        """Restore selected patients."""
        count = 0
        for patient in queryset:
            if patient.is_deleted:
                patient.restore(restored_by=request.user)
                count += 1
        
        messages.success(
            request,
            f'{count} patient(s) were restored.'
        )
    restore_selected.short_description = "Restore selected patients"
```

### Step 6: Update Template Logic

#### 6.1: Patient Detail Template

```django
<!-- apps/patients/templates/patients/patient_detail.html -->
{% if patient.is_deleted %}
    <div class="alert alert-danger">
        <i class="fas fa-exclamation-triangle"></i>
        <strong>This patient has been deleted</strong>
        <br>
        Deleted by: {{ patient.deleted_by.get_full_name|default:patient.deleted_by.username }}
        <br>
        Deleted on: {{ patient.deleted_at|date:"M d, Y H:i" }}
        {% if patient.deletion_reason %}
            <br>
            Reason: {{ patient.deletion_reason }}
        {% endif %}
        
        {% if user.is_superuser %}
            <form method="post" action="{% url 'patients:restore' patient.id %}" class="d-inline mt-2">
                {% csrf_token %}
                <button type="submit" class="btn btn-success btn-sm">
                    <i class="fas fa-undo"></i> Restore Patient
                </button>
            </form>
        {% endif %}
    </div>
{% endif %}
```

#### 6.2: Delete Confirmation Modal

```django
<!-- Delete confirmation modal with reason requirement -->
<div class="modal fade" id="deletePatientModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Delete Patient</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form method="post" action="{% url 'patients:delete' patient.id %}">
                {% csrf_token %}
                <div class="modal-body">
                    <p><strong>Warning:</strong> This will mark the patient as deleted.</p>
                    <p>This action can be reversed by an administrator.</p>
                    
                    <div class="mb-3">
                        <label for="deletion_reason" class="form-label">Reason for deletion (required):</label>
                        <textarea 
                            class="form-control" 
                            id="deletion_reason" 
                            name="deletion_reason" 
                            rows="3" 
                            required
                            placeholder="Please explain why this patient is being deleted..."
                        ></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="submit" class="btn btn-danger">Delete Patient</button>
                </div>
            </form>
        </div>
    </div>
</div>
```

### Step 7: Testing Implementation

#### 7.1: Soft Delete Tests

```python
# apps/patients/tests/test_soft_delete.py
from django.test import TestCase
from django.contrib.auth import get_user_model  
from apps.patients.models import Patient

User = get_user_model()

class TestSoftDelete(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.admin = User.objects.create_superuser(username='admin')
        
    def test_soft_delete_patient(self):
        """Test that patient soft delete works."""
        patient = Patient.objects.create(
            name='Test Patient',
            created_by=self.user
        )
        
        # Soft delete
        patient.delete(deleted_by=self.user, reason='Test deletion')
        
        # Should not appear in normal queries
        self.assertEqual(Patient.objects.count(), 0)
        
        # Should appear in all_objects
        self.assertEqual(Patient.all_objects.count(), 1)
        
        # Check deletion fields
        deleted_patient = Patient.all_objects.first()
        self.assertTrue(deleted_patient.is_deleted)
        self.assertEqual(deleted_patient.deleted_by, self.user)
        self.assertEqual(deleted_patient.deletion_reason, 'Test deletion')
        self.assertIsNotNone(deleted_patient.deleted_at)
    
    def test_restore_patient(self):
        """Test that patient restoration works."""
        patient = Patient.objects.create(
            name='Test Patient',
            created_by=self.user
        )
        
        # Soft delete then restore
        patient.delete(deleted_by=self.user, reason='Test deletion')
        patient.restore(restored_by=self.admin)
        
        # Should appear in normal queries again
        self.assertEqual(Patient.objects.count(), 1)
        
        # Check restoration
        restored_patient = Patient.objects.first()
        self.assertFalse(restored_patient.is_deleted)
        self.assertIsNone(restored_patient.deleted_at)
        self.assertIsNone(restored_patient.deleted_by)
        self.assertEqual(restored_patient.deletion_reason, '')
    
    def test_cascade_soft_delete(self):
        """Test that related objects handle soft deletes properly."""
        patient = Patient.objects.create(
            name='Test Patient',
            created_by=self.user
        )
        
        # Create related event
        from apps.events.models import Event
        event = Event.objects.create(
            patient=patient,
            description='Test event',
            created_by=self.user
        )
        
        # Soft delete patient
        patient.delete(deleted_by=self.user, reason='Test deletion')
        
        # Event should still exist and reference the patient
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.first().patient, patient)
```

### Step 8: Management Commands

#### 8.1: Cleanup Command

```python
# apps/core/management/commands/cleanup_soft_deleted.py
from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from apps.patients.models import Patient
from apps.events.models import Event

class Command(BaseCommand):
    help = 'Clean up old soft-deleted records'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete records soft-deleted more than N days ago'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
    
    def handle(self, *args, **options):
        cutoff_date = datetime.now() - timedelta(days=options['days'])
        
        # Find old soft-deleted records
        old_patients = Patient.all_objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        )
        
        old_events = Event.all_objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        )
        
        if options['dry_run']:
            self.stdout.write(f"Would delete {old_patients.count()} patients")
            self.stdout.write(f"Would delete {old_events.count()} events")
        else:
            patient_count = old_patients.count()
            event_count = old_events.count()
            
            # Hard delete old records
            old_patients.hard_delete()
            old_events.hard_delete()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Deleted {patient_count} patients and {event_count} events '
                    f'that were soft-deleted more than {options["days"]} days ago'
                )
            )
```

## Implementation Checklist

### Development Phase
- [ ] Create soft delete base classes (SoftDeleteModel, SoftDeleteManager)
- [ ] Update Patient model to inherit from SoftDeleteModel
- [ ] Update Event model to inherit from SoftDeleteModel
- [ ] Update AllowedTag model to inherit from SoftDeleteModel
- [ ] Create initial database schema with soft delete fields
- [ ] Update patient delete/restore views
- [ ] Update admin interface with restore functionality
- [ ] Update templates to show deletion status
- [ ] Write comprehensive tests
- [ ] Create cleanup management command

### Testing Phase
- [ ] Test soft delete functionality
- [ ] Test restoration functionality
- [ ] Test admin interface operations
- [ ] Test cascade behavior with related objects
- [ ] Test performance with large datasets
- [ ] Test edge cases (already deleted, etc.)
- [ ] Verify history integration works

### Deployment Phase
- [ ] Deploy to staging environment
- [ ] Verify soft delete behavior in staging
- [ ] Train admin users on restoration process
- [ ] Deploy to production
- [ ] Monitor for any issues

## Expected Benefits

### Data Protection
- **Prevents permanent data loss** from malicious deletions
- **Enables recovery** of accidentally deleted records
- **Maintains data integrity** and relationships
- **Preserves audit history** of deleted records

### Security Improvements
- **Tracks deletion attempts** with user attribution
- **Requires deletion reasons** for accountability
- **Admin oversight** of all deletions
- **Recovery capabilities** for incident response

### Operational Benefits
- **Reduces data loss incidents**
- **Simplifies backup/restore operations**
- **Enables data retention policies**
- **Supports compliance requirements**

## Risk Considerations

### Query Performance
- **Risk**: Additional filtering on all queries
- **Mitigation**: Database indexes on `is_deleted` field

### Storage Usage
- **Risk**: Deleted records consume storage
- **Mitigation**: Cleanup command for old deletions

### Code Complexity
- **Risk**: Need to handle deleted records in queries
- **Mitigation**: Manager automatically filters, clear documentation

## Success Metrics

- [ ] Zero permanent data loss from accidental deletions
- [ ] 100% of deletions tracked with user and reason
- [ ] Admin can successfully restore deleted records
- [ ] Query performance impact < 5%
- [ ] All existing functionality works unchanged
- [ ] Cleanup process maintains reasonable storage usage

This phase provides critical protection against the database poisoning scenarios you experienced, ensuring data can be recovered and incidents can be investigated.