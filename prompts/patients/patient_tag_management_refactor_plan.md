# Patient Tag Management Refactor Plan

## Overview

Move patient tag management from the create/update forms to the patient detail page to achieve better separation of concerns between personal data and medical/organizational data.

## Current State Analysis

### Current Tag Management Location

- **Patient Create Form** (`patient_create.html`): Lines 268-301 - Full tag section with checkboxes
- **Patient Update Form** (`patient_update.html`): Lines 275-308 - Same tag section with pre-selected values
- **PatientForm** (`forms.py`): Lines 35-41, 147-155, 248-264 - Tag field definition and handling logic

### Current Tag Flow

1. User selects tags via checkboxes during patient creation/editing
2. Form handles tag selection through `tag_selection` ModelMultipleChoiceField
3. Form save method creates/assigns Tag instances to patient
4. Tags are pre-selected in update form based on existing assignments

## Refactor Goals

### Data Separation

- **Patient Forms**: Personal data only (name, birthday, documents, contact info)
- **Patient Detail Page**: Medical/organizational data (status, tags, ward assignments)

### User Experience Improvements

- Tags managed in context with patient's medical history
- Immediate visual feedback when adding/removing tags
- No need to navigate to separate form pages for tag changes
- Consistent with existing status management pattern

## Implementation Plan

### Phase 1: Remove Tags from Forms

#### 1.1 Update PatientForm (`apps/patients/forms.py`)

- **Remove tag_selection field** (lines 35-41)
- **Remove tag widget updates** in `__init__` method (lines 147-155)
- **Remove tag handling** in `save()` method (lines 248-264)
- **Remove tag section** from `get_form_sections()` method (lines 208-216)
- **Keep**: Initial record number handling for create form

#### 1.2 Update Patient Create Template (`patient_create.html`)

- **Remove Tags Section** (lines 268-301)
- **Keep**: All other sections (Basic Info, Documents, Contact, Hospital Status, Record Number)
- **Update**: Form becomes focused on patient registration essentials

#### 1.3 Update Patient Update Template (`patient_update.html`)

- **Remove Tags Section** (lines 275-308)
- **Keep**: All other sections (Basic Info, Documents, Contact, Hospital Status, Current Record Info)
- **Update**: Form becomes focused on personal data updates only

### Phase 2: Design Tag Management Interface

#### 2.1 Patient Detail Page Integration

- **Location**: Add tag management section to patient detail page (`patient_detail.html`)
- **Position**: Place near status management area for logical grouping
- **Design**: Match visual style and interaction patterns of status change modals

#### 2.2 Tag Management Components

- **Tag Display Widget**: Visual representation of current patient tags with colors
- **Add Tag Modal**: Modal dialog for adding new tags to patient
- **Remove Tag Actions**: Quick remove buttons on existing tags
- **Tag History**: Optional history of tag changes with timestamps

#### 2.3 UI/UX Design Considerations

- **Visual Consistency**: Use same button styles and modal patterns as status changes
- **Color Integration**: Display tags with their configured colors from AllowedTag model
- **Permission Checks**: Show/hide tag management based on user permissions
- **Loading States**: Show feedback during tag operations

### Phase 3: Backend Tag Management Views

#### 3.1 New View Classes (`apps/patients/views.py`)

```python
class PatientTagAddView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Add tag to patient via AJAX"""
    permission_required = 'patients.change_patient'

    def post(self, request, patient_id):
        # Handle adding tag to patient
        # Return JSON response with updated tag list

class PatientTagRemoveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Remove tag from patient via AJAX"""
    permission_required = 'patients.change_patient'

    def post(self, request, patient_id, tag_id):
        # Handle removing tag from patient
        # Return JSON response with updated tag list

class PatientTagsAPIView(LoginRequiredMixin, View):
    """API endpoint for patient tags"""

    def get(self, request, patient_id):
        # Return current patient tags as JSON
        # Include tag colors and metadata
```

#### 3.2 URL Configuration (`apps/patients/urls.py`)

