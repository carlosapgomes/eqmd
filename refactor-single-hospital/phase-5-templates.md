# Phase 5: Templates and Frontend Cleanup

**Estimated Time:** 45-60 minutes  
**Complexity:** Medium  
**Dependencies:** Phase 4 completed

## Objectives

1. Remove hospital selection UI from all templates
2. Remove hospital context from template rendering
3. Clean up hospital-related template tags and variables
4. Simplify navigation and user interface

## Tasks

### 1. Remove Hospital Selection UI

**Remove hospital context switcher:**
- [ ] Remove hospital selection dropdown from navbar/header
- [ ] Remove hospital context display from templates
- [ ] Remove hospital switching forms/modals

**Templates to update:**
- [ ] `templates/base.html` - Remove hospital context from header
- [ ] `templates/navbar.html` - Remove hospital selector
- [ ] Any hospital selection modals or forms

### 2. Update Patient Templates

**Simplify patient templates:**
- [ ] `apps/patients/templates/patients/patient_list.html` - Remove hospital filters
- [ ] `apps/patients/templates/patients/patient_detail.html` - Remove hospital info
- [ ] `apps/patients/templates/patients/patient_form.html` - Remove hospital fields
- [ ] Patient search templates - Remove hospital filtering

**Remove hospital information display:**
```django
<!-- Before (hospital context displayed) -->
<div class="patient-hospital">
    <strong>Hospital:</strong> {{ patient.current_hospital.name }}
    <span class="badge">{{ patient.status }}</span>
</div>

<!-- After (simple status only) -->
<div class="patient-status">
    <span class="badge badge-{{ patient.status }}">{{ patient.status|capfirst }}</span>
</div>
```

### 3. Update Core Dashboard Templates

**Simplify dashboard:**
- [ ] `apps/core/templates/core/dashboard.html` - Remove hospital widgets
- [ ] Remove hospital-specific statistics
- [ ] Remove hospital context from dashboard widgets

**Simplify dashboard widgets:**
```django
<!-- Before (hospital-aware widgets) -->
{% load hospital_tags %}
<div class="hospital-stats">
    <h4>{{ current_hospital.name }} Statistics</h4>
    {% hospital_patient_count current_hospital %}
</div>

<!-- After (simple global stats) -->
<div class="stats">
    <h4>Patient Statistics</h4>
    {% patient_count_widget %}
</div>
```

### 4. Update Event Templates

**Remove hospital context from events:**
- [ ] `apps/events/templates/events/event_list.html` - Remove hospital filters
- [ ] `apps/events/templates/events/event_detail.html` - Remove hospital context
- [ ] Event timeline templates - Remove hospital information

**Simplify event display:**
```django
<!-- Before (complex hospital context) -->
<div class="event-context">
    <span>Patient: {{ event.patient.name }}</span>
    <span>Hospital: {{ event.patient.current_hospital.name }}</span>
    <span>Ward: {{ event.patient.current_hospital.ward }}</span>
</div>

<!-- After (simple patient context) -->
<div class="event-context">
    <span>Patient: {{ event.patient.name }}</span>
    <span>Status: {{ event.patient.status|capfirst }}</span>
</div>
```

### 5. Update Daily Notes Templates

**Simplify daily notes templates:**
- [ ] Remove hospital context from daily note templates
- [ ] Simplify patient information display
- [ ] Remove hospital filtering from daily notes list

### 6. Update Form Templates

**Remove hospital fields from forms:**
- [ ] Patient creation/update forms - Remove hospital selection
- [ ] Remove hospital record inline formsets
- [ ] Simplify form validation display

**Simplified patient form with hospital header:**
```django
<!-- Before (complex hospital form) -->
<div class="form-group">
    {{ form.current_hospital.label_tag }}
    {{ form.current_hospital }}
    {% if form.current_hospital.errors %}
        <div class="invalid-feedback">{{ form.current_hospital.errors }}</div>
    {% endif %}
</div>

<!-- After (simple form with hospital context) -->
{% load hospital_tags %}
<div class="hospital-context mb-3">
    <small class="text-muted">{% hospital_name %} - {% hospital_address %}</small>
</div>

<div class="form-group">
    {{ form.status.label_tag }}
    {{ form.status }}
</div>
```

### 7. Update Navigation Templates

**Simplify navigation:**
- [ ] Remove hospital-related menu items
- [ ] Remove hospital management links
- [ ] Remove hospital context from breadcrumbs

### 8. Update Template Tags and Add Hospital Context

**Remove hospital-related template tags:**
- [ ] Remove hospital context template tags
- [ ] Remove hospital filtering template tags
- [ ] Update permission template tags to remove hospital logic

**Add hospital configuration template tags:**
```python
# apps/core/templatetags/hospital_tags.py
from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def hospital_name():
    return settings.HOSPITAL_CONFIG['name']

@register.simple_tag
def hospital_address():
    return settings.HOSPITAL_CONFIG['address']

@register.simple_tag
def hospital_logo():
    if settings.HOSPITAL_CONFIG['logo_url']:
        return settings.HOSPITAL_CONFIG['logo_url']
    return settings.STATIC_URL + settings.HOSPITAL_CONFIG['logo_path']

@register.inclusion_tag('core/partials/hospital_header.html')
def hospital_header():
    return {'hospital': settings.HOSPITAL_CONFIG}
```

