## Vertical Slice 4: Patient Views and URLs

### Step 1: Create Basic Views

1. Create views.py:

   ```python
   from django.shortcuts import render, redirect, get_object_or_404
   from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
   from django.urls import reverse_lazy
   from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
   from django.contrib.auth.decorators import login_required, permission_required
   from django.contrib import messages
   from .models import Patient, PatientHospitalRecord, AllowedTag
   from .forms import PatientForm, PatientHospitalRecordForm, AllowedTagForm

   # Patient views
   class PatientListView(LoginRequiredMixin, ListView):
       model = Patient
       template_name = 'patients/patient_list.html'
       context_object_name = 'patients'
       paginate_by = 10

       def get_queryset(self):
           queryset = super().get_queryset()
           query = self.request.GET.get('q')
           if query:
               queryset = queryset.filter(name__icontains=query)
           return queryset

   class PatientDetailView(LoginRequiredMixin, DetailView):
       model = Patient
       template_name = 'patients/patient_detail.html'
       context_object_name = 'patient'

   class PatientCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
       model = Patient
       form_class = PatientForm
       template_name = 'patients/patient_form.html'
       permission_required = 'patients.add_patient'

       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.pk})

       def form_valid(self, form):
           form.instance.created_by = self.request.user
           form.instance.updated_by = self.request.user
           messages.success(self.request, 'Patient created successfully.')
           return super().form_valid(form)

   class PatientUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
       model = Patient
       form_class = PatientForm
       template_name = 'patients/patient_form.html'
       permission_required = 'patients.change_patient'

       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.pk})

       def form_valid(self, form):
           form.instance.updated_by = self.request.user
           messages.success(self.request, 'Patient updated successfully.')
           return super().form_valid(form)

   class PatientDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
       model = Patient
       template_name = 'patients/patient_confirm_delete.html'
       success_url = reverse_lazy('patients:patient_list')
       permission_required = 'patients.delete_patient'

       def delete(self, request, *args, **kwargs):
           messages.success(request, 'Patient deleted successfully.')
           return super().delete(request, *args, **kwargs)

   # PatientHospitalRecord views
   class PatientHospitalRecordCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
       model = PatientHospitalRecord
       form_class = PatientHospitalRecordForm
       template_name = 'patients/hospital_record_form.html'
       permission_required = 'patients.add_patienthospitalrecord'

       def get_initial(self):
           initial = super().get_initial()
           initial['patient'] = get_object_or_404(Patient, pk=self.kwargs['patient_id'])
           return initial

       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.kwargs['patient_id']})

       def form_valid(self, form):
           form.instance.created_by = self.request.user
           form.instance.updated_by = self.request.user
           messages.success(self.request, 'Hospital record created successfully.')
           return super().form_valid(form)

   class PatientHospitalRecordUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
       model = PatientHospitalRecord
       form_class = PatientHospitalRecordForm
       template_name = 'patients/hospital_record_form.html'
       permission_required = 'patients.change_patienthospitalrecord'

       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})

       def form_valid(self, form):
           form.instance.updated_by = self.request.user
           messages.success(self.request, 'Hospital record updated successfully.')
           return super().form_valid(form)

   class PatientHospitalRecordDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
       model = PatientHospitalRecord
       template_name = 'patients/hospital_record_confirm_delete.html'
       permission_required = 'patients.delete_patienthospitalrecord'

       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})

       def delete(self, request, *args, **kwargs):
           messages.success(request, 'Hospital record deleted successfully.')
           return super().delete(request, *args, **kwargs)

   # AllowedTag views
   class AllowedTagListView(LoginRequiredMixin, ListView):
       model = AllowedTag
       template_name = 'patients/tag_list.html'
       context_object_name = 'tags'
       paginate_by = 20

   class AllowedTagCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
       model = AllowedTag
       form_class = AllowedTagForm
       template_name = 'patients/tag_form.html'
       success_url = reverse_lazy('patients:tag_list')
       permission_required = 'patients.add_allowedtag'

       def form_valid(self, form):
           messages.success(self.request, 'Tag created successfully.')
           return super().form_valid(form)

   class AllowedTagUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
       model = AllowedTag
       form_class = AllowedTagForm
       template_name = 'patients/tag_form.html'
       success_url = reverse_lazy('patients:tag_list')
       permission_required = 'patients.change_allowedtag'

       def form_valid(self, form):
           messages.success(self.request, 'Tag updated successfully.')
           return super().form_valid(form)

   class AllowedTagDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
       model = AllowedTag
       template_name = 'patients/tag_confirm_delete.html'
       success_url = reverse_lazy('patients:tag_list')
       permission_required = 'patients.delete_allowedtag'

       def delete(self, request, *args, **kwargs):
           messages.success(request, 'Tag deleted successfully.')
           return super().delete(request, *args, **kwargs)
   ```

