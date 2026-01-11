# PDF Forms Architecture Refactor Plan

## Executive Summary

This plan outlines the refactoring of the PDF forms system to support both hospital-specific configurable forms and complex national forms (APAC/AIH) while maintaining backward compatibility and enhancing user experience with gender auto-fill functionality.

## Current Architecture Analysis

### Existing Components

- **PDFFormTemplate**: Hospital-specific forms with JSON field configuration
- **PDFFormSubmission**: Event-based form submissions with timeline integration
- **DynamicFormGenerator**: Creates Django forms from JSON configuration
- **PDFFormOverlay**: Generates filled PDFs from form data
- **Admin Configurator**: Graphical tool for field positioning

### Current Limitations

1. Gender fields require manual checkbox selection (UX degradation)
2. National forms (APAC/AIH) don't fit the configurable model
3. 5000+ procedures need database integration, not Data Sources
4. Complex forms require hardcoded logic vs graphical configuration

## Proposed Solution: Path A - Hybrid Architecture

### Core Principles

- **Zero Breaking Changes**: Existing hospital forms continue working unchanged
- **Code Reuse**: Share components where beneficial (PDF overlay, security)
- **Simplicity**: Single interface, same event types, minimal complexity
- **Flexibility**: Full control for complex forms while keeping speed for simple ones

## Implementation Plan

### Phase 1: Foundation & Procedures Database

#### 1.1 Procedures Database Table

**Location**: `apps/core/models.py`

```python
class MedicalProcedure(models.Model):
    """National medical procedures and codes (APAC/AIH)"""
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Features**:

- 5000+ procedures storage
- Full-text search capabilities
- Audit trail for updates

#### 1.2 Management Command

**Location**: `apps/core/management/commands/import_procedures.py`

```bash
# Import from CSV/JSON
uv run python manage.py import_procedures --file procedures.csv
```

#### 1.3 Procedures API

**Location**: `apps/core/api/procedures.py`

```python
# Dynamic search endpoint for form fields
GET /api/procedures/search/?q=diabetes&limit=10
```

**Returns**:

```json
{
  "results": [
    {
      "code": "0301010012",
      "description": "Consulta médica em atenção especializada"
    }
  ]
}
```

#### 1.4 Testing

- Procedures model tests
- API endpoint tests
- Import command tests
- Search functionality tests

**Deliverables**:

- [ ] Procedures database model
- [ ] Import management command
- [ ] Search API endpoint
- [ ] Comprehensive test suite
- [ ] Basic admin interface

---

### Phase 2: Gender Auto-fill Enhancement

#### 2.1 Enhanced Field Mapping

**Location**: `apps/pdf_forms/services/field_mapping.py`

**Enhancement**: Detect gender field patterns:

```python
GENDER_FIELD_PATTERNS = {
    'male_checkbox': ['masculino', 'male', 'homem', 'M'],
    'female_checkbox': ['feminino', 'female', 'mulher', 'F'],
    'gender_text': ['sexo', 'genero', 'gender']
}
```

#### 2.2 Form Generator Enhancement

**Location**: `apps/pdf_forms/services/form_generator.py`

**New Features**:

- Auto-detect gender checkbox pairs
- Set initial values based on `patient.gender`
- Handle both checkbox and text field types
- Maintain backward compatibility

```python
def process_gender_fields(self, field_config, patient):
    """Process gender fields for auto-fill"""
    if patient and patient.gender:
        # Auto-check appropriate gender boxes
        # Set text field values
        pass
```

#### 2.3 Frontend Enhancement

**Location**: `assets/js/pdf_forms/`

**New Features**:

- JavaScript for linked gender fields
- Visual feedback for auto-filled fields
- Validation for gender field consistency

#### 2.4 Testing

- Gender detection logic tests
- Auto-fill functionality tests
- JavaScript integration tests
- Backward compatibility tests

**Deliverables**:

- [ ] Enhanced gender field detection
- [ ] Auto-fill implementation
- [ ] Frontend JavaScript enhancements
- [ ] Comprehensive test coverage
- [ ] Documentation for gender field configuration

---

### Phase 3: National Forms Infrastructure

#### 3.1 Model Enhancements

**Location**: `apps/pdf_forms/models.py`

**Changes**:

```python
class PDFFormTemplate(models.Model):
    # Add form type field
    form_type = models.CharField(
        max_length=20,
        choices=[
            ('HOSPITAL', 'Hospital Specific'),
            ('APAC', 'APAC National'),
            ('AIH', 'AIH National'),
        ],
        default='HOSPITAL'
    )

    # Keep existing hospital_specific for backward compatibility
    hospital_specific = models.BooleanField(default=True)

    @property
    def is_national_form(self):
        return self.form_type in ['APAC', 'AIH']
```

#### 3.2 National Forms Views

**Location**: `apps/pdf_forms/views/national_forms.py`

**New Views**:

- `APACFormView`: Hardcoded APAC form logic
- `AIHFormView`: Future AIH form implementation
- Procedures search integration
- Same security and permissions model

#### 3.3 Hardcoded APAC Form

**Location**: `apps/pdf_forms/forms/apac_form.py`

```python
class APACForm(forms.Form):
    """Hardcoded APAC form with complex validation"""

    # Patient fields (auto-filled)
    patient_name = forms.CharField()
    patient_gender = forms.CharField()

    # Procedures field with search
    procedure = forms.ModelChoiceField(
        queryset=MedicalProcedure.objects.filter(
            procedure_type__in=['APAC', 'BOTH'],
            is_active=True
        )
    )

    # Complex validation logic
    def clean(self):
        # National form specific validations
        pass
