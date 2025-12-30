# Events App - Timeline Architecture Guide

**Base event system for medical records**

## Overview

- Event types: History/Physical, Daily Notes, Photos, Exam Results, etc.
- UUID primary keys, audit trail, 24-hour edit/delete window
- django-model-utils inheritance for extensibility
- URLs: `/events/patient/<uuid>/`, `/events/user/`

## Timeline Template Architecture

**Modular event card system with type-specific functionality**

### Template Partials

Located in `apps/events/templates/events/partials/`:

- `event_card_base.html` - Base template with common structure
- `event_card_dailynote.html` - DailyNote-specific card with duplicate button
- `event_card_default.html` - Standard card for other event types

### Dynamic Rendering

- Timeline uses `event.event_type` to select appropriate template
- Event Type Detection: `event.event_type == 1` identifies DailyNote events
- Extensibility: Easy to add custom cards for new event types

### Template Block Architecture

Event card templates extend `event_card_base.html` with these blocks:

- `{% block event_actions %}` - Action buttons (view, edit, delete, etc.)
- `{% block event_content %}` - Main event content display
- `{% block event_metadata %}` - Footer metadata (creator, timestamps, etc.)
- `{% block extra_html %}` - Additional HTML (modals, hidden elements)
- `{% block extra_css %}` - Event-specific CSS styles
- `{% block extra_js %}` - Event-specific JavaScript

## Event Model Architecture

### Base Event Model

```python
class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    event_datetime = models.DateTimeField()
    description = models.TextField()
    event_type = models.IntegerField(choices=EVENT_TYPE_CHOICES)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updated_events')
```

### Event Types

```python
EVENT_TYPE_CHOICES = [
    (1, 'Daily Note'),
    (2, 'History/Physical'),
    (3, 'Photo'),
    (4, 'Exam Result'),
    (5, 'Prescription'),
    (6, 'Simple Note'),
    (7, 'Outpatient Prescription'),
    (8, 'PDF Form'),
    (9, 'Photo Series'),
    (10, 'Video Clip'),
]
```

### Inheritance Pattern

Using django-model-utils for clean inheritance:

```python
from model_utils.managers import InheritanceManager

class Event(models.Model):
    objects = InheritanceManager()
    # ... base fields ...

class DailyNote(Event):
    content = models.TextField()
    # Additional daily note fields

class Photo(Event):
    image_file = models.FileField(upload_to='photos/')
    # Additional photo fields
```

## 24-Hour Edit Window

### Edit Window Logic

- Events can be edited within 24 hours of creation
- After 24 hours, events become read-only
- Admin override available for data corrections
- Edit attempts logged in audit trail

### Implementation

```python
def can_edit_event(user, event):
    """Check if user can edit the event within time window."""
    if user.is_superuser:
        return True
    
    time_limit = timezone.now() - timedelta(hours=24)
    if event.created_at < time_limit:
        return False
    
    return user == event.created_by or has_edit_permission(user, event)
```

## Timeline Views

### Patient Timeline

- Shows all events for a specific patient
- Chronological ordering (newest first)
- Pagination for performance
- Event type filtering
- Date range filtering

### User Timeline

- Shows events created by specific user
- Cross-patient view for medical staff
- Activity tracking and statistics
- Personal productivity metrics

### Global Timeline

- System-wide event stream (admin only)
- Security monitoring
- Bulk operations overview
- System health metrics

## Event Creation Workflow

### Generic Event Creation

1. Select patient
2. Choose event type
3. Fill event-specific form
4. Auto-set creation metadata
5. Save and redirect to timeline

### Type-Specific Creation

- Each event type has custom form
- Pre-filled patient context
- Type-specific validation
- Custom success messaging

### Bulk Event Creation

- Import from external systems
- Batch operations interface
- Data validation and cleanup
- Progress tracking and reporting

## Timeline Performance Optimization

### Database Optimization

- Indexes on common query patterns
- Event type and patient indexes
- Date range indexes
- Creator indexes

### Query Optimization

```python
# Optimized timeline query
events = Event.objects.select_subclasses()\
    .select_related('patient', 'created_by')\
    .filter(patient=patient)\
    .order_by('-event_datetime')\
    .prefetch_related('tags')
```

### Template Optimization

- Lazy loading of event details
- Pagination with prefetch
- Template fragment caching
- Static asset optimization

## Event Search and Filtering

### Search Capabilities

- Full-text search in event descriptions
- Patient name and ID search
- Creator search
- Date range search
- Event type filtering

### Advanced Filtering

- Combine multiple criteria
- Save filter presets
- Export filtered results
- Filter history tracking

### Search Performance

- Full-text search indexes
- Cached filter options
- Optimized query patterns
- Search result pagination

## Event Cards Customization

### Creating New Event Card

1. Create template in `events/partials/`
2. Extend `event_card_base.html`
3. Implement required blocks
4. Add to dynamic rendering logic

### Card Components

- Header with event type and datetime
- Content area for event-specific data
- Action buttons for CRUD operations
- Metadata footer with creator and timestamps

### Interactive Features

- Expand/collapse details
- Inline editing (within 24h window)
- Quick actions (duplicate, share, etc.)
- Real-time updates via WebSocket

## Integration Points

### Patient Integration

- Patient context in all event views
- Patient timeline aggregation
- Cross-patient event analysis
- Patient-specific event statistics

### User Integration

- Creator attribution and tracking
- User activity timelines
- Permission-based access control
- User preference settings

### MediaFiles Integration

- Embedded media in timeline
- Secure file serving
- Thumbnail generation
- Media-specific event cards

### Audit Integration

- Complete change tracking
- Security monitoring hooks
- Compliance reporting
- Data integrity verification