### Step 2: Create URLs

1. Create urls.py:

   ```python
   from django.urls import path
   from . import views

   app_name = 'patients'

   urlpatterns = [
       # Patient URLs
       path('', views.PatientListView.as_view(), name='patient_list'),
       path('create/', views.PatientCreateView.as_view(), name='patient_create'),
       path('<uuid:pk>/', views.PatientDetailView.as_view(), name='patient_detail'),
       path('<uuid:pk>/update/', views.PatientUpdateView.as_view(), name='patient_update'),
       path('<uuid:pk>/delete/', views.PatientDeleteView.as_view(), name='patient_delete'),

       # Hospital record URLs
       path('<uuid:patient_id>/records/create/', views.PatientHospitalRecordCreateView.as_view(), name='record_create'),
       path('records/<uuid:pk>/update/', views.PatientHospitalRecordUpdateView.as_view(), name='record_update'),
       path('records/<uuid:pk>/delete/', views.PatientHospitalRecordDeleteView.as_view(), name='record_delete'),

       # Tag URLs
       path('tags/', views.AllowedTagListView.as_view(), name='tag_list'),
       path('tags/create/', views.AllowedTagCreateView.as_view(), name='tag_create'),
       path('tags/<int:pk>/update/', views.AllowedTagUpdateView.as_view(), name='tag_update'),
       path('tags/<int:pk>/delete/', views.AllowedTagDeleteView.as_view(), name='tag_delete'),
   ]
   ```

2. Include patient URLs in project urls.py:
   ```python
   # In config/urls.py
   path('patients/', include('apps.patients.urls', namespace='patients')),
   ```

### Step 3: Verify URL Configuration

1. Test URL resolution:

   ```bash
   python manage.py shell -c "from django.urls import reverse; print(reverse('patients:patient_list'))"
   ```

2. Verify URL patterns:
   ```bash
   python manage.py show_urls | grep patients
   ```

### Step 4: Add View Permissions

1. Ensure permission_required is added to all class-based views that modify data:

   ```python
   # Already implemented in the views above with PermissionRequiredMixin
   permission_required = 'patients.add_patient'  # Example for PatientCreateView
   ```

2. Add permission checks to templates:
   ```html
   {% if perms.patients.add_patient %}
   <a href="{% url 'patients:patient_create' %}" class="btn btn-primary"
     >Add Patient</a
   >
   {% endif %}
   ```

### Step 5: Verify App Configuration and Basic Functionality

1. Check app configuration:

   ```bash
   python manage.py check patients
   ```

2. Verify URL configuration:

   ```bash
   python manage.py shell -c "from django.urls import reverse; print(reverse('patients:patient_list'), reverse('patients:patient_create'))"
   ```

3. Test view class instantiation:

   ```bash
   python manage.py shell -c "from apps.patients.views import PatientListView; view = PatientListView(); print(f'View class: {view.__class__.__name__}')"
   ```

4. Verify template existence:

   ```bash
   python manage.py shell -c "from django.template.loader import get_template; print(get_template('patients/patient_list.html'))"
   ```

5. Test basic view access:
   ```bash
   python manage.py runserver
   ```
   Then visit http://localhost:8000/patients/ in your browser.

### Step 6: Test Views

