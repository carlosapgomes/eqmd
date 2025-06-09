# DailyNote Model Implementation Plan

This document outlines the detailed implementation plan for the DailyNote model and its associated features using a vertical slicing approach.

## Project Overview

The DailyNote app extends the existing Event system to provide specialized daily note functionality for medical records. It inherits from the Event model and adds content field with EasyMDE editor support.

### Key Requirements
- Extend `apps.events.models.Event` model
- Add to `INSTALLED_APPS` in settings
- Create full CRUD operations with permissions
- Use EasyMDE editor for content field
- Follow project styling guidelines
- Implement comprehensive testing

### Architecture Context
- **Base Event Model**: Located in `apps/events/models.py` with UUID primary keys, audit fields, and inheritance support
- **Patient Model**: Located in `apps/patients/models.py` with UUID primary keys and hospital relationships
- **Permission System**: Comprehensive role-based permissions in `apps/core/permissions/`
- **Styling**: Bootstrap 5.3 with medical theme and crispy forms
- **Testing**: pytest with Django integration, use Django test runner for events-related apps

## Vertical Slicing Approach

### Slice 1: Core Model and Basic Infrastructure
**Goal**: Establish the foundation with model, admin, and basic configuration

#### 1.1 App Configuration
- [ ] Add `apps.dailynotes` to `INSTALLED_APPS` in `config/settings.py`
- [ ] Verify app is properly configured and can be imported

#### 1.2 Model Implementation
- [ ] Create `DailyNote` model in `apps/dailynotes/models.py`:
  - Inherit from `apps.events.models.Event`
  - Add `content = models.TextField(verbose_name="Conteúdo")`
  - Implement `save()` method to set `event_type = Event.DAILY_NOTE_EVENT`
  - Implement `__str__()` method
  - Add Meta class with Portuguese verbose names

#### 1.3 Admin Integration
- [ ] Create admin configuration in `apps/dailynotes/admin.py`:
  - Register `DailyNote` model
  - Configure list display, filters, and search
  - Set up proper field ordering and readonly fields

#### 1.4 Database Migration
- [ ] Create and run initial migration
- [ ] Test model creation in Django shell

#### 1.5 Basic Testing
- [ ] Create basic model tests in `apps/dailynotes/tests.py`:
  - Test model creation
  - Test string representation
  - Test save method behavior
  - Test inheritance from Event

**Verification Commands**:
```bash
python manage.py shell -c "from apps.dailynotes.models import DailyNote"
python manage.py test apps.dailynotes.tests -v --no-cov
```

### Slice 2: Forms and Basic Views
**Goal**: Create forms and basic CRUD views without templates

#### 2.1 Forms Implementation
- [ ] Create `apps/dailynotes/forms.py`:
  - Create `DailyNoteForm` using crispy forms
  - Configure field layout for responsive design
  - Add proper validation and help text
  - Integrate EasyMDE editor configuration

#### 2.2 Basic Views
- [ ] Create `apps/dailynotes/views.py`:
  - Implement `DailyNoteListView` (class-based)
  - Implement `DailyNoteDetailView` (class-based)
  - Implement `DailyNoteCreateView` (class-based)
  - Implement `DailyNoteUpdateView` (class-based)
  - Implement `DailyNoteDeleteView` (class-based)
  - Add proper permission decorators and mixins

#### 2.3 URL Configuration
- [ ] Create `apps/dailynotes/urls.py`:
  - Define URL patterns for all CRUD operations
  - Use UUID patterns for detail/update/delete views
  - Follow RESTful naming conventions

#### 2.4 Main URL Integration
- [ ] Add dailynotes URLs to `config/urls.py`:
  - Include dailynotes URLs with proper namespace

#### 2.5 Form Testing
- [ ] Add form tests:
  - Test form validation with valid data
  - Test form validation with invalid data
  - Test form field configuration
  - Test crispy forms integration

**Verification Commands**:
```bash
python manage.py test apps.dailynotes.tests.test_forms -v --no-cov
```

### Slice 3: Templates and UI Integration
**Goal**: Create complete user interface with proper styling

#### 3.1 Template Structure
- [ ] Create template directory: `apps/dailynotes/templates/dailynotes/`
- [ ] Create base templates following project structure:
  - `dailynote_list.html` - List view with pagination
  - `dailynote_detail.html` - Detail view with actions
  - `dailynote_form.html` - Create/update form
  - `dailynote_confirm_delete.html` - Delete confirmation

#### 3.2 Template Implementation
- [ ] Implement list template:
  - Bootstrap 5 table with medical styling
  - Pagination controls
  - Search and filter options
  - Action buttons with proper permissions

- [ ] Implement detail template:
  - Patient information display
  - Content rendering with markdown support
  - Edit/delete buttons with permission checks
  - Breadcrumb navigation

