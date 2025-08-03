# Tag Search and Filtering Implementation Plan

## Overview

Implement comprehensive tag search and filtering functionality across both the Patient List and Ward Patient Map views. This will allow users to search and filter patients based on their assigned tags, enhancing the usability and efficiency of patient management.

## Current State Analysis

### What Exists
- ✅ Complete tag management system (AllowedTag, Tag models)
- ✅ Tag assignment/removal functionality
- ✅ Tag display in patient list and ward map
- ✅ Basic patient search (name, CPF, health card, etc.)
- ✅ Status and ward filtering

### What's Missing
- ❌ Tag filtering in PatientListView
- ❌ Tag filter dropdown in patient list template
- ❌ Tag filtering in WardPatientMapView
- ❌ Tag filter dropdown in ward map template
- ❌ JavaScript implementation of filterByTag() method

## Implementation Phases

---

## Phase 1: Backend Tag Filtering (Patient List) ✅ COMPLETED

**Goal**: Add tag filtering capability to the PatientListView backend

### Step 1.1: Update PatientListView.get_queryset()

**File**: `apps/patients/views.py`

```python
# Add after existing filters in PatientListView.get_queryset()

# Tag filter
tag_filter = self.request.GET.get('tag')
if tag_filter:
    try:
        tag_id = int(tag_filter)
        # Filter patients who have this specific tag assigned
        queryset = queryset.filter(
            patient_tags__allowed_tag_id=tag_id
        ).distinct()
    except (ValueError, TypeError):
        pass
```

### Step 1.2: Update get_context_data()

**File**: `apps/patients/views.py`

```python
# Add to PatientListView.get_context_data()
context['tag_filter'] = self.request.GET.get('tag', '')
context['available_tags'] = AllowedTag.objects.filter(
    is_active=True,
    tag_instances__isnull=False  # Only tags that are actually used
).distinct().order_by('name')
```

### Step 1.3: Import Requirements

```python
# Add to imports at top of views.py
from django.db.models import Exists, OuterRef
```

### Considerations
- Use `.distinct()` to avoid duplicate patients when multiple tags match
- Only show tags that are actually assigned to patients
- Handle invalid tag IDs gracefully
- Maintain existing filter combinations

---

## Phase 2: Frontend Tag Filtering (Patient List) ✅ COMPLETED

**Goal**: Add tag filter dropdown to patient list template

### Step 2.1: Add Tag Filter Dropdown

**File**: `apps/patients/templates/patients/patient_list.html`

```html
<!-- Add after Status Filter section -->
<!-- Tag Filter -->
<div class="col-md-3">
  <label for="tag" class="form-label">
    <i class="bi bi-tags me-2"></i>Tag
  </label>
  <select class="form-select" id="tag" name="tag">
    <option value="">Todas as tags</option>
    {% for tag in available_tags %}
      <option value="{{ tag.id }}" 
              {% if request.GET.tag == tag.id|stringformat:"s" %}selected{% endif %}
              style="background-color: {{ tag.color }}; color: white;">
        {{ tag.name }}
      </option>
    {% endfor %}
  </select>
</div>
```

### Step 2.2: Update Actions Column Width

```html
<!-- Update actions column to accommodate new filter -->
<div class="col-md-3 d-flex align-items-end">
```

### Step 2.3: Update Active Filters Display

```html
<!-- Add to active filters section -->
{% if request.GET.tag %}
  <span class="badge bg-medical-teal">
    Tag: {{ available_tags|get_item:request.GET.tag.0.name }}
    <a href="?{% if request.GET.q %}q={{ request.GET.q }}{% endif %}{% if request.GET.status %}&status={{ request.GET.status }}{% endif %}" 
       class="text-white text-decoration-none ms-1">×</a>
  </span>
{% endif %}
```

### Step 2.4: Update Clear Filters Link

```html
<!-- Update form preservation in clear filters links -->
{% if request.GET.q or request.GET.status or request.GET.tag %}
```

### Considerations
- Use tag colors in dropdown for visual consistency
- Preserve other filter parameters when removing tag filter
- Update column layout to accommodate new filter
- Ensure proper form parameter handling

---

## Phase 3: Backend Support (Ward Map Tag Filtering) ✅ COMPLETED

**Goal**: Add tag filtering support to WardPatientMapView

