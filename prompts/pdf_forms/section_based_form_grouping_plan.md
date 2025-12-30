# PDF Forms Section-Based Grouping Implementation Plan

## Overview

This document outlines the detailed implementation plan for adding section-based field grouping to PDF forms, combining **Option 1 (Section-Based Configuration)** with **Option 4 (Accordion Interface)**.

### Goals

- Allow admin users to organize form fields into logical sections
- Improve form filling UX with collapsible accordion sections
- Maintain backward compatibility with existing forms
- Provide intuitive section management in the admin configurator

### Architecture Changes

- Extend JSON field configuration to include sections
- Enhance form generator to handle sectioned fields
- Update admin configurator with section management UI
- Implement accordion-based form rendering

---

## Phase 1: Data Model & Configuration Updates

### 1.1 Update Field Configuration Schema

**File:** `apps/pdf_forms/models.py` (documentation update)

Update the `form_fields` JSONField to support the new structure:

```json
{
  "sections": {
    "patient_info": {
      "label": "Informações do Paciente",
      "description": "Dados básicos e informações de contato do paciente",
      "order": 1,
      "collapsed": false,
      "icon": "bi-person"
    },
    "procedure_details": {
      "label": "Detalhes do Procedimento", 
      "description": "Informações específicas sobre o procedimento realizado",
      "order": 2,
      "collapsed": true,
      "icon": "bi-clipboard-pulse"
    },
    "medical_history": {
      "label": "Histórico Médico",
      "description": "Antecedentes médicos relevantes",
      "order": 3,
      "collapsed": true,
      "icon": "bi-journal-medical"
    }
  },
  "fields": {
    "patient_name": {
      "type": "text",
      "label": "Nome do Paciente",
      "section": "patient_info",
      "field_order": 1,
      "x": 2.0, "y": 3.0, "width": 6.0, "height": 0.7,
      "font_size": 12,
      "required": true,
      "patient_field_mapping": "name"
    },
    "patient_birth_date": {
      "type": "date",
      "label": "Data de Nascimento", 
      "section": "patient_info",
      "field_order": 2,
      "x": 2.0, "y": 4.0, "width": 4.0, "height": 0.7,
      "font_size": 12,
      "required": true,
      "patient_field_mapping": "birth_date"
    },
    "procedure_name": {
      "type": "text",
      "label": "Nome do Procedimento",
      "section": "procedure_details", 
      "field_order": 1,
      "x": 2.0, "y": 8.0, "width": 8.0, "height": 0.7,
      "font_size": 12,
      "required": true
    }
  }
}
```

### 1.2 Add Configuration Validation

**File:** `apps/pdf_forms/security.py`

Add validation for the new section structure:

```python
@staticmethod
def validate_section_configuration(sections_config):
    """Validate sections configuration structure."""
    # Validate section properties
    # Check for required fields: label, order
    # Validate order uniqueness
    # Sanitize section keys and labels
```

### 1.3 Create Migration (if needed)

**File:** `apps/pdf_forms/migrations/000X_add_section_support.py`

Add data migration to handle existing forms without breaking them.

---

## Phase 2: Form Generator Enhancements

### 2.1 Update DynamicFormGenerator

**File:** `apps/pdf_forms/services/form_generator.py`

#### 2.1.1 Add Section Processing Methods

```python
def _organize_sections(self, sections_config, field_configs):
    """
    Organize sections and fields into structured format.
    
    Returns:
    {
        'sections': {
            'section_key': {
                'info': section_metadata,
                'fields': [list_of_django_fields]
            }
        },
        'unsectioned_fields': [fields_without_section]
    }
    """

def _sort_sections_by_order(self, sections):
    """Sort sections by their order property."""

def _sort_fields_within_section(self, fields, field_configs):
    """Sort fields within a section by field_order property."""

def _get_section_field_count(self, section_key, field_configs):
    """Count fields assigned to a specific section."""
```

#### 2.1.2 Modify generate_form_class Method