**Files to update:**
- [ ] `apps/core/templatetags/permission_tags.py` - Remove hospital checks
- [ ] `apps/patients/templatetags/patient_tags.py` - Remove hospital context
- [ ] **Create:** `apps/core/templatetags/hospital_tags.py` - Hospital config access
- [ ] Remove any hospital-specific template tag files

### 9. Update Static Templates

**Clean up static content:**
- [ ] Update about page / help pages - Remove hospital references
- [ ] Update any documentation templates
- [ ] Remove hospital-related help content

### 10. Update Error Templates

**Simplify error handling:**
- [ ] Remove hospital context from error pages
- [ ] Update permission denied pages - Remove hospital context
- [ ] Simplify error messages

## Template Variable Cleanup

### Remove Hospital Context Variables

**Common variables to remove:**
```django
<!-- Remove these template variables -->
{{ current_hospital }}
{{ available_hospitals }}
{{ user.hospitals.all }}
{{ user.current_hospital }}
{{ patient.current_hospital }}
{{ patient.hospital_records }}

<!-- Replace with simplified variables -->
{{ user.profession }}
{{ patient.status }}
{{ patient.get_status_display }}
```

### Update Template Conditionals

**Simplify conditional logic:**
```django
<!-- Before (complex hospital logic) -->
{% if user.current_hospital and patient.current_hospital == user.current_hospital %}
    <a href="{% url 'patient_edit' patient.id %}">Edit Patient</a>
{% endif %}

<!-- After (simple role logic) -->
{% if user|has_permission:"patients.change_patient" %}
    <a href="{% url 'patient_edit' patient.id %}">Edit Patient</a>
{% endif %}
```

## Search Interface Simplification

**Simplify search forms:**
```django
<!-- Before (hospital-aware search) -->
<form method="get" class="search-form">
    <select name="hospital">
        <option value="">All Hospitals</option>
        {% for hospital in available_hospitals %}
            <option value="{{ hospital.id }}">{{ hospital.name }}</option>
        {% endfor %}
    </select>
    <input type="text" name="query" placeholder="Search patients...">
    <button type="submit">Search</button>
</form>

<!-- After (simple search) -->
<form method="get" class="search-form">
    <input type="text" name="query" placeholder="Search patients...">
    <select name="status">
        <option value="">All Statuses</option>
        {% for status_code, status_name in patient_status_choices %}
            <option value="{{ status_code }}">{{ status_name }}</option>
        {% endfor %}
    </select>
    <button type="submit">Search</button>
</form>
```

## Patient Status Display

**Simplify patient status badges:**
```django
<!-- Before (complex hospital + status) -->
<div class="patient-info">
    <span class="hospital-badge">{{ patient.current_hospital.name }}</span>
    <span class="status-badge status-{{ patient.status }}">{{ patient.get_status_display }}</span>
</div>

<!-- After (simple status focus) -->
<div class="patient-info">
    <span class="status-badge status-{{ patient.status }}">{{ patient.get_status_display }}</span>
</div>
```

## Files to Modify

### Template Files:
- [ ] `templates/base.html` - Add hospital logo and name to header
- [ ] `templates/navbar.html` - Add hospital branding
- [ ] `apps/core/templates/core/dashboard.html` - Add hospital info widget
- [ ] `apps/patients/templates/patients/*.html` - Add hospital context display
- [ ] `apps/events/templates/events/*.html` - Add hospital header to reports
- [ ] `apps/dailynotes/templates/dailynotes/*.html` - Add hospital context
- [ ] **Create:** `apps/core/templates/core/partials/hospital_header.html` - Hospital branding partial

### Template Tag Files:
- [ ] `apps/core/templatetags/permission_tags.py` - Remove hospital logic
- [ ] `apps/patients/templatetags/patient_tags.py` - Remove hospital context
- [ ] **Create:** `apps/core/templatetags/hospital_tags.py` - Hospital configuration tags
- [ ] Remove hospital-specific template tag files

### Static Files (if any hospital-specific):
- [ ] Remove hospital-related CSS classes
- [ ] Remove hospital-related JavaScript
- [ ] Update form styling

## CSS/JavaScript Cleanup

**Remove hospital-related frontend code:**
- [ ] Remove hospital selection JavaScript
- [ ] Remove hospital context switching logic
- [ ] Remove hospital-specific CSS classes
- [ ] Simplify form styling

## Validation Checklist

Before proceeding to Phase 6:
- [ ] All templates render without hospital context
- [ ] Patient forms work without hospital fields
- [ ] Dashboard displays correctly
- [ ] Navigation works without hospital links
- [ ] Search functionality works
- [ ] No template rendering errors
- [ ] No missing template variables
- [ ] Event timeline displays correctly

## User Experience Improvements

**Simplified interface benefits:**
- Cleaner, less cluttered UI
- Faster page loading (less context)
- Simpler navigation
- Reduced cognitive load for users
- Focus on patient care rather than hospital management

## Responsive Design

**Ensure templates remain responsive:**
- [ ] Test templates on mobile devices
- [ ] Verify form layouts work correctly
- [ ] Check that removed hospital fields don't break layouts
- [ ] Update grid layouts if needed