### Step 3.1: Update WardPatientMapView.get_context_data()

**File**: `apps/patients/views.py`

```python
# Add to WardPatientMapView.get_context_data()
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    
    # Get filter parameters
    tag_filter = self.request.GET.get('tag')
    
    # Get all active wards
    wards = Ward.objects.filter(is_active=True).order_by('name')
    
    ward_data = []
    total_patients = 0
    
    for ward in wards:
        # Base queryset for patients in this ward
        patients_qs = Patient.objects.filter(
            ward=ward,
            status__in=[Patient.Status.INPATIENT, Patient.Status.EMERGENCY],
            is_deleted=False
        ).select_related('ward').prefetch_related('patient_tags__allowed_tag')
        
        # Apply tag filter if specified
        if tag_filter:
            try:
                tag_id = int(tag_filter)
                patients_qs = patients_qs.filter(
                    patient_tags__allowed_tag_id=tag_id
                ).distinct()
            except (ValueError, TypeError):
                pass
        
        patients = patients_qs.order_by('bed', 'name')
        
        # ... rest of existing logic
    
    # Add tag context
    context['available_tags'] = AllowedTag.objects.filter(
        is_active=True,
        tag_instances__patient__status__in=[
            Patient.Status.INPATIENT, 
            Patient.Status.EMERGENCY
        ]
    ).distinct().order_by('name')
    
    context['selected_tag'] = tag_filter
    
    return context
```

### Considerations
- Apply tag filter before building ward patient lists
- Only include tags that are assigned to current inpatients/emergency patients
- Maintain existing ward capacity calculations
- Preserve other filter parameters

---

## Phase 4: Frontend Tag Filtering (Ward Map) ✅ COMPLETED

**Goal**: Add tag filter dropdown and implement JavaScript filtering

### Step 4.1: Add Tag Filter to Template

**File**: `apps/patients/templates/patients/ward_patient_map.html`

```html
<!-- Add after Ward Filter section -->
<!-- Tag Filter -->
<div class="col-md-2">
  <label for="tag-filter" class="form-label">Tag</label>
  <select class="form-select" id="tag-filter">
    <option value="">Todas as Tags</option>
    {% for tag in available_tags %}
      <option value="{{ tag.id }}" 
              style="background-color: {{ tag.color }}; color: white;"
              {% if selected_tag == tag.id|stringformat:"s" %}selected{% endif %}>
        {{ tag.name }}
      </option>
    {% endfor %}
  </select>
</div>
```

### Step 4.2: Update Column Layout

```html
<!-- Adjust existing columns -->
<!-- Search: col-md-4 → col-md-3 -->
<!-- Status: col-md-2 → col-md-2 -->
<!-- Ward: col-md-3 → col-md-2 -->
<!-- Tag: col-md-2 (new) -->
<!-- Controls: col-md-3 → col-md-3 -->
```

### Step 4.3: Implement filterByTag() JavaScript Method

**File**: `assets/js/ward_patient_map.js`

```javascript
filterByTag(tagId) {
  const patients = document.querySelectorAll('.patient-item');
  
  patients.forEach(patient => {
    if (tagId === '') {
      // Show all patients
      patient.classList.remove('filtered-out');
      return;
    }
    
    // Check if patient has the selected tag
    const patientTags = patient.querySelectorAll('.badge[style*="background-color"]');
    let hasTag = false;
    
    patientTags.forEach(tagBadge => {
      // Get tag ID from data attribute or text matching
      const tagName = tagBadge.textContent.trim();
      const tagOption = document.querySelector(`#tag-filter option[value="${tagId}"]`);
      
      if (tagOption && tagOption.textContent.trim() === tagName) {
        hasTag = true;
      }
    });
    
    if (hasTag) {
      patient.classList.remove('filtered-out');
    } else {
      patient.classList.add('filtered-out');
    }
  });
  
  this.updateWardVisibility();
}
```

### Step 4.4: Enhanced Implementation with Data Attributes

**Alternative approach for more robust tag matching:**

**Template Update**:
```html
<!-- Add data attributes to patient items -->
<div class="patient-item p-3 mb-2 bg-white border rounded" 
     data-patient-tags="{% for tag in patient_info.tags %}{{ tag.allowed_tag.id }}{% if not forloop.last %},{% endif %}{% endfor %}">