```python
def generate_form_class(self, pdf_template, patient=None):
    """
    Enhanced to handle sections:
    1. Process sections configuration
    2. Group fields by sections
    3. Add section metadata to form class
    4. Maintain backward compatibility
    """
    
    # New logic:
    # - Extract sections and fields from config
    # - Group fields by section
    # - Sort sections and fields
    # - Add metadata to form class
    # - Handle unsectioned fields
```

#### 2.1.3 Add Form Class Metadata

```python
# Add these properties to the dynamically created form class:
form_class._sections_metadata = organized_sections
form_class._has_sections = bool(sections_config)
form_class._unsectioned_fields = unsectioned_fields
```

### 2.2 Create Section Helper Utilities

**File:** `apps/pdf_forms/services/section_utils.py` (new file)

```python
class SectionUtils:
    """Utilities for handling form sections."""
    
    @staticmethod
    def get_default_section_config():
        """Return default section configuration."""
    
    @staticmethod
    def migrate_unsectioned_form(field_config):
        """Convert old format to new sectioned format."""
    
    @staticmethod
    def validate_section_assignment(sections, fields):
        """Validate that field sections exist."""
    
    @staticmethod
    def get_section_icons():
        """Return available Bootstrap icons for sections."""
```

---

## Phase 3: Template Updates

### 3.1 Update Form Rendering Template

**File:** `apps/pdf_forms/templates/pdf_forms/form_fill.html`

#### 3.1.1 Replace Current Form Rendering

Replace the current field loop with accordion-based rendering:

```html
<!-- Replace current form rendering section -->
<div class="accordion" id="form-sections">
  {% if form._has_sections %}
    <!-- Render sectioned fields -->
    {% for section_key, section_data in form._sections_metadata.sections.items %}
    <div class="accordion-item">
      <h2 class="accordion-header" id="heading-{{ section_key }}">
        <button class="accordion-button {% if section_data.info.collapsed %}collapsed{% endif %}" 
                type="button" data-bs-toggle="collapse" 
                data-bs-target="#collapse-{{ section_key }}">
          {% if section_data.info.icon %}
          <i class="{{ section_data.info.icon }} me-2"></i>
          {% endif %}
          {{ section_data.info.label }}
          <span class="badge bg-primary ms-auto me-2">
            {{ section_data.fields|length }}
          </span>
        </button>
      </h2>
      <div id="collapse-{{ section_key }}" 
           class="accordion-collapse collapse {% if not section_data.info.collapsed %}show{% endif %}"
           data-bs-parent="#form-sections">
        <div class="accordion-body">
          {% if section_data.info.description %}
          <p class="text-muted mb-3">{{ section_data.info.description }}</p>
          {% endif %}
          <div class="row">
            {% for field_name in section_data.fields %}
              {% with field=form|lookup:field_name %}
              <div class="col-md-6 mb-3">
                <!-- Field rendering logic -->
              </div>
              {% endwith %}
            {% endfor %}
          </div>
        </div>
      </div>
    </div>
    {% endfor %}
    
    <!-- Render unsectioned fields if any -->
    {% if form._unsectioned_fields %}
    <div class="accordion-item">
      <h2 class="accordion-header" id="heading-other">
        <button class="accordion-button collapsed" type="button" 
                data-bs-toggle="collapse" data-bs-target="#collapse-other">
          <i class="bi-gear me-2"></i>
          Outros Campos
          <span class="badge bg-secondary ms-auto me-2">
            {{ form._unsectioned_fields|length }}
          </span>
        </button>
      </h2>
      <div id="collapse-other" class="accordion-collapse collapse" 
           data-bs-parent="#form-sections">
        <div class="accordion-body">
          <div class="row">
            {% for field_name in form._unsectioned_fields %}
              {% with field=form|lookup:field_name %}
              <div class="col-md-6 mb-3">
                <!-- Field rendering logic -->
              </div>
              {% endwith %}
            {% endfor %}
          </div>
        </div>
      </div>
    </div>
    {% endif %}
    
  {% else %}
    <!-- Fallback: render all fields without sections (backward compatibility) -->
    <div class="row">
      {% for field in form %}
      <div class="col-md-6 mb-3">
        <!-- Current field rendering logic -->
      </div>
      {% endfor %}
    </div>
  {% endif %}
</div>
```

