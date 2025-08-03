# Ward Patient Map Filtering Refactor Plan

## Overview

This plan refactors the ward patient map filtering system from auto-updating JavaScript-based filtering to a form-based server-side filtering approach, similar to the patient list page. This eliminates race conditions and provides a more reliable user experience.

## Current State Analysis

- **Current System**: Auto-updating JavaScript filtering with race conditions
- **Target System**: Form-based server-side filtering like patient_list.html
- **Key Files to Modify**:
  - `apps/patients/templates/patients/ward_patient_map.html`
  - `apps/patients/views.py` (ward_patient_map view)
  - `static/js/ward_patient_map.js` (to remove auto-update logic)

## Phase 1: Backend View Refactoring

### 1.1 Update ward_patient_map View

**File**: `apps/patients/views.py`

- [x] Add GET parameter handling for:
  - `q` (search query for patient name or bed)
  - `ward` (ward filter)
  - `tag` (tag filter)
- [x] Implement server-side filtering logic
- [x] Update context data to include filtered results
- [x] Add active filters to context for badge display
- [x] Maintain backward compatibility with existing data structure

### 1.2 Update URL Parameters

**File**: `apps/patients/views.py`

- [x] Parse query parameters from request.GET
- [x] Build filter queryset based on parameters
- [x] Handle empty/missing parameters gracefully
- [x] Preserve existing ward_data structure while applying filters

## Phase 2: Template Structure Refactoring

### 2.1 Replace Filter Section

**File**: `apps/patients/templates/patients/ward_patient_map.html`

- [x] Replace current filter inputs with form-based approach
- [x] Wrap filters in `<form method="get">`
- [x] Add proper name attributes to form inputs
- [x] Add search/submit button
- [x] Add clear filters button

### 2.2 Add Active Filter Badges

**File**: `apps/patients/templates/patients/ward_patient_map.html`

- [x] Create filter summary section below form
- [x] Add badges for active filters with removal links
- [x] Style badges consistently with patient_list.html
- [x] Handle multiple active filters

### 2.3 Update Form Fields

**Current Fields** → **New Structure**:

- Search input: `id="patient-search"` → `name="q"`
- Ward select: `id="ward-filter"` → `name="ward"`
- Tag select: `id="tag-filter"` → `name="tag"`

## Phase 3: JavaScript Cleanup

### 3.1 Remove Auto-Update Logic

**File**: `static/js/ward_patient_map.js`

- [x] Remove event listeners for filter changes
- [x] Remove auto-update AJAX calls
- [x] Remove filter summary update functions
- [x] Remove search results display logic
- [x] Keep expand/collapse and refresh functionality

### 3.2 Simplify JavaScript

**File**: `static/js/ward_patient_map.js`

- [x] Remove filter-related functions
- [x] Keep only tree view controls (expand/collapse)
- [x] Keep refresh button functionality
- [x] Remove unused variables and functions

## Phase 4: Styling and UX Updates

### 4.1 Form Styling

**File**: `apps/patients/templates/patients/ward_patient_map.html`

- [x] Apply consistent styling with patient_list.html
- [x] Use Bootstrap form classes
- [x] Ensure responsive design
- [x] Match button styling to patient_list.html

### 4.2 Filter Badge Styling

**File**: `apps/patients/templates/patients/ward_patient_map.html`

- [x] Copy badge styling from patient_list.html
- [x] Ensure consistent colors and spacing
- [x] Add hover effects for removal links
- [x] Ensure accessibility

## Phase 5: Testing and Validation

### 5.1 Backend Testing

- [x] Test filter combinations
- [x] Test empty parameter handling
- [x] Test invalid parameter handling
- [x] Verify performance with large datasets

### 5.2 Frontend Testing

- [x] Test form submission
- [x] Test filter removal via badges
- [x] Test clear all filters
- [x] Test responsive design
- [x] Test keyboard navigation

### 5.3 Edge Cases

- [x] Test with no wards
- [x] Test with no patients
- [x] Test with no tags
- [x] Test special characters in search

## Implementation Steps by File

### apps/patients/views.py