```

**JavaScript Update**:
```javascript
filterByTag(tagId) {
  const patients = document.querySelectorAll('.patient-item');
  
  patients.forEach(patient => {
    if (tagId === '') {
      patient.classList.remove('filtered-out');
      return;
    }
    
    const patientTagIds = patient.dataset.patientTags.split(',').filter(id => id);
    const hasTag = patientTagIds.includes(tagId);
    
    if (hasTag) {
      patient.classList.remove('filtered-out');
    } else {
      patient.classList.add('filtered-out');
    }
  });
  
  this.updateWardVisibility();
}
```

### Step 4.5: Update setupFilters() Method

```javascript
setupFilters() {
  // Existing filters...
  
  // Tag filter
  const tagFilter = document.getElementById('tag-filter');
  tagFilter?.addEventListener('change', (e) => {
    this.filterByTag(e.target.value);
  });
  
  // Update URL parameters to maintain state
  tagFilter?.addEventListener('change', (e) => {
    const url = new URL(window.location);
    if (e.target.value) {
      url.searchParams.set('tag', e.target.value);
    } else {
      url.searchParams.delete('tag');
    }
    window.history.replaceState({}, '', url);
  });
}
```

---

## Phase 5: Enhanced Search Integration

**Goal**: Integrate tag search with text search functionality

### Step 5.1: Enhanced PatientListView Search

**File**: `apps/patients/views.py`

```python
# Enhanced search to include tag names
search_query = self.request.GET.get('search', '').strip()
if search_query:
    queryset = queryset.filter(
        Q(name__icontains=search_query) |
        Q(healthcard_number__icontains=search_query) |
        Q(id_number__icontains=search_query) |
        Q(fiscal_number__icontains=search_query) |
        Q(current_record_number__icontains=search_query) |
        Q(record_numbers__record_number__icontains=search_query) |
        Q(patient_tags__allowed_tag__name__icontains=search_query)  # NEW: Tag name search
    ).distinct()
```

### Step 5.2: Update Ward Map Search

**File**: `assets/js/ward_patient_map.js`

```javascript
filterPatients(searchTerm) {
  const wardBranches = document.querySelectorAll('.ward-branch');
  
  wardBranches.forEach(branch => {
    const patients = branch.querySelectorAll('.patient-item');
    let hasVisiblePatients = false;

    patients.forEach(patient => {
      const patientName = patient.querySelector('span:nth-of-type(3)')?.textContent?.toLowerCase() || '';
      const bedNumber = patient.querySelector('strong')?.textContent?.toLowerCase() || '';
      
      // NEW: Search in tag names
      const tagElements = patient.querySelectorAll('.badge[style*="background-color"]');
      const tagNames = Array.from(tagElements).map(tag => 
        tag.textContent.trim().toLowerCase()
      ).join(' ');
      
      if (searchTerm === '' || 
          patientName.includes(searchTerm) || 
          bedNumber.includes(searchTerm) ||
          tagNames.includes(searchTerm)) {  // NEW: Tag search
        patient.style.display = 'block';
        hasVisiblePatients = true;
      } else {
        patient.style.display = 'none';
      }
    });
    
    // ... rest of existing logic
  });
}
```

---

## Phase 6: Basic Optimization and Polish

**Goal**: Simple optimizations and user experience polish appropriate for small-to-medium scale

### Step 6.1: Keep Existing Query Optimization

```python
# The existing prefetch_related in PatientListView is sufficient
queryset = queryset.select_related('created_by').prefetch_related('patient_tags__allowed_tag')

# The simple .distinct() approach is fine for this scale
tag_filter = self.request.GET.get('tag')
if tag_filter:
    try:
        tag_id = int(tag_filter)
        queryset = queryset.filter(
            patient_tags__allowed_tag_id=tag_id
        ).distinct()
    except (ValueError, TypeError):
        pass
```

### Step 6.2: Simple Frontend Enhancements

```javascript
// Add loading state for better UX (no complex caching needed)
filterByTag(tagId) {
  // Show loading state for larger filter operations
  const patients = document.querySelectorAll('.patient-item');
  
  if (patients.length > 50) {
    this.showFilteringState(true);
  }
  
  // Existing filtering logic...
  
  if (patients.length > 50) {
    setTimeout(() => this.showFilteringState(false), 100);
  }
}