- [ ] Implement form template:
  - Crispy forms integration
  - EasyMDE editor initialization
  - Responsive layout
  - Proper error handling

- [ ] Implement delete confirmation:
  - Clear confirmation message
  - Cancel and confirm buttons
  - Proper styling

#### 3.3 EasyMDE Integration
- [ ] Configure EasyMDE editor in form template:
  - Load required CSS and JS files
  - Initialize editor with proper configuration
  - Set Portuguese placeholder text
  - Configure toolbar options

#### 3.4 Navigation Integration
- [ ] Add navigation items to sidebar (if applicable)
- [ ] Update breadcrumbs and page titles
- [ ] Ensure responsive design

#### 3.5 Template Testing
- [ ] Add template rendering tests:
  - Test template context data
  - Test template inheritance
  - Test responsive design elements
  - Test EasyMDE integration

**Verification Commands**:
```bash
python manage.py test apps.dailynotes.tests.test_templates -v --no-cov
python manage.py runserver  # Manual UI testing
```

### Slice 4: Permissions and Security
**Goal**: Implement comprehensive permission system integration

#### 4.1 Permission Integration
- [ ] Apply permission decorators to views:
  - Use `@patient_access_required` for patient-specific operations
  - Use `@can_edit_event_required` for edit operations
  - Use `@can_delete_event_required` for delete operations
  - Use `@hospital_context_required` where appropriate

#### 4.2 Template Permission Checks
- [ ] Add permission checks in templates:
  - Show/hide action buttons based on permissions
  - Use permission template tags
  - Implement object-level permission checks

#### 4.3 View-Level Security
- [ ] Ensure proper permission checking in views:
  - Filter querysets based on user permissions
  - Validate user can access specific patients
  - Implement proper error handling for unauthorized access

#### 4.4 Permission Testing
- [ ] Add comprehensive permission tests:
  - Test different user roles (doctor, nurse, student, etc.)
  - Test hospital context requirements
  - Test time-based edit/delete restrictions
  - Test unauthorized access attempts

**Verification Commands**:
```bash
python manage.py test apps.dailynotes.tests.test_permissions -v --no-cov
```

### Slice 5: Advanced Features and Integration
**Goal**: Add advanced features and integrate with existing systems

#### 5.1 Patient Integration
- [ ] Add patient-specific daily note views:
  - List daily notes for specific patient
  - Filter by date ranges
  - Integration with patient detail pages

#### 5.2 Search and Filtering
- [ ] Implement search functionality:
  - Search by content
  - Filter by date range
  - Filter by patient
  - Filter by creator

#### 5.3 Dashboard Integration
- [ ] Add daily notes widgets to dashboard (if applicable):
  - Recent daily notes widget
  - Daily notes statistics
  - Quick action buttons

#### 5.4 Export/Print Features
- [ ] Add export functionality:
  - PDF export for individual notes
  - Print-friendly views
  - Bulk export options

#### 5.5 Integration Testing
- [ ] Add integration tests:
  - Test patient-daily note relationships
  - Test dashboard integration
  - Test search and filtering
  - Test export functionality

**Verification Commands**:
```bash
python manage.py test apps.dailynotes.tests.test_integration -v --no-cov
```

### Slice 6: Performance and Final Polish
**Goal**: Optimize performance and add final touches

#### 6.1 Performance Optimization
- [ ] Optimize database queries:
  - Add select_related and prefetch_related
  - Implement proper indexing
  - Optimize pagination queries

#### 6.2 Caching Integration
- [ ] Implement caching where appropriate:
  - Cache daily note lists
  - Cache patient-specific queries
  - Integrate with permission caching system

#### 6.3 Final Testing
- [ ] Comprehensive test suite:
  - Run all tests and ensure 100% pass rate
  - Test with large datasets
  - Performance testing
  - Cross-browser testing

#### 6.4 Documentation
- [ ] Update documentation:
  - Add API documentation
  - Update user guides
  - Document new features

**Verification Commands**:
```bash
python manage.py test apps.dailynotes.tests -v --no-cov
pytest apps/dailynotes/tests/ -v --no-cov
python manage.py test apps.dailynotes.tests.test_models apps.dailynotes.tests.test_views apps.dailynotes.tests.test_forms
```

## Testing Strategy

### Test Organization
```
apps/dailynotes/tests/
├── __init__.py
├── test_models.py      # Model tests
├── test_forms.py       # Form tests
├── test_views.py       # View tests
├── test_templates.py   # Template tests
├── test_permissions.py # Permission tests
└── test_integration.py # Integration tests
```

