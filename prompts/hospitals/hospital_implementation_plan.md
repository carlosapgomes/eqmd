# Hospital Model Implementation Plan - Vertical Slicing Approach

## Slice 1: Core Model and Basic Admin Interface

### Step 1: Initial Model Setup

1. Create the Hospital model in `apps/hospitals/models.py`:
   - Add UUID primary key, name, and short_name fields
   - Implement `__str__` method
   - Add Meta class with ordering

### Step 2: Basic Admin Integration

1. Register Hospital model in `apps/hospitals/admin.py`
2. Configure basic list_display and search_fields

### Step 3: Add to INSTALLED_APPS

1. Add "apps.hospitals" to INSTALLED_APPS in `config/settings.py`

### Step 4: Create and Apply Migrations

1. Run `python manage.py makemigrations`
2. Run `python manage.py migrate`

### Step 5: Test Basic Functionality

1. Create test for model creation and string representation
2. Verify admin interface access

## Slice 2: Location Information and URL Configuration

### Step 1: Extend Model with Location Fields

1. Add address, city, state, zip_code fields to Hospital model
2. Update migrations

### Step 2: Implement get_absolute_url Method

1. Add the method to return detail view URL

### Step 3: Create Basic URL Configuration

1. Create `apps/hospitals/urls.py`
2. Define URL patterns for hospital views
3. Include hospital URLs in project's main urls.py

### Step 4: Test Location Fields and Configuration Verification

1. **Configuration Verification**

   - Verify `apps/hospitals/apps.py` has correct `name = 'apps.hospitals'`
   - Test model import in Django shell:

     ```bash
     python manage.py shell -c "from apps.hospitals.models import Hospital; print('Hospital model imported successfully')"
     ```

2. **Basic Functionality Smoke Test**

   - Test model creation with new location fields:

     ```bash
     python manage.py shell -c "from apps.hospitals.models import Hospital; h = Hospital.objects.create(name='Test Hospital', short_name='TH', address='123 Main St', city='Salvador', state='BA', zip_code='40000-000'); print(f'Created hospital with location: {h}')"
     ```

3. **Test Execution with Fallback Options**

   - Primary method (using pytest):

     ```bash
     pytest apps/hospitals/tests.py -v --no-cov
     ```

   - Fallback method (if pytest fails):

     ```bash
     python manage.py shell -c "from apps.hospitals.tests import *; import unittest; unittest.main(verbosity=2, exit=False)"
     ```

4. **URL Resolution Verification**

   - Test URL configuration before writing complex tests
   - Verify `get_absolute_url` method works in Django shell
   - Check that URLs are properly included in main `config/urls.py`

5. **Create tests for location field validation**
6. **Test URL resolution**

### Step 5: Error Troubleshooting

1. **Common Issues Checklist**

   - If encountering "Model doesn't declare an explicit app_label" error, verify INSTALLED_APPS includes 'apps.hospitals'
   - If URL resolution fails, ensure hospitals URLs are included in main urls.py
   - If migrations fail, check for field conflicts with existing data

2. **Configuration Validation**
   - Verify `config/test_settings.py` inherits from main settings
   - Confirm all model fields are properly configured before proceeding
   - Test admin interface accessibility with new fields

## Slice 3: Contact Information and Tracking Fields

### Step 1: Add Contact Information Fields

1. Add phone field to Hospital model
2. Update migrations

### Step 2: Add Tracking Fields

1. Add created_at, updated_at, created_by, updated_by fields
2. Update migrations

### Step 3: Verify App Configuration and Basic Functionality

1. **Verify Model Field Updates**

   - Test field additions through Django shell:

     ```bash
     python manage.py shell -c "from apps.hospitals.models import Hospital; print(Hospital._meta.get_fields())"
     ```

2. **Basic Functionality Smoke Test**

   - Test model creation with tracking fields:

     ```bash
     python manage.py shell -c "from apps.hospitals.models import Hospital; from django.contrib.auth import get_user_model; User = get_user_model(); user = User.objects.first(); h = Hospital.objects.create(name='Test Hospital', phone='123456789', created_by=user, updated_by=user); print(f'Created hospital with tracking: {h}, created at {h.created_at}')"
     ```

3. **Test Execution with Fallback Options**

   - Primary method (using pytest):

     ```bash
     pytest apps/hospitals/tests.py::TestHospitalModel::test_tracking_fields -v
     ```

   - Fallback method (if pytest fails):

     ```bash
     python manage.py test apps.hospitals.tests.TestHospitalModel.test_tracking_fields
     ```

