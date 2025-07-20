# Sample Content App Documentation

The Sample Content app provides template content management for various medical event types in the EquipeMed platform.

## Overview

The Sample Content app allows superusers to create and manage template content that can be used across different event types. This helps standardize medical documentation and provides quick access to commonly used templates.

## Key Features

- **Template Management**: Create, read, update, and delete sample content templates
- **Event Type Integration**: Templates are categorized by event types (Daily Notes, History & Physical, etc.)
- **Permission Control**: Superuser-only write access, read access for all authenticated users
- **API Access**: RESTful endpoint for programmatic access
- **Web Interface**: User-friendly interface with filtering and pagination
- **Search & Filter**: Filter templates by event type
- **Audit Trail**: Track creation and modification history

## Models

### SampleContent

The main model for storing template content.

**Fields:**

- `id`: UUID primary key
- `title`: CharField (max 255 chars) - Template title
- `content`: TextField - Template content
- `event_type`: PositiveSmallIntegerField - Links to Event.EVENT_TYPE_CHOICES
- `created_at`: DateTimeField - Auto-generated creation timestamp
- `created_by`: ForeignKey to User - User who created the template
- `updated_at`: DateTimeField - Auto-updated modification timestamp
- `updated_by`: ForeignKey to User - User who last modified the template

**Methods:**

- `__str__()`: Returns the title
- `get_event_type_display_formatted()`: Returns formatted event type display name

**Meta Options:**

- Ordering: `['event_type', 'title']`
- Verbose names: "Conteúdo de Exemplo" / "Conteúdos de Exemplo"
- Database indexes on `event_type` and `created_at` fields

## Permissions

### Access Control

- **Read Access**: All authenticated users can view sample content
- **Write Access**: Only superusers can create, edit, or delete sample content
- **Admin Interface**: Restricted to superusers only

### Implementation

Permission control is implemented at multiple levels:

1. **Admin Interface**: Custom `has_*_permission` methods restrict access
2. **Views**: LoginRequiredMixin ensures authentication
3. **API**: Authentication required for all endpoints

## URLs

### Web Interface

- `/sample-content/` - List all sample content with filtering options

### API Endpoints

- `/sample-content/api/event-type/<event_type>/` - Get sample content by event type (JSON)

## Usage Examples

### Model Usage

```python
from apps.sample_content.models import SampleContent
from apps.events.models import Event

# Create new sample content (superuser only)
sample = SampleContent.objects.create(
    title="Daily Note Template",
    content="Patient presents in [condition]...",
    event_type=Event.DAILY_NOTE_EVENT,
    created_by=superuser,
    updated_by=superuser
)

# Query sample content
daily_note_templates = SampleContent.objects.filter(
    event_type=Event.DAILY_NOTE_EVENT
)

# Get all templates ordered by event type
all_templates = SampleContent.objects.all()
```

### API Usage

```javascript
// Fetch daily note templates
fetch("/sample-content/api/event-type/1/")
  .then((response) => response.json())
  .then((data) => {
    data.sample_contents.forEach((template) => {
      console.log(`${template.title}: ${template.content}`);
    });
  });
```

### Admin Interface

1. Login as superuser
2. Navigate to `/admin/`
3. Find "Sample Content" under "SAMPLE_CONTENT" section
4. Create, edit, or delete templates as needed

## Management Commands

### create_sample_content

Creates initial sample content templates for common event types.

```bash
python manage.py create_sample_content

# Specify superuser by email
python manage.py create_sample_content --superuser-email admin@example.com
```

**What it creates:**

- Daily Note template
- History & Physical template
- Simple Note template
- Discharge Report template
- Exam Request template

## Testing

Run the test suite:

```bash
python manage.py test apps.sample_content.tests
```

**Test Coverage:**

- Model creation and validation
- String representation
- View authentication and permissions
- API endpoint functionality
- Template rendering

## Integration with Other Apps

### Events App

- Uses `Event.EVENT_TYPE_CHOICES` for consistent event type mapping
- Templates can be used when creating new events of matching types

### Admin Integration

- Follows standard Django admin patterns
- Consistent with other app admin interfaces
- Proper permission controls implemented

## File Structure

```
apps/sample_content/
├── __init__.py
├── admin.py                 # Admin interface configuration
├── apps.py                  # App configuration
├── models.py                # SampleContent model
├── tests.py                 # Test suite
├── urls.py                  # URL patterns
├── views.py                 # Views and API endpoints
├── management/
│   └── commands/
│       └── create_sample_content.py  # Management command
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py     # Initial migration
└── templates/
    └── sample_content/
        └── sample_content_list.html  # List view template
```

## Future Enhancements

Potential areas for expansion:

- Rich text editor integration for content editing
- Template versioning system
- Template sharing between institutions
- Import/export functionality
- Template usage analytics
- Integration with event creation forms for auto-population

