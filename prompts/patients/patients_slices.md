This is a splitting plan for the file @prompts/patient_implementation_plan.md.

````markdown path=prompts/patient_implementation_plan_part1.md mode=EDIT
# Patients App Implementation Plan - Part 1: Core Setup and Models

## Vertical Slice 1: Initial App Setup and Patient Model

### Step 1: App Configuration and Basic Setup

1. Create the patients app structure
   ```bash
   python manage.py startapp patients apps/patients
   ```
2. Add the app to INSTALLED_APPS in config/settings.py
3. Verify app configuration:
   - Check app is properly registered in Django
   - Verify app structure is correct
   - Run Django shell to confirm app is recognized

### Step 2: Create Patient Model

1. Create the Patient model in apps/patients/models.py:
   - Add UUID primary key
   - Add basic fields (name, birthday, contact info)
   - Add status field with choices
   - Add hospital relationship fields
   - Add tracking fields (created_at, updated_by, etc.)
   - Implement **str** method
   - Add Meta class with ordering and verbose names

### Step 3: Create PatientHospitalRecord Model

1. Add the PatientHospitalRecord model:
   - Add UUID primary key
   - Add patient and hospital ForeignKeys
   - Add record_number field
   - Add admission/discharge date fields
   - Add tracking fields
   - Implement **str** method
   - Add Meta class with ordering and verbose names

### Step 4: Create AllowedTag Model

1. Add the AllowedTag model:
   - Add name and slug fields
   - Implement **str** method
   - Add Meta class with ordering and verbose names
2. Add ManyToMany relationship from Patient to AllowedTag

### Step 5: Create and Apply Migrations

1. Run `python manage.py makemigrations patients`
2. Run `python manage.py migrate patients`
3. Verify migrations applied correctly:
   ```bash
   python manage.py showmigrations patients
   ```

### Step 6: Basic Admin Integration

1. Create apps/patients/admin.py:
   - Register Patient model
   - Register PatientHospitalRecord model
   - Register AllowedTag model
   - Configure basic list_display and search_fields

### Step 7: Test Basic Functionality

1. Create test directory structure:
   ```bash
   mkdir -p apps/patients/tests
   touch apps/patients/tests/__init__.py
   ```
2. Create test_models.py:
   - Test model creation
   - Test string representation
   - Test status choices
   - Test relationships between models
````

````markdown path=prompts/patient_implementation_plan_part2.md mode=EDIT
# Patients App Implementation Plan - Part 2: Model Methods and Admin Customization

## Vertical Slice 2: Patient Model Methods and Admin Customization

### Step 1: Implement Patient Model Methods

1. Add helper methods to Patient model:
   - Add admit_to_hospital method
   - Add discharge method
   - Add transfer method
   - Add set_record_number method

### Step 2: Verify Basic Model Methods

1. Test model methods through Django shell:
   ```bash
   python manage.py shell -c "from apps.patients.models import Patient; from apps.hospitals.models import Hospital; from django.contrib.auth import get_user_model; User = get_user_model(); user = User.objects.first(); hospital = Hospital.objects.first(); patient = Patient.objects.create(name='Test Patient', birthday='1980-01-01', status=1, created_by=user, updated_by=user); patient.admit_to_hospital(hospital, user=user); print(f'Patient admitted to {patient.current_hospital}')"
   ```

### Step 3: Enhance Admin Interface

1. Customize Patient admin:

   - Add fieldsets for better organization
   - Add list_filters for status, hospital, etc.
   - Add inlines for hospital records
   - Add custom actions (e.g., discharge patients)

2. Customize PatientHospitalRecord admin:

   - Add fieldsets
   - Add list_filters for hospital
   - Add search fields

3. Customize AllowedTag admin:
   - Add prepopulated_fields for slug

### Step 4: Test Admin Customizations

1. Create admin test file:

   - Test admin site registration
   - Test custom admin actions
   - Test inline admin functionality

2. Test admin customizations:
   - Verify inline admin works correctly
   - Test adding hospital records through patient admin
   - Verify permissions work as expected
````

````markdown path=prompts/patient_implementation_plan_part3.md mode=EDIT
# Patients App Implementation Plan - Part 3: Forms and Basic Views

## Vertical Slice 3: Patient Forms and Basic Views

### Step 1: Create Patient Forms