```python
# Add to ward_patient_map view:
def ward_patient_map(request):
    # Current code...

    # Add filter handling
    search_query = request.GET.get('q', '')
    selected_ward = request.GET.get('ward', '')
    selected_tag = request.GET.get('tag', '')

    # Apply filters to queryset
    patients = patients.filter(...)  # Apply filters based on parameters

    # Add active filters to context
    context['active_filters'] = {
        'q': search_query,
        'ward': selected_ward,
        'tag': selected_tag,
    }

    # Filter ward_data based on parameters
    # ...
```

### apps/patients/templates/patients/ward_patient_map.html

```html
<!-- Replace current filter section -->
<div class="card">
  <div class="card-body">
    <form method="get" class="row g-3">
      <!-- Search -->
      <div class="col-md-3">
        <label for="search" class="form-label">
          <i class="bi bi-search me-1"></i>Buscar Paciente
        </label>
        <input type="text"
               class="form-control"
               id="search"
               name="q"
               value="{{ request.GET.q|default:'' }}"
               placeholder="Nome do paciente ou número do leito...">
      </div>

      <!-- Ward -->
      <div class="col-md-2">
        <label for="ward" class="form-label">Ala</label>
        <select class="form-select" id="ward" name="ward">
          <option value="">Todas as Alas</option>
          {% for ward_info in ward_data %}
            <option value="{{ ward_info.ward.id }}"
                    {% if request.GET.ward == ward_info.ward.id|stringformat:"s" %}selected{% endif %}>
              {{ ward_info.ward.abbreviation }} - {{ ward_info.ward.name }}
            </option>
          {% endfor %}
        </select>
      </div>

      <!-- Tag -->
      <div class="col-md-2">
        <label for="tag" class="form-label">Tag</label>
        <select class="form-select" id="tag" name="tag">
          <option value="">Todas as Tags</option>
          {% for tag in available_tags %}
            <option value="{{ tag.id }}"
                    {% if request.GET.tag == tag.id|stringformat:"s" %}selected{% endif %}
                    style="background-color: {{ tag.color }}; color: white;">
              {{ tag.name }}
            </option>
          {% endfor %}
        </select>
      </div>

      <!-- Actions -->
      <div class="col-md-3 d-flex align-items-end">
        <div class="btn-group w-100" role="group">
          <button type="submit" class="btn btn-medical-outline-primary">
            <i class="bi bi-search"></i>
          </button>
          <a href="{% url 'apps.patients:ward_patient_map' %}"
             class="btn btn-outline-secondary"
             title="Limpar filtros">
            <i class="bi bi-x-circle"></i>
          </a>
        </div>
      </div>
    </form>

    <!-- Active Filters -->
    {% if request.GET.q or request.GET.ward or request.GET.tag %}
    <div class="mt-3">
      <small class="text-muted">Filtros ativos:</small>
      <div class="d-flex flex-wrap gap-2 mt-1">
        <!-- Filter badges -->
      </div>
    </div>
    {% endif %}
  </div>
</div>
```

### static/js/ward_patient_map.js

```javascript
// Remove these sections:
- Event listeners for filter changes
- Auto-update functions
- Filter summary updates
- AJAX calls for filtering

// Keep these sections:
- Expand/collapse functionality
- Refresh button functionality
- Tree view controls
```

## Rollback Plan

If issues arise, the rollback procedure:

1. Revert view changes in `views.py`
2. Restore original template from git
3. Restore original JavaScript file
4. Test basic functionality

## Success Criteria

- [x] No JavaScript errors in console
- [x] Filters apply correctly via URL parameters
- [x] Active filter badges display and work correctly
- [x] Clear filters button works
- [x] Responsive design maintained
- [x] No race conditions or performance issues
- [x] All existing functionality preserved (expand/collapse, refresh)

## Testing Checklist

- [x] Single filter application
- [x] Multiple filter combinations
- [x] Filter removal via badges
- [x] Clear all filters
- [x] URL parameter persistence
- [x] Empty search results handling
- [x] Special characters in search
- [x] Mobile responsiveness
- [x] Keyboard navigation
- [x] Screen reader compatibility

## Post-Implementation Review

After implementation:

1. Monitor for any user-reported issues
2. Check server logs for errors
3. Review performance metrics
4. Gather user feedback on new filtering experience

