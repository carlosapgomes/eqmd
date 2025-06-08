# Ward Model Implementation Plan

## Overview

This implementation plan outlines the steps to create the Ward model and related functionality using a vertical slicing approach. Each slice represents a complete, testable feature set.

## Vertical Slice 1: Basic Ward Model and Admin Interface

### Step 1: Verify App Configuration

1. Confirm hospitals app is properly registered in INSTALLED_APPS:

   ```bash
   python manage.py shell -c "from django.conf import settings; print('apps.hospitals' in settings.INSTALLED_APPS)"
   ```

2. Verify app structure and configuration:

   ```bash
   python manage.py shell -c "from apps.hospitals.apps import HospitalsConfig; print(HospitalsConfig.name)"
   ```

3. Check Django can discover the app models:

   ```bash
   python manage.py check hospitals
   ```

### Step 2: Create Ward Model

1. Add Ward model to models.py:

   ```python
   class Ward(models.Model):
       name = models.CharField(max_length=100)
       description = models.TextField(blank=True)
       hospital = models.ForeignKey('Hospital', on_delete=models.CASCADE, related_name='wards')
       capacity = models.PositiveIntegerField(default=0)
       is_active = models.BooleanField(default=True)
       created_at = models.DateTimeField(auto_now_add=True)
       updated_at = models.DateTimeField(auto_now=True)
       created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_wards')
       updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='updated_wards')

       def __str__(self):
           return f"{self.name} ({self.hospital.name})"
   ```

2. Create migrations:

   ```bash
   python manage.py makemigrations hospitals
   ```

3. Apply migrations:

   ```bash
   python manage.py migrate hospitals
   ```

4. Verify model creation through Django shell:

   ```bash
   python manage.py shell -c "from apps.hospitals.models import Ward; print(Ward._meta.get_fields())"
   ```

### Step 3: Register Ward in Admin

1. Update admin.py:

   ```python
   from django.contrib import admin
   from .models import Hospital, Ward

   @admin.register(Ward)
   class WardAdmin(admin.ModelAdmin):
       list_display = ('name', 'hospital', 'capacity', 'is_active')
       list_filter = ('hospital', 'is_active')
       search_fields = ('name', 'description', 'hospital__name')
   ```

2. Verify admin registration:

   ```bash
   python manage.py shell -c "from django.contrib import admin; from apps.hospitals.models import Ward; print('Ward registered:', Ward in admin.site._registry)"
   ```

### Step 4: Basic Functionality Verification

1. Test model creation with hospital association:

   ```bash
   python manage.py shell -c "from apps.hospitals.models import Hospital, Ward; hospital = Hospital.objects.first(); if hospital: w = Ward.objects.create(name='Test Ward', description='Test Description', hospital=hospital, capacity=20, is_active=True); print(f'Created ward with hospital: {w.hospital}'); else: print('No hospitals found, create a hospital first')"
   ```

2. Test admin interface access:

   ```bash
   python manage.py runserver
   ```

   Then visit <http://localhost:8000/admin/hospitals/ward/> in your browser.

### Additional Recommendations

1. **For Model Design**:

   - Consider adding specialized fields like ward_type (enum/choices)
   - Add constraints for capacity (non-negative)
   - Consider adding a floor/location field

2. **For Data Integrity**:
   - Add unique_together constraint for hospital and name
   - Consider adding validation for capacity limits
   - Add help_text to fields for admin clarity

## Vertical Slice 2: Ward Properties and Methods

### Step 1: Verify Previous Slice Implementation

1. Confirm Ward model exists and has required fields:

   ```bash
   python manage.py shell -c "from apps.hospitals.models import Ward; print([f.name for f in Ward._meta.get_fields()])"
   ```

2. Verify hospital relationship:

   ```bash
   python manage.py shell -c "from apps.hospitals.models import Ward; ward = Ward.objects.first(); print(ward.hospital if ward else 'No wards found')"
   ```

### Step 2: Implement patient_count Property

1. Add property method to count patients in ward:

   ```python
   @property
   def patient_count(self):
       # This will be implemented when Patient model is available
       # For now, return a placeholder value
       return 0
   ```

2. Verify property implementation:

   ```bash
   python manage.py shell -c "from apps.hospitals.models import Ward; Ward.patient_count"
   ```

### Step 3: Implement occupancy_rate Property

1. Add property method to calculate occupancy percentage:

   ```python
   @property
   def occupancy_rate(self):
       if self.capacity == 0:
           return 0
       return round((self.patient_count / self.capacity) * 100, 1)
   ```