```python
# Add new URL patterns
path('patients/<uuid:patient_id>/tags/add/', PatientTagAddView.as_view(), name='patient_tag_add'),
path('patients/<uuid:patient_id>/tags/<uuid:tag_id>/remove/', PatientTagRemoveView.as_view(), name='patient_tag_remove'),
path('patients/<uuid:patient_id>/tags/api/', PatientTagsAPIView.as_view(), name='patient_tags_api'),
```

### Phase 4: Frontend Tag Management

#### 4.1 Patient Detail Template Updates

- **Add tag management section** after status management
- **Include tag display widget** showing current tags with colors
- **Add modal for tag selection** similar to status change modals
- **Include JavaScript** for tag operations

#### 4.2 Tag Management Partial Template

- **Create**: `apps/patients/templates/patients/partials/tag_management.html`
- **Purpose**: Reusable tag management component
- **Contents**: Tag display, add/remove modals, JavaScript functionality

#### 4.3 JavaScript Tag Management

- **AJAX operations** for adding/removing tags
- **Dynamic UI updates** without page reload
- **Error handling** and user feedback
- **Integration** with existing status management JavaScript patterns

### Phase 5: Template Tag Integration

#### 5.1 Enhanced Patient Tag Template Tags

- **Update existing tags** in `apps/patients/templatetags/patient_tags.py`
- **Add new tags** for tag management interface rendering
- **Color support** for tag display

#### 5.2 Tag Display Components

```python
@register.inclusion_tag('patients/partials/patient_tag_badge.html')
def patient_tag_badge(tag):
    """Render individual tag with color and styling"""
    return {'tag': tag}

@register.inclusion_tag('patients/partials/tag_management_widget.html', takes_context=True)
def tag_management_widget(context, patient):
    """Render complete tag management interface"""
    return {
        'patient': patient,
        'user': context['user'],
        'available_tags': AllowedTag.objects.filter(is_active=True),
        'can_manage_tags': context['user'].has_perm('patients.change_patient')
    }
```

### Phase 6: Permission Integration ✅ COMPLETED

#### 6.1 Enhanced Permission System

**View-Level Permission Checks:**

- Added comprehensive tag management permission functions in `apps/core/permissions/utils.py`:
  - `can_manage_patient_tags()` - Check if user can add/remove tags
  - `can_add_patient_tag()` - Check if user can add specific tag
  - `can_remove_patient_tag()` - Check if user can remove specific tag
  - `can_view_patient_tags()` - Check if user can view patient tags

**Updated Tag Management Views:**

- `PatientTagAddView` - Uses `can_add_patient_tag()` with detailed validation
- `PatientTagRemoveView` - Uses `can_remove_patient_tag()` for secure removal
- `PatientTagRemoveAllView` - Uses `can_manage_patient_tags()` for bulk operations
- `PatientTagsAPIView` - Uses `can_view_patient_tags()` with permission context

#### 6.2 Template-Level Permission Integration

**Permission Template Tags:**

- Added template tags in `apps/core/templatetags/permission_tags.py`:
  - `can_user_manage_patient_tags` - Template tag for management permissions
  - `can_user_view_patient_tags` - Template tag for viewing permissions
  - `can_manage_tags` - Filter for general tag management capability
  - `tag_permissions_context` - Inclusion tag for permission contexts

**Enhanced Templates:**

- Updated `tag_management.html` with permission-based rendering
- Show/hide tag management buttons based on permissions
- Display permission status to users with graceful fallbacks
- JavaScript integration with permission checks

#### 6.3 Event-Based Audit Trail (MAJOR IMPROVEMENT)

**Replaced Separate Audit System with Event Timeline Integration:**

Instead of creating a separate `PatientTagAuditLog` model, integrated tag tracking into the existing Event system for better user experience and consistency.

**Added Tag Event Types to Event Model:**

- `TAG_ADDED_EVENT (20)`: "Tag Adicionada" with badge class `bg-success` and icon `bi-tag-fill`
- `TAG_REMOVED_EVENT (21)`: "Tag Removida" with badge class `bg-warning` and icon `bi-tag`
- `TAG_BULK_REMOVE_EVENT (22)`: "Tags Removidas em Lote" with badge class `bg-danger` and icon `bi-tags`

**Created Tag Event Models:**