#### 3.1.2 Add Template Filters/Tags

**File:** `apps/pdf_forms/templatetags/pdf_forms_tags.py`

```python
@register.filter
def lookup(form, field_name):
    """Lookup form field by name."""
    return form[field_name]

@register.inclusion_tag('pdf_forms/partials/form_field.html')
def render_form_field(field):
    """Render a single form field with consistent styling."""
    return {'field': field}
```

### 3.2 Create Form Field Partial Template

**File:** `apps/pdf_forms/templates/pdf_forms/partials/form_field.html` (new file)

```html
<label for="{{ field.id_for_label }}" class="form-label">
  {{ field.label }}
  {% if field.field.required %}
  <span class="text-danger">*</span>
  {% endif %}
</label>

{{ field }}

{% if field.help_text %}
<div class="form-text">{{ field.help_text }}</div>
{% endif %}

{% if field.errors %}
<div class="invalid-feedback d-block">{{ field.errors }}</div>
{% endif %}
```

---

## Phase 4: Admin Configurator Enhancements

### 4.1 Update Admin Interface HTML

**File:** `apps/pdf_forms/templates/admin/pdf_forms/pdfformtemplate/configure_fields.html`

#### 4.1.1 Add Section Management Panel

Add to properties panel:

```html
<!-- Add after the field list -->
<div id="section-management" class="mt-4">
  <h4>Form Sections</h4>
  <div id="sections-list" class="mb-3">
    <!-- Dynamically populated -->
  </div>
  <button type="button" class="btn btn-outline-primary btn-sm" id="add-section-btn">
    <i class="bi bi-plus"></i> Add Section
  </button>
  <button type="button" class="btn btn-outline-secondary btn-sm" id="reorder-sections-btn">
    <i class="bi bi-arrow-up-down"></i> Reorder
  </button>
</div>

<!-- Section Editor Modal -->
<div class="modal fade" id="sectionModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Section Configuration</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <form id="section-form">
          <div class="mb-3">
            <label for="section-key" class="form-label">Section Key</label>
            <input type="text" class="form-control" id="section-key" required>
            <div class="form-text">Unique identifier (e.g., patient_info)</div>
          </div>
          <div class="mb-3">
            <label for="section-label" class="form-label">Section Label</label>
            <input type="text" class="form-control" id="section-label" required>
            <div class="form-text">Display name (e.g., Patient Information)</div>
          </div>
          <div class="mb-3">
            <label for="section-description" class="form-label">Description</label>
            <textarea class="form-control" id="section-description" rows="2"></textarea>
          </div>
          <div class="mb-3">
            <label for="section-icon" class="form-label">Icon</label>
            <select class="form-control" id="section-icon">
              <option value="">No Icon</option>
              <option value="bi-person">Person</option>
              <option value="bi-clipboard-pulse">Medical</option>
              <option value="bi-journal-medical">History</option>
              <option value="bi-prescription2">Prescription</option>
              <option value="bi-hospital">Hospital</option>
            </select>
          </div>
          <div class="mb-3">
            <label class="form-check-label">
              <input type="checkbox" class="form-check-input" id="section-collapsed">
              Start Collapsed
            </label>
          </div>
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-primary" id="save-section-btn">Save Section</button>
      </div>
    </div>
  </div>
</div>
```

#### 4.1.2 Update Field Properties Panel

Add section assignment to field properties:

```html
<!-- Add to field properties form -->
<div class="form-group">
  <label for="field-section">Section</label>
  <select id="field-section" name="section" class="form-control">
    <option value="">-- No Section --</option>
    <!-- Dynamically populated with available sections -->
  </select>
  <small class="form-text text-muted">
    Assign this field to a form section for better organization
  </small>
</div>

<div class="form-group">
  <label for="field-order">Order within Section</label>
  <input type="number" id="field-order" name="field_order" class="form-control" min="1">
  <small class="form-text text-muted">
    Order of this field within its section (lower numbers appear first)
  </small>
</div>
```