2. Verify property implementation:

   ```bash
   python manage.py shell -c "from apps.hospitals.models import Ward; Ward.occupancy_rate"
   ```

### Step 4: Basic Functionality Verification

1. Test properties through Django shell:

   ```bash
   python manage.py shell -c "from apps.hospitals.models import Ward; ward = Ward.objects.first(); if ward: print(f'Patient count: {ward.patient_count}'); print(f'Occupancy rate: {ward.occupancy_rate}%'); else: print('No wards found')"
   ```

2. Test property behavior with edge cases:

   ```bash
   python manage.py shell -c "from apps.hospitals.models import Hospital, Ward; hospital = Hospital.objects.first(); if hospital: w = Ward.objects.create(name='Zero Capacity Ward', hospital=hospital, capacity=0); print(f'Zero capacity ward occupancy rate: {w.occupancy_rate}%'); else: print('No hospitals found')"
   ```

### Additional Recommendations

1. **For Properties**:

   - Add caching for expensive calculations
   - Consider adding status property based on occupancy
   - Add property for available beds calculation

2. **For Performance**:
   - Use select_related when querying wards with hospitals
   - Consider denormalizing frequently accessed counts
   - Add database indexes for common query patterns

## Vertical Slice 3: Ward Template Tags

### Step 1: Verify Previous Slice Implementation

1. Confirm Ward model properties are working:

   ```bash
   python manage.py shell -c "from apps.hospitals.models import Ward; ward = Ward.objects.first(); if ward: print(f'Ward properties: {ward.patient_count}, {ward.occupancy_rate}'); else: print('No wards found')"
   ```

2. Check template directory structure:

   ```bash
   mkdir -p apps/hospitals/templatetags
   touch apps/hospitals/templatetags/__init__.py
   ```

### Step 2: Create Template Tags

1. Create hospital_tags.py:

   ```python
   from django import template
   from django.utils.html import format_html
   from apps.hospitals.models import Ward

   register = template.Library()

   @register.simple_tag
   def capacity_bar(ward):
       """Renders a progress bar showing ward capacity usage"""
       if not isinstance(ward, Ward):
           return ''

       occupancy = ward.occupancy_rate
       bar_class = 'bg-success'
       if occupancy > 90:
           bar_class = 'bg-danger'
       elif occupancy > 70:
           bar_class = 'bg-warning'

       return format_html(
           '<div class="progress" style="height: 20px;">'
           '<div class="progress-bar {}" role="progressbar" style="width: {}%;" '
           'aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">{}/{}beds ({}%)</div>'
           '</div>',
           bar_class, occupancy, occupancy, ward.patient_count, ward.capacity, occupancy
       )
   ```

2. Verify template tag file creation:

   ```bash
   ls -la apps/hospitals/templatetags/
   ```

### Step 3: Test Template Tags

1. Create a test template:

   ```bash
   mkdir -p apps/hospitals/templates/hospitals/tests
   ```

2. Create test_tags.html:

   ```html
   {% load hospital_tags %}
   <!doctype html>
   <html>
     <head>
       <title>Ward Capacity Test</title>
       <link
         href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
         rel="stylesheet"
       />
     </head>
     <body>
       <div class="container mt-5">
         <h1>Ward Capacity Test</h1>
         {% for ward in wards %}
         <div class="card mb-3">
           <div class="card-header">
             {{ ward.name }} ({{ ward.hospital.name }})
           </div>
           <div class="card-body">
             <p>Capacity: {{ ward.capacity }}</p>
             <p>Patients: {{ ward.patient_count }}</p>
             {% capacity_bar ward %}
           </div>
         </div>
         {% endfor %}
       </div>
     </body>
   </html>
   ```

### Step 4: Basic Functionality Verification

1. Test template tag rendering:

   ```bash
   python manage.py shell -c "from django.template import Template, Context; from apps.hospitals.models import Ward; ward = Ward.objects.first(); t = Template('{% load hospital_tags %}{% capacity_bar ward %}'); c = Context({'ward': ward}); try: rendered = t.render(c); print('Template tag renders successfully'); except Exception as e: print(f'Error: {e}')"
   ```

2. Create a test view to render the test template:

   ```python
   # In views.py
   from django.shortcuts import render
   from .models import Ward

   def test_ward_tags(request):
       wards = Ward.objects.select_related('hospital').all()
       return render(request, 'hospitals/tests/test_tags.html', {'wards': wards})
   ```