1. Create forms.py:
   ```python
   from django import forms
   from crispy_forms.helper import FormHelper
   from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML
   from .models import Patient, PatientHospitalRecord, AllowedTag
   ```
   - Implement PatientForm
   - Implement PatientHospitalRecordForm
   - Implement AllowedTagForm
   - Add crispy forms layouts
   - Add validation methods

### Step 2: Create Base Templates

1. Create patient_base.html template:
   - Add base layout with sidebar
   - Add content blocks
   - Add message display

### Step 3: Create Patient List Template

1. Create patient_list.html:
   - Extend patient_base.html
   - Add search functionality
   - Add table for displaying patients
   - Add pagination
   - Add status indicators

### Step 4: Create Patient Detail Template

1. Create patient_detail.html:
   - Extend patient_base.html
   - Add patient information sections
   - Add hospital records section
   - Add actions (edit, delete, etc.)

### Step 5: Create Form Templates

1. Create patient_form.html:

   - Extend patient_base.html
   - Add crispy form rendering
   - Add cancel/submit buttons

2. Create hospital_record_form.html:

   - Extend patient_base.html
   - Add crispy form rendering
   - Add cancel/submit buttons

3. Create confirmation templates:
   - Create patient_confirm_delete.html
   - Create hospital_record_confirm_delete.html
   - Create tag_confirm_delete.html

### Step 6: Test Template Rendering

1. Create test_templates.py:
   - Test template existence
   - Test template inheritance
   - Test template context variables
````

````markdown path=prompts/patient_implementation_plan_part4.md mode=EDIT
# Patients App Implementation Plan - Part 4: Views and URLs

## Vertical Slice 4: Patient Views and URLs

### Step 1: Create Basic Views

1. Create views.py:
   - Implement PatientListView
   - Implement PatientDetailView
   - Implement PatientCreateView
   - Implement PatientUpdateView
   - Implement PatientDeleteView
   - Implement PatientHospitalRecordCreateView
   - Implement PatientHospitalRecordUpdateView
   - Implement PatientHospitalRecordDeleteView
   - Implement AllowedTagListView
   - Implement AllowedTagCreateView
   - Implement AllowedTagUpdateView
   - Implement AllowedTagDeleteView

### Step 2: Create URLs

1. Create urls.py:

   - Add URL patterns for all views
   - Add app_name for namespacing

2. Include patient URLs in project urls.py:
   ```python
   path('patients/', include('apps.patients.urls', namespace='patients')),
   ```

### Step 3: Verify URL Configuration

1. Test URL resolution:
   ```bash
   python manage.py shell -c "from django.urls import reverse; print(reverse('patients:patient_list'))"
   ```

### Step 4: Add View Permissions

1. Add permission_required to class-based views
2. Add login_required decorators to function-based views
3. Add permission checks to templates

### Step 5: Test Views

1. Create test_views.py:
   - Test list view with and without filters
   - Test detail view
   - Test create view with valid and invalid data
   - Test update view
   - Test delete view
   - Test permission requirements

### Step 6: Test Form Submission

1. Create test_forms.py:
   - Test form validation
   - Test form submission
   - Test form rendering with crispy forms
````

````markdown path=prompts/patient_implementation_plan_part5.md mode=EDIT
# Patients App Implementation Plan - Part 5: Integration and Dashboard

## Vertical Slice 5: Dashboard Integration and Template Tags

### Step 1: Create Dashboard Widgets

1. Create patient_stats.html widget:

   - Add total patient count
   - Add status breakdown
   - Add hospital distribution

2. Create recent_patients.html widget:
   - Add list of recently added patients
   - Add quick actions

### Step 2: Update Sidebar Navigation

1. Update sidebar.html:

   - Add patients section
   - Add links to patient list, create, and tag management

2. Update the dashboard template to include patient widgets:

   ```html
   {% if 'apps.patients' in INSTALLED_APPS %}
   <!-- Patient Statistics Row -->
   {% include 'patients/widgets/patient_stats.html' %}

   <div class="row">
     <!-- Recent Patients Column -->
     <div class="col-lg-6">
       {% include 'patients/widgets/recent_patients.html' %}
     </div>

     <!-- Other dashboard widgets -->
     <div class="col-lg-6">
       <!-- Other widgets here -->
     </div>
   </div>
   {% endif %}
   ```