showFilteringState(show) {
  const wardTree = document.querySelector('.ward-tree');
  if (show) {
    wardTree.style.opacity = '0.7';
  } else {
    wardTree.style.opacity = '1';
  }
}
```

### Step 6.3: User Experience Polish

```javascript
// Add filter result summary
updateFilterSummary() {
  const visiblePatients = document.querySelectorAll('.patient-item:not(.filtered-out):not([style*="none"])');
  const totalPatients = document.querySelectorAll('.patient-item').length;
  
  const summaryElement = document.getElementById('filter-summary');
  if (summaryElement && visiblePatients.length !== totalPatients) {
    summaryElement.innerHTML = `
      <small class="text-muted">
        Mostrando ${visiblePatients.length} de ${totalPatients} pacientes
      </small>
    `;
  } else if (summaryElement) {
    summaryElement.innerHTML = '';
  }
}
```

---

## Phase 7: Testing and Validation

**Goal**: Comprehensive testing of tag filtering functionality

### Step 7.1: Backend Testing

**File**: `apps/patients/tests/test_tag_filtering.py`

```python
class TagFilteringTests(TestCase):
    def setUp(self):
        # Create test data: patients, tags, assignments
        pass
    
    def test_patient_list_tag_filtering(self):
        """Test PatientListView tag filtering"""
        pass
    
    def test_ward_map_tag_filtering(self):
        """Test WardPatientMapView tag filtering"""
        pass
    
    def test_combined_filters(self):
        """Test tag filter with other filters"""
        pass
    
    def test_search_with_tag_names(self):
        """Test text search including tag names"""
        pass
```

### Step 7.2: Frontend Testing

- Test tag filter dropdown functionality
- Test JavaScript filterByTag() method
- Test filter combinations
- Test URL parameter preservation
- Test responsive design on mobile

### Step 7.3: Performance Testing

- Test with large numbers of patients and tags
- Measure database query performance
- Test JavaScript performance with many DOM elements

---

## Implementation Considerations

### Database Performance
- Use existing `prefetch_related()` for tag relationships (already implemented)
- Simple `distinct()` queries are sufficient for this scale (~100-4000 patients)
- No additional database indexes needed for tag filtering at this volume

### User Experience
- Show tag colors in filter dropdowns
- Preserve filter state in URLs
- Provide clear visual feedback for filtered results
- Handle empty states gracefully

### Accessibility
- Ensure proper ARIA labels for filter dropdowns
- Maintain keyboard navigation
- Provide screen reader friendly filter descriptions

### Error Handling
- Handle invalid tag IDs gracefully
- Provide fallback behavior for JavaScript failures
- Show user-friendly error messages

### Mobile Responsiveness
- Ensure filter dropdowns work well on mobile
- Consider collapsible filter sections for small screens
- Test touch interactions

---

## Success Criteria

### Functional Requirements
- ✅ Users can filter patients by tags in patient list
- ✅ Users can filter patients by tags in ward map
- ✅ Tag names are searchable in text search
- ✅ Filter combinations work correctly
- ✅ Filter state is preserved in URLs

### Performance Requirements
- ✅ Tag filtering queries execute in < 500ms
- ✅ JavaScript filtering is smooth on mobile devices
- ✅ Page load time remains acceptable with tag data

### Usability Requirements
- ✅ Filter interface is intuitive and discoverable
- ✅ Tag colors are preserved in filter dropdowns
- ✅ Clear visual feedback for filtered results
- ✅ Easy to clear/reset filters

---

## Files to Modify

### Backend Files
- `apps/patients/views.py` - PatientListView and WardPatientMapView
- `apps/patients/tests/test_tag_filtering.py` - New test file

### Frontend Files
- `apps/patients/templates/patients/patient_list.html` - Add tag filter
- `apps/patients/templates/patients/ward_patient_map.html` - Add tag filter
- `assets/js/ward_patient_map.js` - Implement filterByTag method

### Build Files
- No webpack changes needed (existing files)

---

## Rollback Plan

If issues arise:
1. Remove tag filter from templates (UI changes)
2. Remove tag filtering logic from views (backend changes)
3. Remove filterByTag JavaScript method
4. Test that existing functionality still works
5. Deploy rollback if necessary

Each phase can be implemented and tested independently, allowing for safe incremental deployment.