3. Add URL pattern for testing:

   ```python
   # In urls.py
   from django.urls import path
   from . import views

   urlpatterns = [
       # ... other patterns
       path('test/ward-tags/', views.test_ward_tags, name='test_ward_tags'),
   ]
   ```

4. Test in browser:

   ```bash
   python manage.py runserver
   ```

   Then visit <http://localhost:8000/hospitals/test/ward-tags/>

### Additional Recommendations

1. **For Template Tags**:

   - Add error handling for edge cases
   - Create additional tags for different visualization styles
   - Add accessibility attributes to generated HTML

2. **For Testing**:
   - Create unit tests for template tags
   - Test with various occupancy levels
   - Test with invalid inputs

## Vertical Slice 4: Ward Forms and Views

### Step 1: Verify Previous Slice Implementation

1. Confirm Ward model and template tags are working:

   ```bash
   python manage.py shell -c "from apps.hospitals.models import Ward; from django.template import Template, Context; ward = Ward.objects.first(); if ward: t = Template('{% load hospital_tags %}{% capacity_bar ward %}'); c = Context({'ward': ward}); print('Template tag test:', 'success' if t.render(c) else 'failed'); else: print('No wards found')"
   ```

2. Check URL configuration:

   ```bash
   python manage.py shell -c "from django.urls import reverse; try: print(reverse('hospitals:test_ward_tags')); except: print('URL not configured')"
   ```

### Step 2: Create Ward Forms

1. Create forms.py if it doesn't exist:

   ```python
   from django import forms
   from crispy_forms.helper import FormHelper
   from crispy_forms.layout import Layout, Fieldset, Submit, Row, Column
   from .models import Ward

   class WardForm(forms.ModelForm):
       class Meta:
           model = Ward
           fields = ['name', 'description', 'hospital', 'capacity', 'is_active']

       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.helper = FormHelper()
           self.helper.form_method = 'post'
           self.helper.layout = Layout(
               Fieldset(
                   'Ward Information',
                   Row(
                       Column('name', css_class='form-group col-md-6 mb-0'),
                       Column('hospital', css_class='form-group col-md-6 mb-0'),
                   ),
                   Row(
                       Column('capacity', css_class='form-group col-md-6 mb-0'),
                       Column('is_active', css_class='form-group col-md-6 mb-0'),
                   ),
                   'description',
               ),
               Submit('submit', 'Save', css_class='btn btn-primary mt-3')
           )
   ```

2. Verify form creation:

   ```bash
   python manage.py shell -c "from apps.hospitals.forms import WardForm; print(WardForm().fields)"
   ```

### Step 3: Create Ward Views

1. Update views.py with CRUD views:

   ```python
   from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
   from django.urls import reverse_lazy
   from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
   from .models import Ward
   from .forms import WardForm

   class WardListView(LoginRequiredMixin, ListView):
       model = Ward
       context_object_name = 'wards'

       def get_queryset(self):
           return Ward.objects.select_related('hospital').all()

   class WardDetailView(LoginRequiredMixin, DetailView):
       model = Ward

       def get_queryset(self):
           return Ward.objects.select_related('hospital')

   class WardCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
       model = Ward
       form_class = WardForm
       permission_required = 'hospitals.add_ward'

       def form_valid(self, form):
           form.instance.created_by = self.request.user
           form.instance.updated_by = self.request.user
           return super().form_valid(form)

       def get_success_url(self):
           return reverse_lazy('hospitals:ward_detail', kwargs={'pk': self.object.pk})

   class WardUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
       model = Ward
       form_class = WardForm
       permission_required = 'hospitals.change_ward'

       def form_valid(self, form):
           form.instance.updated_by = self.request.user
           return super().form_valid(form)

       def get_success_url(self):
           return reverse_lazy('hospitals:ward_detail', kwargs={'pk': self.object.pk})

   class WardDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
       model = Ward
       permission_required = 'hospitals.delete_ward'
       success_url = reverse_lazy('hospitals:ward_list')
   ```

2. Verify view imports:

   ```bash
   python manage.py shell -c "from apps.hospitals.views import WardListView, WardDetailView, WardCreateView, WardUpdateView, WardDeleteView; print('Views imported successfully')"
   ```

### Step 4: Create Templates