### Step 3: Create Context Processors

1. Create context_processors.py:

   - Add patient_stats processor
   - Add recent_patients processor

2. Add context processors to settings.py:
   ```python
   'apps.patients.context_processors.patient_stats',
   ```

### Step 4: Add Template Tags for Patient Data

1. Create template tags file:

   ```python
   from django import template
   from django.utils.safestring import mark_safe
   from apps.patients.models import Patient
   ```

   - Add patient_status_badge filter
   - Add patient_tags inclusion tag

2. Create template for rendering patient tags:
   ```html
   {% if tags %}
   <div class="patient-tags">
     {% for tag in tags %}
     <span class="badge bg-secondary me-1">
       <i class="bi bi-tag-fill me-1"></i>{{ tag.name }}
     </span>
     {% endfor %}
   </div>
   {% endif %}
   ```

### Step 5: Test Dashboard Integration

1. Create test_integration.py:
   - Test dashboard includes patient widgets
   - Test sidebar includes patient links
   - Test context processors
   - Test template tags
````

````markdown path=prompts/patient_implementation_plan_part6.md mode=EDIT
# Patients App Implementation Plan - Part 6: Final Integration and Documentation

## Vertical Slice 6: Final Integration and Testing

### Step 1: Create Integration Tests

1. Create test_integration.py:
   ```python
   from django.test import TestCase
   from django.urls import reverse
   from django.contrib.auth import get_user_model
   from apps.patients.models import Patient, PatientHospitalRecord, AllowedTag
   from apps.hospitals.models import Hospital, Ward
   ```
   - Test patient-hospital integration
   - Test patient-ward integration
   - Test complete patient workflow
   - Test dashboard integration

### Step 2: Add Permissions and Groups

1. Create a migration to add patient-specific permissions and groups:
   ```python
   from django.db import migrations
   from django.contrib.auth.models import Group, Permission
   from django.contrib.contenttypes.models import ContentType
   ```
   - Create Patient Managers group with full permissions
   - Create Patient Viewers group with read-only permissions

### Step 3: Final Testing

1. Run all tests:

   ```bash
   python manage.py test apps.patients
   ```

2. Test with different user roles:
   - Test with superuser
   - Test with patient manager
   - Test with patient viewer
   - Test with unauthenticated user

## Vertical Slice 7: Final Documentation and Deployment

### Step 1: Update Project README

1. Add patients app information to the main project README:
   - Add features list
   - Add setup instructions
   - Add usage examples

### Step 2: Create User Guide

1. Create a user guide for the patients app:
   - Add overview
   - Add patient management instructions
   - Add hospital record management instructions
   - Add tag management instructions
   - Add status explanation

### Step 3: Final Deployment Checklist

1. Create a deployment checklist:
   - Add pre-deployment checks
   - Add deployment steps
   - Add post-deployment verification

## Additional Recommendations

1. **For All Slices**:

   - Always verify app configuration before running complex tests
   - Use Django shell for quick verification of model changes
   - Test both positive and negative cases (e.g., permissions denied)

2. **For Views**:

   - Test with authenticated and unauthenticated users
   - Verify proper redirect behavior for unauthorized access
   - Test with various user roles/permissions

3. **For Forms**:

   - Test validation with both valid and invalid data
   - Verify error messages are displayed correctly
   - Test form submission with missing required fields

4. **For Templates**:

   - Verify responsive design on different screen sizes
   - Test accessibility features
   - Ensure consistent styling with the rest of the application

5. **For Related Data**:
   - Test performance with large datasets
   - Implement pagination for related data lists
   - Consider using select_related/prefetch_related for optimization
````

These files are organized to minimize forward dependencies:

1. **Part 1**: Core setup, models, and basic admin integration
2. **Part 2**: Model methods and admin customization
3. **Part 3**: Forms and basic templates
4. **Part 4**: Views and URLs
5. **Part 5**: Dashboard integration and template tags
6. **Part 6**: Final integration, testing, and documentation

Each part builds on the previous ones without introducing dependencies on future parts. This structure allows for sequential implementation while maintaining a logical progression of features.

Based in the above plan, implement the patient_implementation_plan_part_7.md file with the steps from the "Vertical Slice 7: Final Documentation and Deployment" section.