### 4.2 Update JavaScript for Section Management

**File:** `apps/pdf_forms/templates/admin/pdf_forms/pdfformtemplate/configure_fields.html` (JavaScript section)

#### 4.2.1 Add Section Management Variables

```javascript
// Add to global variables
let sections = {};
let editingSectionKey = null;
```

#### 4.2.2 Add Section Management Functions

```javascript
// Section Management Functions
function loadExistingSections() {
  // Load sections from existing config
  // Populate sections list
  // Update field section dropdowns
}

function updateSectionsList() {
  // Render sections list with edit/delete buttons
  // Show field count per section
  // Enable drag-and-drop reordering
}

function showSectionModal(sectionKey = null) {
  // Show modal for creating/editing sections
  // Pre-fill form if editing existing section
}

function saveSectionConfiguration() {
  // Validate section form
  // Add/update section in sections object
  // Refresh sections list and field dropdowns
  // Close modal
}

function deleteSectionWithConfirmation(sectionKey) {
  // Confirm deletion
  // Handle fields assigned to deleted section
  // Remove section and update UI
}

function reorderSections() {
  // Enable drag-and-drop reordering
  // Update section order values
}

function updateFieldSectionDropdown() {
  // Populate section dropdown in field properties
  // Sort by section order
}

function handleFieldSectionChange() {
  // Update field's section assignment
  // Refresh field list grouping
}
```

#### 4.2.3 Update Existing Functions

```javascript
// Modify existing functions
function updateSelectedField() {
  // Add section and field_order handling
  // Existing logic...
}

function updateFieldList() {
  // Group fields by section
  // Show section headers
  // Existing logic...
}

function loadExistingFields() {
  // Load both sections and fields
  // Handle backward compatibility
  // Existing logic...
}

function saveFields() {
  // Save both sections and fields configuration
  // Existing logic...
}
```

---

## Phase 5: CSS & JavaScript Enhancements

### 5.1 Update CSS Styles

**File:** `apps/pdf_forms/static/pdf_forms/css/pdf_forms.css`

```css
/* Section Management Styles */
.section-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    margin-bottom: 5px;
    background: #f8f9fa;
}

.section-item:hover {
    background: #e9ecef;
}

.section-item.dragging {
    opacity: 0.5;
}

.section-info {
    flex: 1;
}

.section-name {
    font-weight: bold;
    color: #495057;
}

.section-field-count {
    font-size: 11px;
    color: #6c757d;
    margin-left: 8px;
}

.section-actions {
    display: flex;
    gap: 5px;
}

.section-actions button {
    padding: 2px 6px;
    font-size: 11px;
    border: none;
    border-radius: 3px;
    cursor: pointer;
}

.section-drag-handle {
    cursor: move;
    color: #6c757d;
    margin-right: 8px;
}

/* Form Section Styles */
.form-section-accordion .accordion-button {
    padding: 1rem 1.25rem;
    font-weight: 500;
}

.form-section-accordion .accordion-button:not(.collapsed) {
    background-color: #e7f3ff;
    border-color: #b3d7ff;
}

.form-section-accordion .accordion-body {
    padding: 1.5rem 1.25rem;
}

.section-description {
    font-style: italic;
    color: #6c757d;
    margin-bottom: 1rem;
}

.section-field-badge {
    font-size: 0.75em;
}

/* Field List Section Grouping */
.field-list-section {
    margin-bottom: 15px;
}

.field-list-section-header {
    background: #f1f3f4;
    padding: 8px 12px;
    font-weight: bold;
    color: #495057;
    border-radius: 4px 4px 0 0;
    font-size: 12px;
}

.field-list-section .field-item {
    margin-left: 10px;
    border-left: 3px solid #007cba;
}

.field-item.no-section {
    border-left: 3px solid #6c757d;
}
```