1. Create ward_list.html:

   ```html
   {% extends "base.html" %} {% load hospital_tags %} {% block title %}Wards{%
   endblock %} {% block content %}
   <div class="container mt-4">
     <div class="d-flex justify-content-between align-items-center mb-4">
       <h1>Wards</h1>
       {% if perms.hospitals.add_ward %}
       <a href="{% url 'hospitals:ward_create' %}" class="btn btn-primary">
         <i class="bi bi-plus-circle"></i> Add Ward
       </a>
       {% endif %}
     </div>

     {% if wards %}
     <div class="row">
       {% for ward in wards %}
       <div class="col-md-6 mb-4">
         <div class="card h-100">
           <div
             class="card-header d-flex justify-content-between align-items-center"
           >
             <h5 class="mb-0">{{ ward.name }}</h5>
             <span
               class="badge {% if ward.is_active %}bg-success{% else %}bg-danger{% endif %}"
             >
               {% if ward.is_active %}Active{% else %}Inactive{% endif %}
             </span>
           </div>
           <div class="card-body">
             <h6 class="card-subtitle mb-2 text-muted">
               {{ ward.hospital.name }}
             </h6>
             <p class="card-text">{{ ward.description|truncatewords:20 }}</p>
             <p>Capacity: {{ ward.capacity }} beds</p>
             {% capacity_bar ward %}
           </div>
           <div class="card-footer">
             <a
               href="{% url 'hospitals:ward_detail' ward.pk %}"
               class="btn btn-sm btn-outline-primary"
               >View Details</a
             >
           </div>
         </div>
       </div>
       {% endfor %}
     </div>
     {% else %}
     <div class="alert alert-info">
       No wards found. {% if perms.hospitals.add_ward %}Click the "Add Ward"
       button to create one.{% endif %}
     </div>
     {% endif %}
   </div>
   {% endblock %}
   ```

2. Create ward_detail.html, ward_form.html, and ward_confirm_delete.html templates.

3. Verify template existence:

   ```bash
   ls -la apps/hospitals/templates/hospitals/
   ```

### Step 5: Update URLs

1. Update urls.py:

   ```python
   from django.urls import path
   from . import views

   app_name = 'hospitals'

   urlpatterns = [
       # ... existing URLs
       path('wards/', views.WardListView.as_view(), name='ward_list'),
       path('wards/<int:pk>/', views.WardDetailView.as_view(), name='ward_detail'),
       path('wards/create/', views.WardCreateView.as_view(), name='ward_create'),
       path('wards/<int:pk>/update/', views.WardUpdateView.as_view(), name='ward_update'),
       path('wards/<int:pk>/delete/', views.WardDeleteView.as_view(), name='ward_delete'),
   ]
   ```

2. Verify URL configuration:

   ```bash
   python manage.py shell -c "from django.urls import reverse; try: print(reverse('hospitals:ward_list')); except Exception as e: print(f'Error: {e}')"
   ```

### Step 6: Basic Functionality Verification

1. Test URL resolution:

   ```bash
   python manage.py shell -c "from django.urls import reverse; print(reverse('hospitals:ward_list'), reverse('hospitals:ward_create'))"
   ```

2. Verify template loading:

   ```bash
   python manage.py shell -c "from django.template.loader import get_template; print(get_template('hospitals/ward_list.html'))"
   ```

3. Test view access:

   ```bash
   python manage.py runserver
   ```

   Then visit <http://localhost:8000/hospitals/wards/> in your browser.

4. Test form rendering:

   ```bash
   python manage.py shell -c "from apps.hospitals.forms import WardForm; form = WardForm(); print(form.as_p()[:100])"
   ```

### Additional Recommendations

1. **For Forms**:

   - Add custom validation for capacity limits
   - Add hospital filtering based on user permissions
   - Implement AJAX for dynamic hospital selection

2. **For Views**:

   - Add filtering options in list view
   - Implement pagination for large datasets
   - Add success messages after CRUD operations

3. **For Templates**:

   - Ensure responsive design works on all screen sizes
   - Add accessibility features (ARIA labels, keyboard navigation)
   - Implement consistent error message styling

4. **For Security**:
   - Test with different user permission levels
   - Verify proper redirect for unauthorized access
   - Implement object-level permissions if needed

## Vertical Slice 5: Ward API Endpoints

### Step 1: Verify Previous Slice Implementation

1. Confirm Ward views are working:

   ```bash
   python manage.py shell -c "from django.urls import reverse; from django.test import Client; c = Client(); response = c.get(reverse('hospitals:ward_list')); print(f'Status code: {response.status_code}')"
   ```

2. Check DRF installation:

   ```bash
   python manage.py shell -c "try: import rest_framework; print('DRF installed'); except ImportError: print('DRF not installed')"
   ```