### Test Commands by Slice
- **Slice 1**: `python manage.py test apps.dailynotes.tests.test_models`
- **Slice 2**: `python manage.py test apps.dailynotes.tests.test_forms apps.dailynotes.tests.test_views`
- **Slice 3**: `python manage.py test apps.dailynotes.tests.test_templates`
- **Slice 4**: `python manage.py test apps.dailynotes.tests.test_permissions`
- **Slice 5**: `python manage.py test apps.dailynotes.tests.test_integration`
- **Slice 6**: `python manage.py test apps.dailynotes.tests`

### Recommended Test Runner
Use Django test runner for events-related apps due to django-model-utils dependency:
```bash
python manage.py test apps.dailynotes.tests
```

Alternative with pytest (if configured properly):
```bash
pytest apps/dailynotes/tests.py -v --no-cov
```

## File Structure After Implementation

```
apps/dailynotes/
├── __init__.py
├── admin.py                    # Admin configuration
├── apps.py                     # App configuration
├── forms.py                    # DailyNote forms
├── models.py                   # DailyNote model
├── urls.py                     # URL patterns
├── views.py                    # CRUD views
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py         # Initial migration
├── templates/dailynotes/
│   ├── dailynote_list.html     # List view
│   ├── dailynote_detail.html   # Detail view
│   ├── dailynote_form.html     # Create/update form
│   └── dailynote_confirm_delete.html # Delete confirmation
└── tests/
    ├── __init__.py
    ├── test_models.py          # Model tests
    ├── test_forms.py           # Form tests
    ├── test_views.py           # View tests
    ├── test_templates.py       # Template tests
    ├── test_permissions.py     # Permission tests
    └── test_integration.py     # Integration tests
```

## Dependencies and Requirements

### Existing Dependencies (Already Available)
- `django-model-utils`: For Event inheritance
- `django-crispy-forms`: For form styling
- `crispy-bootstrap5`: For Bootstrap 5 integration
- `easymde`: For markdown editor (static files available)

### Permission System Integration
- Use existing permission utilities from `apps.core.permissions`
- Follow established permission patterns
- Integrate with hospital context middleware

### Styling Requirements
- Follow medical theme guidelines in `docs/styling.md`
- Use Bootstrap 5.3 with medical color palette
- Implement responsive design
- Use crispy forms for consistent styling

## Success Criteria

### Functional Requirements
- [ ] DailyNote model properly inherits from Event
- [ ] Full CRUD operations work correctly
- [ ] EasyMDE editor functions properly
- [ ] Permissions are properly enforced
- [ ] Templates follow project styling guidelines

### Technical Requirements
- [ ] All tests pass (target: 100% pass rate)
- [ ] No database migration conflicts
- [ ] Proper error handling and validation
- [ ] Performance meets project standards
- [ ] Code follows project conventions

### User Experience Requirements
- [ ] Intuitive user interface
- [ ] Responsive design works on all devices
- [ ] Proper feedback for user actions
- [ ] Consistent with existing app patterns
- [ ] Accessible design principles followed

## Risk Mitigation

### Potential Risks and Solutions
1. **Model Inheritance Issues**: Test inheritance thoroughly in Slice 1
2. **Permission Integration**: Follow existing patterns and test extensively
3. **EasyMDE Integration**: Test editor functionality across browsers
4. **Performance Issues**: Implement query optimization in Slice 6
5. **Migration Conflicts**: Create clean migrations and test thoroughly

### Rollback Plan
- Each slice can be rolled back independently
- Database migrations can be reversed
- Feature flags can be used for gradual rollout
- Comprehensive testing reduces rollback risk

## Implementation Notes

### Key Design Decisions
1. **Inheritance Strategy**: Extend Event model to leverage existing infrastructure
2. **Permission Strategy**: Reuse existing permission system for consistency
3. **UI Strategy**: Follow established patterns for user familiarity
4. **Testing Strategy**: Comprehensive testing at each slice for quality assurance

### Integration Points
1. **Event System**: Inherits from Event model and uses EVENT_TYPE_CHOICES
2. **Patient System**: Links to Patient model for medical record association
3. **Permission System**: Uses existing decorators and template tags
4. **Hospital Context**: Integrates with hospital selection middleware
5. **Styling System**: Uses medical theme and crispy forms

### Performance Considerations
1. **Database Queries**: Use select_related/prefetch_related for optimization
2. **Caching**: Integrate with existing permission caching system
3. **Pagination**: Implement efficient pagination for large datasets
4. **Indexing**: Add appropriate database indexes for common queries

### Security Considerations
1. **Permission Enforcement**: Use existing permission decorators consistently
2. **Input Validation**: Validate all user inputs and sanitize content
3. **CSRF Protection**: Ensure all forms include CSRF tokens
4. **Object-Level Permissions**: Implement fine-grained access control

This implementation plan provides a systematic approach to building the DailyNote functionality while maintaining code quality, following project conventions, and ensuring comprehensive testing at each stage. The vertical slicing approach allows for incremental development and testing, reducing risk and ensuring each component works correctly before moving to the next slice.