```

#### 3.4 Form Selection Integration

**Location**: `apps/pdf_forms/views.py`

**Enhancement**: Update `PDFFormSelectView` to include national forms in the same interface:

```python
def get_queryset(self):
    return PDFFormTemplate.objects.filter(
        is_active=True
    ).exclude(
        form_fields__isnull=True
    ).exclude(
        form_fields__exact={}
    ).order_by('form_type', 'name')
```

**Deliverables**:

- [ ] Enhanced PDFFormTemplate model
- [ ] National forms views infrastructure
- [ ] Hardcoded APAC form implementation
- [ ] Procedures integration
- [ ] Updated form selection interface

---

### Phase 4: UI Integration & Testing

#### 4.1 Admin Configurator Enhancement

**Location**: `apps/pdf_forms/admin.py`

**Enhancement**: Allow admin configurator to work with national forms for developers to generate initial JSON configurations:

```python
def configure_fields_view(self, request, object_id):
    """Enhanced to support both hospital and national forms"""
    template = self.get_object(request, unquote(object_id))

    if template.is_national_form:
        # Show developer-friendly configuration mode
        # Generate JSON for hardcoded forms
        pass
```

#### 4.2 Form Selection UI

**Location**: `templates/pdf_forms/form_select.html`

**Enhancement**: Group forms by type while maintaining single interface:

```html
<div class="form-types">
  <h5>Formulários do Hospital</h5>
  <!-- Hospital forms -->

  <h5>Formulários Nacionais</h5>
  <!-- National forms -->
</div>
```

#### 4.3 Timeline Integration

**Enhancement**: Both form types appear in patient timeline with same event type but visual distinction:

```html
<div class="event-card pdf-form {{ form.form_type|lower }}">
  <span class="form-type-badge">{{ form.get_form_type_display }}</span>
</div>
```

#### 4.4 Comprehensive Testing

- End-to-end form filling tests
- Admin configurator tests
- Form selection integration tests
- Timeline display tests
- Performance tests with large procedures dataset

**Deliverables**:

- [ ] Enhanced admin configurator
- [ ] Improved form selection UI
- [ ] Timeline integration
- [ ] Complete test suite
- [ ] Performance optimization
- [ ] Documentation updates

---

## Migration Strategy

### Backward Compatibility

- **No breaking changes** to existing hospital forms
- **Automatic migration** adds `form_type` field with `HOSPITAL` default
- **Existing workflows** continue unchanged
- **Gradual rollout** of national forms

### Data Migration

```python
# Migration: Add form_type field with proper defaults
def migrate_form_types(apps, schema_editor):
    PDFFormTemplate = apps.get_model('pdf_forms', 'PDFFormTemplate')
    PDFFormTemplate.objects.filter(
        hospital_specific=True
    ).update(form_type='HOSPITAL')
```

### Rollout Plan

1. **Phase 1**: Deploy procedures database (no user-visible changes)
2. **Phase 2**: Deploy gender enhancement (immediate UX improvement)
3. **Phase 3**: Deploy national forms infrastructure (new functionality)
4. **Phase 4**: Deploy UI improvements and testing

## Technical Specifications

### Database Changes

- New `core_medicalprocedure` table
- New `form_type` field in `pdf_forms_pdfformtemplate`
- Indexes for performance on procedures search
- Migration scripts for data preservation

### API Changes

- New `/api/procedures/search/` endpoint
- Enhanced form selection API response
- Same PDF generation endpoints

### Security Considerations

- Same permission system for both form types
- Procedures search with proper input validation
- PDF security validations remain unchanged
- Audit trails for all changes

### Performance Considerations

- Procedures table indexes for fast search
- Cached procedure lookups
- Lazy loading of form configurations
- Optimized PDF generation pipeline

## Success Metrics

### Functionality

- [ ] Zero regressions in existing hospital forms
- [ ] Successful APAC form implementation
- [ ] Gender auto-fill working in 90%+ of cases
- [ ] Procedures search response time < 500ms

### User Experience

- [ ] Single, intuitive form selection interface
- [ ] Reduced manual data entry via auto-fill
- [ ] Clear visual distinction between form types
- [ ] Seamless timeline integration

### Code Quality

- [ ] 90%+ test coverage maintained
- [ ] No increase in complexity metrics
- [ ] Clean separation of concerns
- [ ] Comprehensive documentation

## Future Enhancements

### Phase 5: Advanced Features (Future)

- **AIH form implementation**
- **Bulk form processing**
- **Advanced procedures analytics**
- **Form versioning system**
- **Mobile-optimized forms**

### Technical Debt Reduction

- **Service layer extraction**
- **Enhanced caching strategies**
- **Background PDF generation**
- **Advanced field validation**

## Conclusion

This refactor maintains the simplicity and speed of the current system while adding the flexibility needed for
complex national forms. The phased approach ensures zero downtime and provides immediate value with each phase.

The hybrid architecture leverages the strengths of both approaches:

- **Graphical configuration** for rapid hospital form creation
- **Hardcoded forms** for complex national requirements
- **Shared infrastructure** for consistency and maintainability
- **Enhanced UX** with smart auto-fill capabilities

Each phase is independently valuable and testable, allowing for iterative improvement and continuous system availability.