### Step 4: Test Tracking Functionality

1. Create tests for tracking fields
2. Test automatic timestamp updates

## Slice 4: URL Configuration and Basic Views

### Step 1: Create URL Configuration

1. Create `apps/hospitals/urls.py`
2. Add URL patterns for list and detail views
3. Include hospital URLs in project URLs

### Step 2: Implement Basic List View

1. Create HospitalListView in views.py
2. Create list template in `templates/hospitals/hospital_list.html`

### Step 3: Verify App Configuration and Basic Functionality

1. **Verify URL Configuration**

   - Test URL resolution through Django shell:

     ```bash
     python manage.py shell -c "from django.urls import reverse; print(reverse('hospitals:hospital_list'))"
     ```

2. **Basic View Smoke Test**

   - Test view accessibility:

     ```bash
     python manage.py shell -c "from django.test import Client; c = Client(); response = c.get('/hospitals/'); print(f'Status code: {response.status_code}')"
     ```

3. **Template Verification**

   - Verify template exists and can be rendered:

     ```bash
     python manage.py shell -c "from django.template.loader import get_template; template = get_template('hospitals/hospital_list.html'); print('Template found and loaded successfully')"
     ```

### Step 4: Test List View

1. Create tests for list view
2. Test pagination and ordering

## Slice 5: Detail View Implementation

### Step 1: Implement Detail View

1. Create HospitalDetailView in views.py
2. Create detail template in `templates/hospitals/hospital_detail.html`

### Step 2: Verify App Configuration and Basic Functionality

1. **Verify URL Configuration**

   - Test detail URL resolution through Django shell:

     ```bash
     python manage.py shell -c "from django.urls import reverse; from apps.hospitals.models import Hospital; hospital = Hospital.objects.first(); print(reverse('hospitals:hospital_detail', kwargs={'pk': hospital.pk}))"
     ```

2. **Basic View Smoke Test**

   - Test detail view accessibility:

     ```bash
     python manage.py shell -c "from django.test import Client; from apps.hospitals.models import Hospital; hospital = Hospital.objects.first(); c = Client(); response = c.get(f'/hospitals/{hospital.pk}/'); print(f'Status code: {response.status_code}')"
     ```

3. **Template Verification**

   - Verify template exists and can be rendered:

     ```bash
     python manage.py shell -c "from django.template.loader import get_template; template = get_template('hospitals/hospital_detail.html'); print('Template found and loaded successfully')"
     ```

### Step 3: Test Detail View

1. Create tests for detail view
2. Test context data and template rendering

## Slice 6: Create and Update Views

### Step 1: Create Basic ModelForm

1. Create `apps/hospitals/forms.py`
2. Implement HospitalForm with appropriate fields and validation

### Step 2: Implement Create View

1. Create HospitalCreateView in views.py
2. Create form template in `templates/hospitals/hospital_form.html`
3. Add permission requirements

### Step 3: Verify App Configuration and Basic Functionality

1. **Verify Form Configuration**

   - Test form initialization through Django shell:

     ```bash
     python manage.py shell -c "from apps.hospitals.forms import HospitalForm; form = HospitalForm(); print(f'Form fields: {form.fields}')"
     ```

2. **Basic View Smoke Test**

   - Test create view accessibility:

     ```bash
     python manage.py shell -c "from django.test import Client; from django.contrib.auth import get_user_model; User = get_user_model(); c = Client(); c.force_login(User.objects.first()); response = c.get('/hospitals/create/'); print(f'Status code: {response.status_code}')"
     ```

3. **Template Verification**

   - Verify template exists and can be rendered:

     ```bash
     python manage.py shell -c "from django.template.loader import get_template; template = get_template('hospitals/hospital_form.html'); print('Template found and loaded successfully')"
     ```

### Step 4: Implement Update View

1. Create HospitalUpdateView in views.py
2. Reuse form template
3. Add permission requirements

### Step 5: Test Create and Update Views

1. Create tests for create view
2. Create tests for update view
3. Test form validation and permissions

## Slice 7: Delete View and Confirmation

### Step 1: Implement Delete View

1. Create HospitalDeleteView in views.py
2. Create confirmation template in `templates/hospitals/hospital_confirm_delete.html`
3. Add permission requirements