- `TagAddedEvent`: Tracks individual tag additions with tag name, color, and notes
- `TagRemovedEvent`: Tracks individual tag removals with original tag information
- `TagBulkRemoveEvent`: Tracks bulk tag removal operations with count and tag names list

**Timeline Integration:**

- All tag operations now appear in the unified patient timeline
- Tag events display alongside other patient activities (status changes, daily notes, etc.)
- Users see tag history in the same place they look for all patient activities
- Eliminates confusion from separate audit systems

**Updated Tag Management Views:**

- `PatientTagAddView`: Creates `TagAddedEvent` in timeline with full context
- `PatientTagRemoveView`: Creates `TagRemovedEvent` in timeline with tag details
- `PatientTagRemoveAllView`: Creates `TagBulkRemoveEvent` with tag count and names

**Benefits Achieved:**

- **Unified Timeline**: All patient activities in one chronological view
- **Better UX**: Users know to check patient timeline for all history
- **Consistent Architecture**: Leverages existing Event infrastructure
- **Rich Context**: Tag events include full metadata and styling for timeline display
- **No User Confusion**: Single location for all patient activity history

#### 6.4 Testing and Validation

**Comprehensive Testing Completed:**

- ✅ Permission functions work correctly with various user types
- ✅ Template tags render properly with permission context  
- ✅ Event-based audit logging captures operations with full metadata
- ✅ Views enforce permissions and return appropriate responses
- ✅ Anonymous users are properly denied access
- ✅ Real tag operations create appropriate timeline entries
- ✅ Timeline integration displays tag events alongside other activities

**Security Features:**

- Role-based access control with `patients.change_patient` permission requirement
- Comprehensive audit trail via Event system with user and timestamp logging
- Permission context returned to frontend for dynamic behavior
- Secure API responses with proper error handling

### Phase 7: Testing and Validation

#### 7.1 Form Testing Updates

- **Update existing tests** for PatientForm to exclude tag functionality
- **Verify form validation** still works without tag fields
- **Test form submission** creates patients without tags

#### 7.2 Tag Management Testing

- **Unit tests** for new tag management views
- **Integration tests** for tag operations
- **Permission tests** for access control
- **JavaScript tests** for frontend functionality

#### 7.3 User Experience Testing

- **Navigation flow** from forms to detail page for tag management
- **Tag visualization** with colors and styling
- **Error handling** for invalid operations
- **Performance** with large numbers of tags

## Benefits Expected

### Development Benefits

- **Cleaner separation** of personal vs medical data
- **Consistent patterns** with status management
- **Easier maintenance** of forms and tag logic
- **Better testability** with focused responsibilities

### User Experience Benefits

- **Faster patient registration** without tag selection overhead
- **Contextual tag management** alongside patient care information
- **Immediate feedback** for tag operations
- **Intuitive workflow** matching medical staff expectations

### Future Extensibility

- **Tag bulk operations** easier to implement
- **Tag analytics** and reporting capabilities
- **Tag automation** rules based on patient data
- **Advanced tag filtering** and search features

## Migration Considerations

### Backward Compatibility

- **Existing tag data** remains unchanged
- **No database migrations** required
- **Gradual rollout** possible by feature flags

### Training Requirements

- **Staff notification** about new tag management location
- **Documentation updates** for user guides
- **Admin training** for new tag management interface

### Rollback Plan

- **Keep old form logic** in version control
- **Feature toggle** for new vs old tag management
- **Database rollback** not required (no schema changes)

## Implementation Timeline

1. **Phase 1-2** (1-2 days): Remove tags from forms, design interface
2. **Phase 3-4** (2-3 days): Implement backend views and frontend components
3. **Phase 5-6** (1-2 days): Template tags and permissions
4. **Phase 7** (1-2 days): Testing and validation
5. **Deployment** (1 day): Production rollout and monitoring

**Total Estimated Time: 5-10 days**

## Conclusion

This refactor will create a cleaner, more maintainable patient management system with better user experience and consistent patterns throughout the application. The separation of personal data (forms) from medical data (detail page) aligns with medical workflow expectations and provides a foundation for future enhancements.