### Step 2: Create Serializers

1. Create serializers.py:

   ```python
   from rest_framework import serializers
   from .models import Ward

   class WardSerializer(serializers.ModelSerializer):
       hospital_name = serializers.ReadOnlyField(source='hospital.name')
       patient_count = serializers.ReadOnlyField()
       occupancy_rate = serializers.ReadOnlyField()

       class Meta:
           model = Ward
           fields = ['id', 'name', 'description', 'hospital', 'hospital_name',
                     'capacity', 'is_active', 'patient_count', 'occupancy_rate',
                     'created_at', 'updated_at']
           read_only_fields = ['created_at', 'updated_at']
   ```

2. Verify serializer creation:

   ```bash
   python manage.py shell -c "from apps.hospitals.serializers import WardSerializer; print(WardSerializer().fields)"
   ```

### Step 3: Create API Views

1. Create api_views.py:

   ```python
   from rest_framework import viewsets, permissions
   from .models import Ward
   from .serializers import WardSerializer

   class WardViewSet(viewsets.ModelViewSet):
       queryset = Ward.objects.select_related('hospital').all()
       serializer_class = WardSerializer
       permission_classes = [permissions.IsAuthenticated]

       def perform_create(self, serializer):
           serializer.save(created_by=self.request.user, updated_by=self.request.user)

       def perform_update(self, serializer):
           serializer.save(updated_by=self.request.user)
   ```

2. Verify API view creation:

   ```bash
   python manage.py shell -c "from apps.hospitals.api_views import WardViewSet; print(WardViewSet.serializer_class)"
   ```

### Step 4: Configure API URLs

1. Update urls.py:

   ```python
   from django.urls import path, include
   from rest_framework.routers import DefaultRouter
   from . import views, api_views

   router = DefaultRouter()
   router.register(r'wards', api_views.WardViewSet)

   app_name = 'hospitals'

   urlpatterns = [
       # ... existing URLs
       path('api/', include(router.urls)),
   ]
   ```

2. Verify API URL configuration:

   ```bash
   python manage.py shell -c "from django.urls import reverse; try: print(reverse('hospitals:ward-list')); except Exception as e: print(f'Error: {e}')"
   ```

### Step 5: Basic Functionality Verification

1. Test API endpoint access:

   ```bash
   python manage.py runserver
   ```

   Then visit <http://localhost:8000/hospitals/api/wards/> in your browser.

2. Test API serialization:

   ```bash
   python manage.py shell -c "from apps.hospitals.serializers import WardSerializer; from apps.hospitals.models import Ward; ward = Ward.objects.first(); print(WardSerializer(ward).data if ward else 'No wards found')"
   ```

3. Test API authentication:

   ```bash
   python manage.py shell -c "from django.test import Client; from django.contrib.auth import get_user_model; User = get_user_model(); username='testuser'; password='testpass'; User.objects.filter(username=username).delete(); User.objects.create_user(username=username, password=password); c = Client(); logged_in = c.login(username=username, password=password); response = c.get('/hospitals/api/wards/'); print(f'Status: {response.status_code}, Authenticated: {logged_in}')"
   ```

### Additional Recommendations

1. **For API Design**:

   - Add filtering, searching, and ordering options
   - Implement pagination for large datasets
   - Add custom actions for specific operations

2. **For Security**:

   - Implement token or JWT authentication
   - Add rate limiting for API endpoints
   - Consider object-level permissions

3. **For Documentation**:

   - Add Swagger/OpenAPI documentation
   - Include example requests and responses
   - Document authentication requirements

4. **For Testing**:
   - Create API test cases for all endpoints
   - Test with different authentication scenarios
   - Verify proper error responses

## General Recommendations for All Slices

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

```

I've rewritten the wards implementation plan with comprehensive verification steps for each slice. Key improvements include:

1. Added app configuration verification steps at the beginning of each slice
2. Included Django shell commands to test model creation and functionality
3. Added steps to verify template rendering and URL configuration
4. Incorporated testing for both positive and negative cases
5. Added detailed recommendations for each slice focusing on:
   - Model design and data integrity
   - Performance optimization
   - Security considerations
   - Accessibility and responsive design
   - Form validation and error handling

The plan now follows a consistent pattern for each vertical slice:
1. Verify previous implementation
2. Implement new features
3. Basic functionality verification
4. Additional recommendations

This approach ensures that each slice is properly tested before moving to the next one, reducing the likelihood of encountering the testing issues mentioned in the testing_issues_analysis.md file.



```