### Step 2: Verify App Configuration and Basic Functionality

1. **Verify URL Configuration**

   - Test delete URL resolution through Django shell:

     ```bash
     python manage.py shell -c "from django.urls import reverse; from apps.hospitals.models import Hospital; hospital = Hospital.objects.first(); print(reverse('hospitals:hospital_delete', kwargs={'pk': hospital.pk}))"
     ```

2. **Basic View Smoke Test**

   - Test delete view accessibility:

     ```bash
     python manage.py shell -c "from django.test import Client; from django.contrib.auth import get_user_model; from apps.hospitals.models import Hospital; User = get_user_model(); hospital = Hospital.objects.first(); c = Client(); c.force_login(User.objects.first()); response = c.get(f'/hospitals/{hospital.pk}/delete/'); print(f'Status code: {response.status_code}')"
     ```

3. **Template Verification**

   - Verify template exists and can be rendered:

     ```bash
     python manage.py shell -c "from django.template.loader import get_template; template = get_template('hospitals/hospital_confirm_delete.html'); print('Template found and loaded successfully')"
     ```

### Step 3: Test Delete View

1. Create tests for delete view
2. Test confirmation and actual deletion
3. Test permission requirements

## Slice 8: Search and Filtering

### Step 1: Implement Search Functionality

1. Add search form to list template
2. Update list view to handle search parameters

### Step 2: Implement Filtering

1. Add filtering options to list view
2. Update template to display filters

### Step 3: Verify App Configuration and Basic Functionality

1. **Verify Search Parameter Handling**

   - Test search functionality through Django shell:

     ```bash
     python manage.py shell -c "from apps.hospitals.models import Hospital; from apps.hospitals.views import HospitalListView; from django.http import HttpRequest; request = HttpRequest(); request.GET = {'q': 'Test'}; view = HospitalListView(); view.request = request; queryset = view.get_queryset(); print(f'Search results count: {queryset.count()}')"
     ```

2. **Basic Search Smoke Test**

   - Test search through client:

     ```bash
     python manage.py shell -c "from django.test import Client; c = Client(); response = c.get('/hospitals/?q=Test'); print(f'Status code: {response.status_code}')"
     ```

3. **Template Rendering Verification**

   - Verify search form renders correctly:

     ```bash
     python manage.py shell -c "from django.test import Client; c = Client(); response = c.get('/hospitals/'); print('Search form in response: ' + ('Yes' if 'search' in response.content.decode() else 'No'))"
     ```

### Step 4: Test Search and Filtering

1. Create tests for search functionality
2. Test filtering options
3. Test combined search and filtering

## Slice 9: Related Data Display

### Step 1: Display Related Wards

1. Update detail view to include related wards
2. Add ward list to detail template

### Step 2: Display Related Users

1. Update detail view to include related users
2. Add user list to detail template

### Step 3: Verify App Configuration and Basic Functionality

1. **Verify Related Data Queries**

   - Test related data access through Django shell:

     ```bash
     python manage.py shell -c "from apps.hospitals.models import Hospital; hospital = Hospital.objects.first(); print(f'Related wards: {list(hospital.ward_set.all())}'); print(f'Related users: {list(hospital.hospitaluser_set.all())}')"
     ```

2. **Context Data Verification**

   - Test context data in detail view:

     ```bash
     python manage.py shell -c "from apps.hospitals.views import HospitalDetailView; from django.test import RequestFactory; from apps.hospitals.models import Hospital; hospital = Hospital.objects.first(); factory = RequestFactory(); request = factory.get(f'/hospitals/{hospital.pk}/'); view = HospitalDetailView(); view.setup(request, pk=hospital.pk); context = view.get_context_data(); print(f'Context keys: {context.keys()}')"
     ```

3. **Template Rendering Verification**

   - Verify related data sections in template:

     ```bash
     python manage.py shell -c "from django.test import Client; from apps.hospitals.models import Hospital; hospital = Hospital.objects.first(); c = Client(); response = c.get(f'/hospitals/{hospital.pk}/'); content = response.content.decode(); print('Wards section in template: ' + ('Yes' if 'wards' in content.lower() else 'No')); print('Users section in template: ' + ('Yes' if 'users' in content.lower() else 'No'))"
     ```

### Step 4: Test Related Data Display

1. Create tests for related wards display
2. Create tests for related users display
3. Test empty related data handling

### Additional Recommendations

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