### 5.2 Update JavaScript Enhancements

**File:** `apps/pdf_forms/static/pdf_forms/js/pdf_forms.js`

```javascript
// Add accordion state management
document.addEventListener('DOMContentLoaded', function() {
    // Existing code...
    
    // Section accordion state persistence
    const accordionButtons = document.querySelectorAll('.accordion-button');
    accordionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const sectionId = this.getAttribute('data-bs-target');
            const isCollapsed = this.classList.contains('collapsed');
            
            // Save state to localStorage
            localStorage.setItem(`pdf-form-section-${sectionId}`, !isCollapsed);
        });
    });
    
    // Restore accordion states on page load
    accordionButtons.forEach(button => {
        const sectionId = button.getAttribute('data-bs-target');
        const savedState = localStorage.getItem(`pdf-form-section-${sectionId}`);
        
        if (savedState === 'false') {
            const target = document.querySelector(sectionId);
            if (target) {
                target.classList.remove('show');
                button.classList.add('collapsed');
            }
        }
    });
});
```

---

## Phase 6: Testing & Migration

### 6.1 Create Tests

**File:** `apps/pdf_forms/tests/test_sections.py` (new file)

```python
class SectionConfigurationTests(TestCase):
    """Test section-based form configuration."""
    
    def test_sectioned_form_generation(self):
        """Test form generation with sections."""
    
    def test_unsectioned_form_backward_compatibility(self):
        """Test that forms without sections still work."""
    
    def test_section_validation(self):
        """Test section configuration validation."""
    
    def test_field_section_assignment(self):
        """Test field assignment to sections."""
    
    def test_section_ordering(self):
        """Test section and field ordering."""
```

### 6.2 Create Data Migration

**File:** `apps/pdf_forms/management/commands/migrate_form_sections.py` (new file)

```python
class Command(BaseCommand):
    """Management command to migrate existing forms to section format."""
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--create-default-sections', action='store_true')
    
    def handle(self, *args, **options):
        # Process existing forms
        # Add default sections if requested
        # Preserve existing field configurations
```

### 6.3 Update Documentation

**File:** `docs/apps/pdf-forms.md`

Add section about section-based form organization:

- Configuration examples
- Admin interface usage
- Best practices for section organization
- Troubleshooting common issues

---

## Phase 7: Rollout Strategy

### 7.1 Backward Compatibility

- All existing forms continue to work without modifications
- Forms without sections render using the fallback method
- Admin can gradually add sections to existing forms

### 7.2 Migration Path

1. **Deploy code changes**
2. **Run migration command** (if needed)
3. **Train admin users** on new section features
4. **Gradually update existing forms** with sections
5. **Monitor performance** and user feedback

### 7.3 Feature Flags (Optional)

Consider adding a feature flag to enable/disable sections:

```python
# settings.py
PDF_FORMS_SECTIONS_ENABLED = True
```

This allows for safe rollout and easy rollback if needed.

---

## Timeline Estimate

- **Phase 1-2:** 2-3 days (Backend changes)
- **Phase 3:** 1-2 days (Template updates)  
- **Phase 4:** 3-4 days (Admin interface)
- **Phase 5:** 1-2 days (CSS/JS enhancements)
- **Phase 6:** 2-3 days (Testing & migration)
- **Phase 7:** 1 day (Deployment)

**Total:** 10-15 development days

---

## Success Criteria

1. ✅ Admin users can create and manage form sections
2. ✅ Fields can be assigned to sections with ordering
3. ✅ Forms render with collapsible accordion sections
4. ✅ Backward compatibility maintained for existing forms
5. ✅ No performance degradation in form rendering
6. ✅ All existing tests pass
7. ✅ New functionality is well-tested
8. ✅ Documentation updated

This implementation provides a clean, user-friendly way to organize PDF form fields while maintaining full backward compatibility and providing an intuitive admin interface.