1. Create test_views.py:

   ```python
   from django.test import TestCase
   from django.urls import reverse
   from django.contrib.auth import get_user_model
   from .models import Patient, PatientHospitalRecord, AllowedTag

   User = get_user_model()

   class PatientViewsTestCase(TestCase):
       def setUp(self):
           self.user = User.objects.create_user(
               username='testuser',
               email='test@example.com',
               password='testpassword'
           )
           self.patient = Patient.objects.create(
               name='Test Patient',
               birthday='1990-01-01',
               status=Patient.OUTPATIENT,
               created_by=self.user,
               updated_by=self.user
           )

       def test_patient_list_view(self):
           self.client.login(username='testuser', password='testpassword')
           response = self.client.get(reverse('patients:patient_list'))
           self.assertEqual(response.status_code, 200)
           self.assertTemplateUsed(response, 'patients/patient_list.html')
           self.assertContains(response, 'Test Patient')

       def test_patient_detail_view(self):
           self.client.login(username='testuser', password='testpassword')
           response = self.client.get(
               reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
           )
           self.assertEqual(response.status_code, 200)
           self.assertTemplateUsed(response, 'patients/patient_detail.html')
           self.assertEqual(response.context['patient'], self.patient)

       def test_patient_create_view(self):
           self.client.login(username='testuser', password='testpassword')
           self.user.user_permissions.add(
               Permission.objects.get(codename='add_patient')
           )
           response = self.client.get(reverse('patients:patient_create'))
           self.assertEqual(response.status_code, 200)
           self.assertTemplateUsed(response, 'patients/patient_form.html')

           # Test form submission
           data = {
               'name': 'New Patient',
               'birthday': '1995-05-05',
               'status': Patient.OUTPATIENT,
           }
           response = self.client.post(reverse('patients:patient_create'), data)
           self.assertEqual(Patient.objects.count(), 2)
           new_patient = Patient.objects.get(name='New Patient')
           self.assertRedirects(
               response,
               reverse('patients:patient_detail', kwargs={'pk': new_patient.pk})
           )

       def test_patient_update_view(self):
           self.client.login(username='testuser', password='testpassword')
           self.user.user_permissions.add(
               Permission.objects.get(codename='change_patient')
           )
           response = self.client.get(
               reverse('patients:patient_update', kwargs={'pk': self.patient.pk})
           )
           self.assertEqual(response.status_code, 200)
           self.assertTemplateUsed(response, 'patients/patient_form.html')

           # Test form submission
           data = {
               'name': 'Updated Patient',
               'birthday': '1990-01-01',
               'status': Patient.OUTPATIENT,
           }
           response = self.client.post(
               reverse('patients:patient_update', kwargs={'pk': self.patient.pk}),
               data
           )
           self.patient.refresh_from_db()
           self.assertEqual(self.patient.name, 'Updated Patient')
           self.assertRedirects(
               response,
               reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
           )

       def test_patient_delete_view(self):
           self.client.login(username='testuser', password='testpassword')
           self.user.user_permissions.add(
               Permission.objects.get(codename='delete_patient')
           )
           response = self.client.get(
               reverse('patients:patient_delete', kwargs={'pk': self.patient.pk})
           )
           self.assertEqual(response.status_code, 200)
           self.assertTemplateUsed(response, 'patients/patient_confirm_delete.html')

           # Test deletion
           response = self.client.post(
               reverse('patients:patient_delete', kwargs={'pk': self.patient.pk})
           )
           self.assertEqual(Patient.objects.count(), 0)
           self.assertRedirects(response, reverse('patients:patient_list'))

       def test_unauthenticated_access(self):
           # Test without login
           response = self.client.get(reverse('patients:patient_list'))
           self.assertRedirects(
               response,
               f'/accounts/login/?next={reverse("patients:patient_list")}'
           )

       def test_unauthorized_access(self):
           # Login but without permissions
           self.client.login(username='testuser', password='testpassword')
           response = self.client.post(reverse('patients:patient_create'), {
               'name': 'Unauthorized Patient',
               'birthday': '1990-01-01',
               'status': Patient.OUTPATIENT,
           })
           self.assertEqual(response.status_code, 403)  # Permission denied
   ```

2. Run view tests:
   ```bash
   python manage.py test apps.patients.tests.test_views
   ```

### Step 7: Test Form Submission

1. Create test_forms.py:

   ```python
   from django.test import TestCase
   from django.contrib.auth import get_user_model
   from .models import Patient, PatientHospitalRecord, AllowedTag
   from .forms import PatientForm, PatientHospitalRecordForm, AllowedTagForm

   User = get_user_model()

   class PatientFormsTestCase(TestCase):
       def setUp(self):
           self.user = User.objects.create_user(
               username='testuser',
               email='test@example.com',
               password='testpassword'
           )

       def test_patient_form_valid(self):
           form_data = {
               'name': 'Test Patient',
               'birthday': '1990-01-01',
               'status': Patient.OUTPATIENT,
           }
           form = PatientForm(data=form_data)
           self.assertTrue(form.is_valid())

       def test_patient_form_invalid(self):
           # Missing required field
           form_data = {
               'birthday': '1990-01-01',
               'status': Patient.OUTPATIENT,
           }
           form = PatientForm(data=form_data)
           self.assertFalse(form.is_valid())
           self.assertIn('name', form.errors)

       def test_hospital_record_form_valid(self):
           patient = Patient.objects.create(
               name='Test Patient',
               birthday='1990-01-01',
               status=Patient.OUTPATIENT,
               created_by=self.user,
               updated_by=self.user
           )
           hospital = Hospital.objects.create(name='Test Hospital')

           form_data = {
               'patient': patient.pk,
               'hospital': hospital.pk,
               'record_number': '12345',
               'admission_date': '2023-01-01',
           }
           form = PatientHospitalRecordForm(data=form_data)
           self.assertTrue(form.is_valid())

       def test_tag_form_valid(self):
           form_data = {
               'name': 'Test Tag',
               'slug': 'test-tag',
           }
           form = AllowedTagForm(data=form_data)
           self.assertTrue(form.is_valid())
   ```

2. Run form tests:
   ```bash
   python manage.py test apps.patients.tests.test_forms
   ```

## Additional Recommendations

1. **For All Slices**:

   - Always verify app configuration before running complex tests
   - Use Django shell for quick verification of model changes
   - Test both positive and negative cases (e.g., permissions denied)

2. **For Views**:

   - Test with authenticated and unauthenticated users
   - Verify proper redirect behavior for unauthorized access
   - Test with various user roles/permissions
   - Consider adding view mixins for common functionality

3. **For Forms**:

   - Test validation with both valid and invalid data
   - Verify error messages are displayed correctly
   - Test form submission with missing required fields
   - Consider adding custom form validation for complex business rules

4. **For Templates**:

   - Verify responsive design on different screen sizes
   - Test accessibility features
   - Ensure consistent styling with the rest of the application
   - Use template inheritance to maintain DRY principles

5. **For URL Configuration**:

   - Use namespaced URLs consistently
   - Test URL reversing in views and templates
   - Consider using path converters for complex URL patterns
   - Document URL patterns for API consumers

6. **For Permissions**:
   - Test permission checks at both view and template levels
   - Create permission groups for common user roles
   - Consider using a custom permission mixin for complex permission logic
   - Document permission requirements for each view

```

I've created the patient_implementation_plan_part4.md file with detailed steps for implementing the "Vertical Slice 4: Patient Views and URLs" section. The implementation includes:

1. Creating class-based views for all CRUD operations on Patient, PatientHospitalRecord, and AllowedTag models
2. Setting up URL patterns with proper namespacing
3. Adding permission requirements to views that modify data
4. Including verification steps to test URL configuration and basic functionality
5. Creating comprehensive test cases for views and forms
6. Adding additional recommendations for views, forms, templates, URL configuration, and permissions

The implementation follows Django best practices with class-based views, proper permission handling, and comprehensive testing. Each step builds logically on the previous ones, and verification steps are included to ensure everything works correctly before moving on.




```
