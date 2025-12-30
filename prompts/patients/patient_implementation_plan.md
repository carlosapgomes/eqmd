# Patients App Implementation Plan

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

### Step 2: Create AllowedTag and UUIDTaggedItem Models

1. Create the tag models in models.py:

````python path=apps/patients/models.py mode=EDIT
   import uuid
   from django.db import models
   from django.conf import settings
   from taggit.models import TagBase, GenericUUIDTaggedItemBase
   
   class AllowedTag(TagBase):
       class Meta:
           verbose_name = "Allowed Tag"
           verbose_name_plural = "Allowed Tags"
           ordering = ["name"]
   
   class UUIDTaggedItem(GenericUUIDTaggedItemBase):
       tag = models.ForeignKey(
           AllowedTag, on_delete=models.CASCADE, related_name="tagged_items"
       )
   
       class Meta:
           verbose_name = "Tag"
           verbose_name_plural = "Tags"
````

1. Test basic functionality:
   - Run Django shell to verify models
   - Create a test tag and verify it works

### Step 3: Create Patient Model

1. Add Patient model to models.py:

````python path=apps/patients/models.py mode=EDIT
   from taggit.managers import TaggableManager
   
   class Patient(models.Model):
       # Status choices
       OUTPATIENT = 1
       INPATIENT = 2
       EMERGENCY = 3
       DISCHARGED = 4
       TRANSFERRED = 5
       
       STATUS_CHOICES = [
           (OUTPATIENT, "Ambulatorial"),
           (INPATIENT, "Internado"),
           (EMERGENCY, "Emergência"),
           (DISCHARGED, "Alta"),
           (TRANSFERRED, "Transferido"),
       ]
       
       id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
       name = models.CharField(max_length=255, verbose_name="Nome")
       birthday = models.DateField(verbose_name="Data de Nascimento")
       healthcard_number = models.CharField(
           max_length=20, blank=True, verbose_name="Cartão de Saúde"
       )
       id_number = models.CharField(max_length=20, blank=True, verbose_name="RG")
       fiscal_number = models.CharField(max_length=20, blank=True, verbose_name="CPF")
       phone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
       address = models.CharField(max_length=255, blank=True, verbose_name="Endereço")
       city = models.CharField(max_length=50, blank=True, verbose_name="Cidade")
       state = models.CharField(max_length=2, blank=True, verbose_name="Estado")
       zip_code = models.CharField(max_length=10, blank=True, verbose_name="CEP")
   
       status = models.PositiveSmallIntegerField(
           choices=STATUS_CHOICES, default=OUTPATIENT, verbose_name="Status"
       )
       last_discharge_date = models.DateField(
           blank=True, null=True, verbose_name="Data da Última Alta"
       )
       last_admission_date = models.DateField(
           blank=True, null=True, verbose_name="Data da Última Admissão"
       )
       # Add direct hospital relationship
       current_hospital = models.ForeignKey(
           "hospitals.Hospital",
           on_delete=models.PROTECT,
           related_name="current_patients",
           null=True,
           blank=True,
           verbose_name="Hospital Atual",
       )
       # Use string reference for Ward model as it's not implemented yet
       ward = models.ForeignKey(
           "wards.Ward",
           on_delete=models.PROTECT,
           blank=True,
           null=True,
           verbose_name="Enfermaria",
       )
       bed = models.CharField(max_length=10, blank=True, verbose_name="Leito")
   
       created_at = models.DateTimeField(auto_now_add=True)
       created_by = models.ForeignKey(
           settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="patient_set"
       )
       updated_at = models.DateTimeField(auto_now=True)
       updated_by = models.ForeignKey(
           settings.AUTH_USER_MODEL,
           on_delete=models.PROTECT,
           related_name="patient_updated",
       )
   
       # Using TaggableManager with our custom UUIDTaggedItem
       tags = TaggableManager(through=UUIDTaggedItem, blank=True)
       
       # Add Patient model methods here
       @property
       def is_outpatient(self):
           """Check if patient is currently an outpatient"""
           return self.status == self.OUTPATIENT
           
       @property
       def is_inpatient(self):
           """Check if patient is currently an inpatient"""
           return self.status == self.INPATIENT
   
       def get_record_number(self, hospital=None):
           """Get patient's record number at specified hospital or current hospital"""
           if hospital is None and self.ward and hasattr(self.ward, 'hospital'):
               hospital = self.ward.hospital
   
           if hospital:
               record = self.hospital_records.filter(hospital=hospital).first()
               if record:
                   return record.record_number
           return None
   
       # Additional methods will be added in the next steps
````

1. Add remaining Patient model methods:

````python path=apps/patients/models.py mode=EDIT
       def set_record_number(self, hospital, record_number, user):
           """Set or update patient's record number at specified hospital"""
           record, created = PatientHospitalRecord.objects.get_or_create(
               patient=self,
               hospital=hospital,
               defaults={
                   "record_number": record_number,
                   "created_by": user,
                   "updated_by": user,
               },
           )
   
           if not created:
               record.record_number = record_number
               record.updated_by = user
               record.save(update_fields=["record_number", "updated_by", "updated_at"])
   
           return record
   
       def admit_to_hospital(
           self,
           hospital,
           ward=None,
           bed=None,
           record_number=None,
           admission_date=None,
           user=None,
       ):
           """Admit patient to a hospital, with optional ward/bed assignment"""
           if admission_date is None:
               from django.utils import timezone
   
               admission_date = timezone.now().date()
   
           # Update patient status and location
           self.status = self.INPATIENT
           self.current_hospital = hospital
           self.ward = ward
           self.bed = bed or ""
           self.last_admission_date = admission_date
   
           if user:
               self.updated_by = user
   
           self.save()
   
           # Update hospital record if record number provided
           if record_number and user:
               self.set_record_number(hospital, record_number, user)
   
           return self
   
       def discharge_from_hospital(self, discharge_date=None, user=None):
           """Discharge patient from current hospital"""
           if not self.is_inpatient:
               return None
   
           if discharge_date is None:
               from django.utils import timezone
   
               discharge_date = timezone.now().date()
   
           hospital = self.current_hospital
   
           # Update patient status
           self.status = self.OUTPATIENT
           self.last_discharge_date = discharge_date
           self.current_hospital = None
           self.ward = None
           self.bed = ""
   
           if user:
               self.updated_by = user
   
           self.save()
   
           # Update hospital record
           if hospital and user:
               record = self.hospital_records.filter(hospital=hospital).first()
               if record:
                   record.last_discharge_date = discharge_date
                   record.updated_by = user
                   record.save()
   
           return self
   
       def assign_ward(self, ward, bed=None, user=None):
           """Assign patient to a specific ward/bed within their current hospital"""
           if not self.is_inpatient:
               return False
   
           # Ensure ward belongs to current hospital
           if hasattr(ward, 'hospital') and ward.hospital != self.current_hospital:
               # Update current_hospital to match ward's hospital
               self.current_hospital = ward.hospital
   
           self.ward = ward
           if bed:
               self.bed = bed
   
           if user:
               self.updated_by = user
   
           self.save()
           return True
````

### Step 4: Create PatientHospitalRecord Model

1. Add PatientHospitalRecord model to models.py:

````python path=apps/patients/models.py mode=EDIT
   class PatientHospitalRecord(models.Model):
       """Tracks a patient's record numbers and history at different hospitals"""
   
       id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
       patient = models.ForeignKey(
           Patient,
           on_delete=models.CASCADE,
           related_name="hospital_records",
           verbose_name="Paciente",
       )
       hospital = models.ForeignKey(
           "hospitals.Hospital",
           on_delete=models.PROTECT,
           related_name="patient_records",
           verbose_name="Hospital",
       )
       record_number = models.CharField(max_length=30, verbose_name="Número de Registro")
       first_admission_date = models.DateField(
           null=True, blank=True, verbose_name="Data da Primeira Admissão"
       )
       last_admission_date = models.DateField(
           null=True, blank=True, verbose_name="Data da Última Admissão"
       )
       last_discharge_date = models.DateField(
           null=True, blank=True, verbose_name="Data da Última Alta"
       )
       created_at = models.DateTimeField(auto_now_add=True)
       created_by = models.ForeignKey(
           settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
       )
       updated_at = models.DateTimeField(auto_now=True)
       updated_by = models.ForeignKey(
           settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
       )
   
       class Meta:
           unique_together = ["patient", "hospital"]
           verbose_name = "Hospital Record"
           verbose_name_plural = "Hospital Records"
           indexes = [
               models.Index(fields=["patient", "hospital"]),
               models.Index(fields=["hospital", "record_number"]),
           ]
           
       def __str__(self):
           return f"{self.patient.name} - {self.hospital.name} ({self.record_number})"
````

1. Create migrations and verify models:

   ```bash
   python manage.py makemigrations patients
   python manage.py migrate
   ```

2. Test basic model functionality:
   - Use Django shell to create test instances
   - Verify relationships work correctly
   - Test model methods with simple cases

## Vertical Slice 2: Admin Interface for Patient Models

### Step 1: Register Models in Admin

1. Update admin.py:

````python path=apps/patients/admin.py mode=EDIT
   from django.contrib import admin
   from .models import Patient, PatientHospitalRecord, AllowedTag, UUIDTaggedItem
   
   @admin.register(AllowedTag)
   class AllowedTagAdmin(admin.ModelAdmin):
       list_display = ('name', 'slug')
       search_fields = ('name',)
       prepopulated_fields = {'slug': ('name',)}
   
   @admin.register(Patient)
   class PatientAdmin(admin.ModelAdmin):
       list_display = ('name', 'birthday', 'status', 'current_hospital', 'created_at')
       list_filter = ('status', 'current_hospital')
       search_fields = ('name', 'id_number', 'fiscal_number', 'healthcard_number')
       readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')
       fieldsets = (
           ('Personal Information', {
               'fields': ('name', 'birthday', 'healthcard_number', 'id_number', 
                          'fiscal_number', 'phone')
           }),
           ('Address', {
               'fields': ('address', 'city', 'state', 'zip_code')
           }),
           ('Hospital Status', {
               'fields': ('status', 'current_hospital', 'ward', 'bed', 
                          'last_admission_date', 'last_discharge_date')
           }),
           ('Tags', {
               'fields': ('tags',)
           }),
           ('System Information', {
               'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
               'classes': ('collapse',)
           }),
       )
       
       def save_model(self, request, obj, form, change):
           if not change:  # If creating a new object
               obj.created_by = request.user
           obj.updated_by = request.user
           super().save_model(request, obj, form, change)
   
   @admin.register(PatientHospitalRecord)
   class PatientHospitalRecordAdmin(admin.ModelAdmin):
       list_display = ('patient', 'hospital', 'record_number', 'created_at')
       list_filter = ('hospital',)
       search_fields = ('patient__name', 'record_number')
       readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')
       
       def save_model(self, request, obj, form, change):
           if not change:  # If creating a new object
               obj.created_by = request.user
           obj.updated_by = request.user
           super().save_model(request, obj, form, change)
````

1. Test admin interface:
   - Verify models appear in admin
   - Test creating and editing records
   - Verify all fields display correctly

### Step 2: Create Admin Customizations

1. Add inline admin for PatientHospitalRecord:

````python path=apps/patients/admin.py mode=EDIT
   class PatientHospitalRecordInline(admin.TabularInline):
       model = PatientHospitalRecord
       extra = 0
       readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')
       
       def has_add_permission(self, request, obj=None):
           return True
           
       def has_change_permission(self, request, obj=None):
           return True
   
   # Update PatientAdmin to include the inline
   @admin.register(Patient)
   class PatientAdmin(admin.ModelAdmin):
       # ... existing code ...
       inlines = [PatientHospitalRecordInline]
````

1. Test admin customizations:
   - Verify inline admin works correctly
   - Test adding hospital records through patient admin
   - Verify permissions work as expected

## Vertical Slice 3: Patient Forms and Basic Views

### Step 1: Create Patient Forms

1. Create forms.py:

````python path=apps/patients/forms.py mode=EDIT
   from django import forms
   from crispy_forms.helper import FormHelper
   from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML
   from .models import Patient, PatientHospitalRecord, AllowedTag
   
   class PatientForm(forms.ModelForm):
       class Meta:
           model = Patient
           fields = [
               'name', 'birthday', 'healthcard_number', 'id_number', 'fiscal_number',
               'phone', 'address', 'city', 'state', 'zip_code', 'status',
               'current_hospital', 'tags'
           ]
           # Ward field is excluded as it's not implemented yet
           
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.helper = FormHelper()
           self.helper.form_method = 'post'
           
           # Add Bootstrap classes to all fields
           for field_name, field in self.fields.items():
               field.widget.attrs['class'] = 'form-control'
               
           # Create layout with Bootstrap grid
           self.helper.layout = Layout(
               Fieldset(
                   'Personal Information',
                   Row(
                       Column('name', css_class='form-group col-md-6'),
                       Column('birthday', css_class='form-group col-md-6'),
                       css_class='form-row'
                   ),
                   Row(
                       Column('healthcard_number', css_class='form-group col-md-4'),
                       Column('id_number', css_class='form-group col-md-4'),
                       Column('fiscal_number', css_class='form-group col-md-4'),
                       css_class='form-row'
                   ),
                   Row(
                       Column('phone', css_class='form-group col-md-6'),
                       css_class='form-row'
                   ),
               ),
               Fieldset(
                   'Address',
                   Row(
                       Column('address', css_class='form-group col-md-12'),
                       css_class='form-row'
                   ),
                   Row(
                       Column('city', css_class='form-group col-md-5'),
                       Column('state', css_class='form-group col-md-3'),
                       Column('zip_code', css_class='form-group col-md-4'),
                       css_class='form-row'
                   ),
               ),
               Fieldset(
                   'Hospital Information',
                   Row(
                       Column('status', css_class='form-group col-md-6'),
                       Column('current_hospital', css_class='form-group col-md-6'),
                       css_class='form-row'
                   ),
               ),
               Fieldset(
                   'Tags',
                   'tags',
               ),
               Submit('submit', 'Save', css_class='btn btn-primary')
           )
   
   class PatientHospitalRecordForm(forms.ModelForm):
       class Meta:
           model = PatientHospitalRecord
           fields = ['hospital', 'record_number', 'first_admission_date', 
                    'last_admission_date', 'last_discharge_date']
           
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.helper = FormHelper()
           self.helper.form_method = 'post'
           
           # Add Bootstrap classes to all fields
           for field_name, field in self.fields.items():
               field.widget.attrs['class'] = 'form-control'
               
           self.helper.layout = Layout(
               Row(
                   Column('hospital', css_class='form-group col-md-6'),
                   Column('record_number', css_class='form-group col-md-6'),
                   css_class='form-row'
               ),
               Row(
                   Column('first_admission_date', css_class='form-group col-md-4'),
                   Column('last_admission_date', css_class='form-group col-md-4'),
                   Column('last_discharge_date', css_class='form-group col-md-4'),
                   css_class='form-row'
               ),
               Submit('submit', 'Save', css_class='btn btn-primary')
           )
   
   class AllowedTagForm(forms.ModelForm):
       class Meta:
           model = AllowedTag
           fields = ['name']
           
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.helper = FormHelper()
           self.helper.form_method = 'post'
           
           # Add Bootstrap classes
           self.fields['name'].widget.attrs['class'] = 'form-control'
           
           self.helper.layout = Layout(
               'name',
               Submit('submit', 'Save', css_class='btn btn-primary')
           )
````

### Step 2: Create Basic Views

1. Update views.py:

````python path=apps/patients/views.py mode=EDIT
   from django.shortcuts import render, redirect, get_object_or_404
   from django.contrib.auth.decorators import login_required
   from django.contrib import messages
   from django.urls import reverse_lazy
   from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
   from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
   
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
           # Add search functionality
           search_query = self.request.GET.get('search', '')
           if search_query:
               queryset = queryset.filter(name__icontains=search_query)
           return queryset
       
       def get_context_data(self, **kwargs):
           context = super().get_context_data(**kwargs)
           context['search_query'] = self.request.GET.get('search', '')
           return context
   
   class PatientDetailView(LoginRequiredMixin, DetailView):
       model = Patient
       template_name = 'patients/patient_detail.html'
       context_object_name = 'patient'
       
       def get_context_data(self, **kwargs):
           context = super().get_context_data(**kwargs)
           context['hospital_records'] = self.object.hospital_records.all()
           return context
   
   class PatientCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
       model = Patient
       form_class = PatientForm
       template_name = 'patients/patient_form.html'
       success_url = reverse_lazy('patients:patient_list')
       permission_required = 'patients.add_patient'
       
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
````

1. Add PatientHospitalRecord views:

````python path=apps/patients/views.py mode=EDIT
   # PatientHospitalRecord views
   class PatientHospitalRecordCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
       model = PatientHospitalRecord
       form_class = PatientHospitalRecordForm
       template_name = 'patients/hospital_record_form.html'
       permission_required = 'patients.add_patienthospitalrecord'
       
       def get_context_data(self, **kwargs):
           context = super().get_context_data(**kwargs)
           context['patient'] = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])
           return context
       
       def form_valid(self, form):
           patient = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])
           form.instance.patient = patient
           form.instance.created_by = self.request.user
           form.instance.updated_by = self.request.user
           messages.success(self.request, 'Hospital record created successfully.')
           return super().form_valid(form)
           
       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.kwargs['patient_pk']})
   
   class PatientHospitalRecordUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
       model = PatientHospitalRecord
       form_class = PatientHospitalRecordForm
       template_name = 'patients/hospital_record_form.html'
       permission_required = 'patients.change_patienthospitalrecord'
       
       def get_context_data(self, **kwargs):
           context = super().get_context_data(**kwargs)
           context['patient'] = self.object.patient
           return context
           
       def form_valid(self, form):
           form.instance.updated_by = self.request.user
           messages.success(self.request, 'Hospital record updated successfully.')
           return super().form_valid(form)
           
       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})
   
   class PatientHospitalRecordDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
       model = PatientHospitalRecord
       template_name = 'patients/hospital_record_confirm_delete.html'
       permission_required = 'patients.delete_patienthospitalrecord'
       
       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})
           
       def delete(self, request, *args, **kwargs):
           messages.success(request, 'Hospital record deleted successfully.')
           return super().delete(request, *args, **kwargs)
````

1. Add AllowedTag views:

````python path=apps/patients/views.py mode=EDIT
   # AllowedTag views
   class AllowedTagListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
       model = AllowedTag
       template_name = 'patients/tag_list.html'
       context_object_name = 'tags'
       permission_required = 'patients.view_allowedtag'
       
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
````

### Step 3: Create URL Patterns

1. Complete the urls.py file:

````python path=apps/patients/urls.py mode=EDIT
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
       
       # Hospital Record URLs
       path('<uuid:patient_pk>/records/create/', 
            views.PatientHospitalRecordCreateView.as_view(), 
            name='hospital_record_create'),
       path('records/<uuid:pk>/update/', 
            views.PatientHospitalRecordUpdateView.as_view(), 
            name='hospital_record_update'),
       path('records/<uuid:pk>/delete/', 
            views.PatientHospitalRecordDeleteView.as_view(), 
            name='hospital_record_delete'),
       
       # Tag URLs
       path('tags/', views.AllowedTagListView.as_view(), name='tag_list'),
       path('tags/create/', views.AllowedTagCreateView.as_view(), name='tag_create'),
       path('tags/<int:pk>/update/', views.AllowedTagUpdateView.as_view(), name='tag_update'),
       path('tags/<int:pk>/delete/', views.AllowedTagDeleteView.as_view(), name='tag_delete'),
   ]
````

1. Add the app URLs to the project's main urls.py:

````python path=config/urls.py mode=EDIT
   # Add to existing imports and urlpatterns
   path('patients/', include('apps.patients.urls')),
````

### Step 4: Verify App Configuration and Basic Functionality

1. Verify URL configuration:

   ```bash
   python manage.py shell -c "from django.urls import reverse; print(reverse('patients:patient_list'))"
   ```

2. Test view resolution:

   ```bash
   python manage.py shell -c "from django.urls.resolvers import get_resolver; resolver = get_resolver(); print('patients:patient_list' in resolver.reverse_dict)"
   ```

3. Verify model permissions:

   ```bash
   python manage.py shell -c "from django.contrib.auth.models import Permission; from django.contrib.contenttypes.models import ContentType; ct = ContentType.objects.get(app_label='patients', model='patient'); perms = Permission.objects.filter(content_type=ct); print([p.codename for p in perms])"
   ```

## Vertical Slice 4: Templates and Basic UI

### Step 1: Create Base Templates

1. Create patient_base.html:

````html path=templates/patients/patient_base.html mode=EDIT
{% extends "base_app.html" %}
{% load static %}

{% block title %}Patients Management{% endblock %}

{% block content %}
<div class="container-fluid">
  <div class="row">
    <div class="col-md-3 col-lg-2 d-md-block bg-light sidebar">
      <div class="position-sticky pt-3">
        <ul class="nav flex-column">
          <li class="nav-item">
            <a class="nav-link {% if request.resolver_match.url_name == 'patient_list' %}active{% endif %}" 
               href="{% url 'patients:patient_list' %}">
              <i class="bi bi-people"></i> All Patients
            </a>
          </li>
          <li class="nav-item">
            <a class="nav-link {% if request.resolver_match.url_name == 'patient_create' %}active{% endif %}" 
               href="{% url 'patients:patient_create' %}">
              <i class="bi bi-person-plus"></i> Add Patient
            </a>
          </li>
          <li class="nav-item">
            <a class="nav-link {% if request.resolver_match.url_name == 'tag_list' %}active{% endif %}" 
               href="{% url 'patients:tag_list' %}">
              <i class="bi bi-tags"></i> Manage Tags
            </a>
          </li>
        </ul>
      </div>
    </div>
    
    <main class="col-md-9 ms-sm-auto col-lg-10 px-md-4">
      <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
        <h1 class="h2">{% block page_title %}Patients{% endblock %}</h1>
        <div class="btn-toolbar mb-2 mb-md-0">
          {% block page_actions %}{% endblock %}
        </div>
      </div>
      
      {% if messages %}
        <div class="messages">
          {% for message in messages %}
            <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
              {{ message }}
              <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
          {% endfor %}
        </div>
      {% endif %}
      
      {% block patient_content %}{% endblock %}
    </main>
  </div>
</div>
{% endblock %}
````

### Step 2: Create Patient List Template

1. Create patient_list.html:

````html path=templates/patients/patient_list.html mode=EDIT
{% extends "patients/patient_base.html" %}
{% load static %}

{% block page_title %}Patient List{% endblock %}

{% block page_actions %}
  <a href="{% url 'patients:patient_create' %}" class="btn btn-sm btn-primary">
    <i class="bi bi-person-plus"></i> Add Patient
  </a>
{% endblock %}

{% block patient_content %}
  <div class="card mb-4">
    <div class="card-header bg-light">
      <form method="get" class="d-flex">
        <input type="text" name="search" class="form-control me-2" placeholder="Search patients..." 
               value="{{ search_query }}">
        <button type="submit" class="btn btn-outline-primary">Search</button>
        {% if search_query %}
          <a href="{% url 'patients:patient_list' %}" class="btn btn-outline-secondary ms-2">Clear</a>
        {% endif %}
      </form>
    </div>
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-hover table-striped mb-0">
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Hospital</th>
              <th>Birthday</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {% for patient in patients %}
              <tr>
                <td>
                  <a href="{% url 'patients:patient_detail' patient.pk %}">{{ patient.name }}</a>
                  {% if patient.tags.all %}
                    <div class="mt-1">
                      {% for tag in patient.tags.all %}
                        <span class="badge bg-info text-dark">{{ tag.name }}</span>
                      {% endfor %}
                    </div>
                  {% endif %}
                </td>
                <td>
                  {% if patient.status == 1 %}
                    <span class="badge bg-success">Ambulatorial</span>
                  {% elif patient.status == 2 %}
                    <span class="badge bg-primary">Internado</span>
                  {% elif patient.status == 3 %}
                    <span class="badge bg-danger">Emergência</span>
                  {% elif patient.status == 4 %}
                    <span class="badge bg-secondary">Alta</span>
                  {% elif patient.status == 5 %}
                    <span class="badge bg-warning text-dark">Transferido</span>
                  {% endif %}
                </td>
                <td>{{ patient.current_hospital|default:"-" }}</td>
                <td>{{ patient.birthday|date:"d/m/Y" }}</td>
                <td>
                  <div class="btn-group btn-group-sm">
                    <a href="{% url 'patients:patient_detail' patient.pk %}" class="btn btn-outline-primary">
                      <i class="bi bi-eye"></i>
                    </a>
                    <a href="{% url 'patients:patient_update' patient.pk %}" class="btn btn-outline-secondary">
                      <i class="bi bi-pencil"></i>
                    </a>
                  </div>
                </td>
              </tr>
            {% empty %}
              <tr>
                <td colspan="5" class="text-center py-4">
                  <div class="text-muted">
                    <i class="bi bi-search fs-3 d-block mb-3"></i>
                    No patients found.
                    {% if search_query %}
                      <div class="mt-2">
                        <a href="{% url 'patients:patient_list' %}" class="btn btn-sm btn-outline-primary">
                          Clear search
                        </a>
                      </div>
                    {% else %}
                      <div class="mt-2">
                        <a href="{% url 'patients:patient_create' %}" class="btn btn-sm btn-primary">
                          Add your first patient
                        </a>
                      </div>
                    {% endif %}
                  </div>
                </td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
  
  {% if is_paginated %}
    <nav aria-label="Page navigation">
      <ul class="pagination justify-content-center">
        {% if page_obj.has_previous %}
          <li class="page-item">
            <a class="page-link" href="?page=1{% if search_query %}&search={{ search_query }}{% endif %}">First</a>
          </li>
          <li class="page-item">
            <a class="page-link" href="?page={{ page_obj.previous_page_number }}{% if search_query %}&search={{ search_query }}{% endif %}">Previous</a>
          </li>
        {% else %}
          <li class="page-item disabled">
            <a class="page-link" href="#">First</a>
          </li>
          <li class="page-item disabled">
            <a class="page-link" href="#">Previous</a>
          </li>
        {% endif %}
        
        <li class="page-item active">
          <span class="page-link">
            Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}
          </span>
        </li>
        
        {% if page_obj.has_next %}
          <li class="page-item">
            <a class="page-link" href="?page={{ page_obj.next_page_number }}{% if search_query %}&search={{ search_query }}{% endif %}">Next</a>
          </li>
          <li class="page-item">
            <a class="page-link" href="?page={{ page_obj.paginator.num_pages }}{% if search_query %}&search={{ search_query }}{% endif %}">Last</a>
          </li>
        {% else %}
          <li class="page-item disabled">
            <a class="page-link" href="#">Next</a>
          </li>
          <li class="page-item disabled">
            <a class="page-link" href="#">Last</a>
          </li>
        {% endif %}
      </ul>
    </nav>
  {% endif %}
{% endblock %}
````

### Step 3: Create Patient Detail Template

1. Create patient_detail.html:

````html path=templates/patients/patient_detail.html mode=EDIT
{% extends "patients/patient_base.html" %}
{% load static %}

{% block page_title %}Patient Details{% endblock %}

{% block page_actions %}
  <div class="btn-group">
    <a href="{% url 'patients:patient_update' patient.pk %}" class="btn btn-sm btn-outline-secondary">
      <i class="bi bi-pencil"></i> Edit
    </a>
    <a href="{% url 'patients:patient_delete' patient.pk %}" class="btn btn-sm btn-outline-danger">
      <i class="bi bi-trash"></i> Delete
    </a>
  </div>
{% endblock %}

{% block patient_content %}
  <div class="row">
    <div class="col-md-8">
      <div class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
          <h5 class="mb-0">Personal Information</h5>
          <a href="{% url 'patients:patient_update' patient.pk %}" class="btn btn-sm btn-outline-secondary">
            <i class="bi bi-pencil"></i> Edit
          </a>
        </div>
        <div class="card-body">
          <div class="row mb-3">
            <div class="col-md-6">
              <h6 class="text-muted">Name</h6>
              <p class="mb-0">{{ patient.name }}</p>
            </div>
            <div class="col-md-6">
              <h6 class="text-muted">Birthday</h6>
              <p class="mb-0">{{ patient.birthday|date:"d/m/Y" }}</p>
            </div>
          </div>
          
          <div class="row mb-3">
            <div class="col-md-4">
              <h6 class="text-muted">Health Card</h6>
              <p class="mb-0">{{ patient.healthcard_number|default:"-" }}</p>
            </div>
            <div class="col-md-4">
              <h6 class="text-muted">ID Number</h6>
              <p class="mb-0">{{ patient.id_number|default:"-" }}</p>
            </div>
            <div class="col-md-4">
              <h6 class="text-muted">Fiscal Number</h6>
              <p class="mb-0">{{ patient.fiscal_number|default:"-" }}</p>
            </div>
          </div>
          
          <div class="row mb-3">
            <div class="col-md-6">
              <h6 class="text-muted">Phone</h6>
              <p class="mb-0">{{ patient.phone|default:"-" }}</p>
            </div>
          </div>
          
          <h6 class="text-muted">Address</h6>
          <p class="mb-1">{{ patient.address|default:"-" }}</p>
          <p class="mb-0">
            {% if patient.city or patient.state or patient.zip_code %}
              {{ patient.city }}{% if patient.city and patient.state %}, {% endif %}
              {{ patient.state }} {{ patient.zip_code }}
            {% else %}
              -
            {% endif %}
          </p>
        </div>
      </div>
      
      <div class="card mb-4">
        <div class="card-header">
          <h5 class="mb-0">Hospital Records</h5>
        </div>
        <div class="card-body p-0">
          <div class="table-responsive">
            <table class="table table-hover mb-0">
              <thead>
                <tr>
                  <th>Hospital</th>
                  <th>Record Number</th>
                  <th>First Admission</th>
                  <th>Last Admission</th>
                  <th>Last Discharge</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {% for record in hospital_records %}
                  <tr>
                    <td>{{ record.hospital.name }}</td>
                    <td>{{ record.record_number }}</td>
                    <td>{{ record.first_admission_date|date:"d/m/Y"|default:"-" }}</td>
                    <td>{{ record.last_admission_date|date:"d/m/Y"|default:"-" }}</td>
                    <td>{{ record.last_discharge_date|date:"d/m/Y"|default:"-" }}</td>
                    <td>
                      <div class="btn-group btn-group-sm">
                        <a href="{% url 'patients:hospital_record_update' record.pk %}" class="btn btn-outline-secondary">
                          <i class="bi bi-pencil"></i>
                        </a>
                        <a href="{% url 'patients:hospital_record_delete' record.pk %}" class="btn btn-outline-danger">
                          <i class="bi bi-trash"></i>
                        </a>
                      </div>
                    </td>
                  </tr>
                {% empty %}
                  <tr>
                    <td colspan="6" class="text-center py-3">
                      <div class="text-muted">
                        <i class="bi bi-hospital fs-3 d-block mb-2"></i>
                        No hospital records found
                      </div>
                      <a href="{% url 'patients:hospital_record_create' patient.pk %}" class="btn btn-sm btn-primary mt-2">
                        <i class="bi bi-plus-circle"></i> Add Hospital Record
                      </a>
                    </td>
                  </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
        <div class="card-footer bg-white">
          <a href="{% url 'patients:hospital_record_create' patient.pk %}" class="btn btn-primary">
            <i class="bi bi-plus-circle"></i> Add Hospital Record
          </a>
        </div>
      </div>
    </div>
    
    <div class="col-md-4">
      <div class="card mb-4">
        <div class="card-header">
          <h5 class="mb-0">Hospital Status</h5>
        </div>
        <div class="card-body">
          <div class="mb-3">
            <h6 class="text-muted">Current Status</h6>
            <p class="mb-0">
              {% if patient.status == 1 %}
                <span class="badge bg-success">Ambulatorial</span>
              {% elif patient.status == 2 %}
                <span class="badge bg-primary">Internado</span>
              {% elif patient.status == 3 %}
                <span class="badge bg-danger">Emergência</span>
              {% elif patient.status == 4 %}
                <span class="badge bg-secondary">Alta</span>
              {% elif patient.status == 5 %}
                <span class="badge bg-warning text-dark">Transferido</span>
              {% endif %}
            </p>
          </div>
          
          <div class="mb-3">
            <h6 class="text-muted">Current Hospital</h6>
            <p class="mb-0">{{ patient.current_hospital|default:"-" }}</p>
          </div>
          
          <div class="mb-3">
            <h6 class="text-muted">Ward</h6>
            <p class="mb-0">{{ patient.ward|default:"-" }}</p>
          </div>
          
          <div class="mb-3">
            <h6 class="text-muted">Bed</h6>
            <p class="mb-0">{{ patient.bed|default:"-" }}</p>
          </div>
          
          <div class="mb-3">
            <h6 class="text-muted">Last Admission Date</h6>
            <p class="mb-0">{{ patient.last_admission_date|date:"d/m/Y"|default:"-" }}</p>
          </div>
          
          <div class="mb-3">
            <h6 class="text-muted">Last Discharge Date</h6>
            <p class="mb-0">{{ patient.last_discharge_date|date:"d/m/Y"|default:"-" }}</p>
          </div>
        </div>
      </div>
      
      <div class="card mb-4">
        <div class="card-header">
          <h5 class="mb-0">Tags</h5>
        </div>
        <div class="card-body">
          {% for tag in patient.tags.all %}
            <span class="badge bg-info text-dark mb-1">{{ tag.name }}</span>
          {% empty %}
            <p class="text-muted mb-0">No tags assigned</p>
          {% endfor %}
        </div>
        <div class="card-footer bg-white">
          <a href="{% url 'patients:patient_update' patient.pk %}" class="btn btn-sm btn-outline-secondary">
            <i class="bi bi-pencil"></i> Edit Tags
          </a>
        </div>
      </div>
      
      <div class="card mb-4">
        <div class="card-header">
          <h5 class="mb-0">System Information</h5>
        </div>
        <div class="card-body">
          <div class="mb-3">
            <h6 class="text-muted">Created By</h6>
            <p class="mb-0">{{ patient.created_by.get_full_name|default:patient.created_by }}</p>
          </div>
          
          <div class="mb-3">
            <h6 class="text-muted">Created At</h6>
            <p class="mb-0">{{ patient.created_at|date:"d/m/Y H:i" }}</p>
          </div>
          
          <div class="mb-3">
            <h6 class="text-muted">Last Updated By</h6>
            <p class="mb-0">{{ patient.updated_by.get_full_name|default:patient.updated_by }}</p>
          </div>
          
          <div class="mb-3">
            <h6 class="text-muted">Last Updated At</h6>
            <p class="mb-0">{{ patient.updated_at|date:"d/m/Y H:i" }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
{% endblock %}
````

### Step 4: Create Form Templates

1. Create patient_form.html:

````html path=templates/patients/patient_form.html mode=EDIT
{% extends "patients/patient_base.html" %}
{% load crispy_forms_tags %}

{% block page_title %}
  {% if form.instance.pk %}Edit Patient{% else %}Add New Patient{% endif %}
{% endblock %}

{% block page_actions %}
  {% if form.instance.pk %}
    <a href="{% url 'patients:patient_detail' form.instance.pk %}" class="btn btn-sm btn-outline-secondary">
      <i class="bi bi-arrow-left"></i> Back to Details
    </a>
  {% else %}
    <a href="{% url 'patients:patient_list' %}" class="btn btn-sm btn-outline-secondary">
      <i class="bi bi-arrow-left"></i> Back to List
    </a>
  {% endif %}
{% endblock %}

{% block patient_content %}
  <div class="card">
    <div class="card-header">
      <h5 class="mb-0">
        {% if form.instance.pk %}Edit Patient Information{% else %}New Patient Information{% endif %}
      </h5>
    </div>
    <div class="card-body">
      {% crispy form %}
    </div>
  </div>
{% endblock %}
````

1. Create hospital_record_form.html:

````html path=templates/patients/hospital_record_form.html mode=EDIT
{% extends "patients/patient_base.html" %}
{% load crispy_forms_tags %}

{% block page_title %}
  {% if form.instance.pk %}
    Edit Hospital Record
  {% else %}
    Add Hospital Record
  {% endif %}
{% endblock %}

{% block page_actions %}
  <a href="{% url 'patients:patient_detail' patient.pk %}" class="btn btn-sm btn-outline-secondary">
    <i class="bi bi-arrow-left"></i> Back to Patient
  </a>
{% endblock %}

{% block patient_content %}
  <div class="card">
    <div class="card-header">
      <h5 class="mb-0">
        {% if form.instance.pk %}
          Edit Hospital Record for {{ patient.name }}
        {% else %}
          New Hospital Record for {{ patient.name }}
        {% endif %}
      </h5>
    </div>
    <div class="card-body">
      {% crispy form %}
    </div>
  </div>
{% endblock %}
````

1. Create confirmation templates:

````html path=templates/patients/patient_confirm_delete.html mode=EDIT
{% extends "patients/patient_base.html" %}

{% block page_title %}Delete Patient{% endblock %}

{% block page_actions %}
  <a href="{% url 'patients:patient_detail' patient.pk %}" class="btn btn-sm btn-outline-secondary">
    <i class="bi bi-arrow-left"></i> Back to Details
  </a>
{% endblock %}

{% block patient_content %}
  <div class="card border-danger">
    <div class="card-header bg-danger text-white">
      <h5 class="mb-0">Confirm Deletion</h5>
    </div>
    <div class="card-body">
      <p class="mb-0">
        Are you sure you want to delete the patient <strong>{{ patient.name }}</strong>?
        This action cannot be undone.
      </p>
      
      <div class="alert alert-warning mt-3">
        <i class="bi bi-exclamation-triangle-fill"></i>
        This will also delete all hospital records associated with this patient.
      </div>
      
      <form method="post" class="mt-4">
        {% csrf_token %}
        <div class="d-flex">
          <a href="{% url 'patients:patient_detail' patient.pk %}" class="btn btn-secondary me-2">
            Cancel
          </a>
          <button type="submit" class="btn btn-danger">
            <i class="bi bi-trash"></i> Delete Patient
          </button>
        </div>
      </form>
    </div>
  </div>
{% endblock %}
````

````html path=templates/patients/hospital_record_confirm_delete.html mode=EDIT
{% extends "patients/patient_base.html" %}

{% block page_title %}Delete Hospital Record{% endblock %}

{% block page_actions %}
  <a href="{% url 'patients:patient_detail' object.patient.pk %}" class="btn btn-sm btn-outline-secondary">
    <i class="bi bi-arrow-left"></i> Back to Patient
  </a>
{% endblock %}

{% block patient_content %}
  <div class="card border-danger">
    <div class="card-header bg-danger text-white">
      <h5 class="mb-0">Confirm Deletion</h5>
    </div>
    <div class="card-body">
      <p class="mb-0">
        Are you sure you want to delete the hospital record for 
        <strong>{{ object.patient.name }}</strong> at <strong>{{ object.hospital.name }}</strong>?
        This action cannot be undone.
      </p>
      
      <form method="post" class="mt-4">
        {% csrf_token %}
        <div class="d-flex">
          <a href="{% url 'patients:patient_detail' object.patient.pk %}" class="btn btn-secondary me-2">
            Cancel
          </a>
          <button type="submit" class="btn btn-danger">
            <i class="bi bi-trash"></i> Delete Record
          </button>
        </div>
      </form>
    </div>
  </div>
{% endblock %}
````

### Step 5: Create Tag Templates

1. Create tag_list.html:

````html path=templates/patients/tag_list.html mode=EDIT
{% extends "patients/patient_base.html" %}

{% block page_title %}Manage Tags{% endblock %}

{% block page_actions %}
  <a href="{% url 'patients:tag_create' %}" class="btn btn-sm btn-primary">
    <i class="bi bi-plus-circle"></i> Add Tag
  </a>
{% endblock %}

{% block patient_content %}
  <div class="card">
    <div class="card-header">
      <h5 class="mb-0">Available Tags</h5>
    </div>
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-hover mb-0">
          <thead>
            <tr>
              <th>Name</th>
              <th>Slug</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {% for tag in tags %}
              <tr>
                <td>
                  <span class="badge bg-info text-dark">{{ tag.name }}</span>
                </td>
                <td>{{ tag.slug }}</td>
                <td>
                  <div class="btn-group btn-group-sm">
                    <a href="{% url 'patients:tag_update' tag.pk %}" class="btn btn-outline-secondary">
                      <i class="bi bi-pencil"></i>
                    </a>
                    <a href="{% url 'patients:tag_delete' tag.pk %}" class="btn btn-outline-danger">
                      <i class="bi bi-trash"></i>
                    </a>
                  </div>
                </td>
              </tr>
            {% empty %}
              <tr>
                <td colspan="3" class="text-center py-4">
                  <div class="text-muted">
                    <i class="bi bi-tags fs-3 d-block mb-3"></i>
                    No tags defined yet.
                    <div class="mt-2">
                      <a href="{% url 'patients:tag_create' %}" class="btn btn-sm btn-primary">
                        Add your first tag
                      </a>
                    </div>
                  </div>
                </td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
{% endblock %}
````

1. Create tag_form.html:

````html path=templates/patients/tag_form.html mode=EDIT
    <div class="card-body">
      {% crispy form %}
    </div>
  </div>
{% endblock %}
````

1. Create tag_confirm_delete.html:

````html path=templates/patients/tag_confirm_delete.html mode=EDIT
{% extends "patients/patient_base.html" %}

{% block page_title %}Delete Tag{% endblock %}

{% block page_actions %}
  <a href="{% url 'patients:tag_list' %}" class="btn btn-sm btn-outline-secondary">
    <i class="bi bi-arrow-left"></i> Back to Tags
  </a>
{% endblock %}

{% block patient_content %}
  <div class="card border-danger">
    <div class="card-header bg-danger text-white">
      <h5 class="mb-0">Confirm Deletion</h5>
    </div>
    <div class="card-body">
      <p class="mb-0">
        Are you sure you want to delete the tag <strong>{{ tag.name }}</strong>?
        This action cannot be undone.
      </p>
      
      <div class="alert alert-warning mt-3">
        <i class="bi bi-exclamation-triangle-fill"></i>
        This will remove this tag from all patients that currently have it.
      </div>
      
      <form method="post" class="mt-4">
        {% csrf_token %}
        <div class="d-flex">
          <a href="{% url 'patients:tag_list' %}" class="btn btn-secondary me-2">
            Cancel
          </a>
          <button type="submit" class="btn btn-danger">
            <i class="bi bi-trash"></i> Delete Tag
          </button>
        </div>
      </form>
    </div>
  </div>
{% endblock %}
````

## Vertical Slice 5: Tests and Documentation

### Step 1: Create Model Tests

1. Create test_models.py:

````python path=apps/patients/tests/test_models.py mode=EDIT
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.patients.models import Patient, PatientHospitalRecord, AllowedTag
from apps.hospitals.models import Hospital, Ward

User = get_user_model()

class PatientModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a test hospital
        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            code='TEST01',
            created_by=cls.user,
            updated_by=cls.user
        )
        
        # Create a test ward
        cls.ward = Ward.objects.create(
            name='Test Ward',
            code='TW01',
            hospital=cls.hospital,
            created_by=cls.user,
            updated_by=cls.user
        )
        
        # Create a test tag
        cls.tag = AllowedTag.objects.create(
            name='Test Tag',
            slug='test-tag'
        )
        
        # Create a test patient
        cls.patient = Patient.objects.create(
            name='John Doe',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.patient.tags.add(cls.tag)
        
        # Create a test hospital record
        cls.hospital_record = PatientHospitalRecord.objects.create(
            patient=cls.patient,
            hospital=cls.hospital,
            record_number='REC123',
            created_by=cls.user,
            updated_by=cls.user
        )
    
    def test_patient_creation(self):
        """Test that a patient can be created with proper attributes"""
        self.assertEqual(self.patient.name, 'John Doe')
        self.assertEqual(self.patient.birthday.strftime('%Y-%m-%d'), '1980-01-01')
        self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)
        self.assertEqual(self.patient.created_by, self.user)
        self.assertEqual(self.patient.updated_by, self.user)
        
    def test_patient_str(self):
        """Test the string representation of a patient"""
        self.assertEqual(str(self.patient), 'John Doe')
    
    def test_patient_tags(self):
        """Test that tags can be added to a patient"""
        self.assertEqual(self.patient.tags.count(), 1)
        self.assertEqual(self.patient.tags.first().name, 'Test Tag')
    
    def test_hospital_record_creation(self):
        """Test that a hospital record can be created with proper attributes"""
        self.assertEqual(self.hospital_record.patient, self.patient)
        self.assertEqual(self.hospital_record.hospital, self.hospital)
        self.assertEqual(self.hospital_record.record_number, 'REC123')
    
    def test_hospital_record_str(self):
        """Test the string representation of a hospital record"""
        expected = f'John Doe at Test Hospital (REC123)'
        self.assertEqual(str(self.hospital_record), expected)
    
    def test_tag_creation(self):
        """Test that a tag can be created with proper attributes"""
        self.assertEqual(self.tag.name, 'Test Tag')
        self.assertEqual(self.tag.slug, 'test-tag')
    
    def test_tag_str(self):
        """Test the string representation of a tag"""
        self.assertEqual(str(self.tag), 'Test Tag')
    
    def test_patient_current_hospital(self):
        """Test the current_hospital property of a patient"""
        # Set the patient's current hospital
        self.patient.current_hospital = self.hospital
        self.patient.save()
        
        # Refresh from database
        self.patient.refresh_from_db()
        
        self.assertEqual(self.patient.current_hospital, self.hospital)
    
    def test_patient_ward_assignment(self):
        """Test that a patient can be assigned to a ward"""
        # Assign the patient to a ward
        self.patient.ward = self.ward
        self.patient.save()
        
        # Refresh from database
        self.patient.refresh_from_db()
        
        self.assertEqual(self.patient.ward, self.ward)
````

### Step 2: Create Form Tests

1. Create test_forms.py:

````python path=apps/patients/tests/test_forms.py mode=EDIT
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.patients.forms import PatientForm, PatientHospitalRecordForm, AllowedTagForm
from apps.patients.models import Patient, AllowedTag
from apps.hospitals.models import Hospital

User = get_user_model()

class PatientFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a test tag
        cls.tag = AllowedTag.objects.create(
            name='Test Tag',
            slug='test-tag'
        )
    
    def test_patient_form_valid_data(self):
        """Test that the patient form works with valid data"""
        form_data = {
            'name': 'Jane Doe',
            'birthday': '1990-05-15',
            'status': Patient.Status.OUTPATIENT,
            'healthcard_number': 'HC123456',
            'id_number': 'ID789012',
            'fiscal_number': 'FN345678',
            'phone': '555-123-4567',
            'address': '123 Main St',
            'city': 'Anytown',
            'state': 'ST',
            'zip_code': '12345',
            'tags': [self.tag.id],
        }
        
        form = PatientForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_patient_form_invalid_data(self):
        """Test that the patient form validates required fields"""
        form_data = {
            # Missing required name field
            'birthday': '1990-05-15',
            'status': Patient.Status.OUTPATIENT,
        }
        
        form = PatientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_patient_form_future_birthday(self):
        """Test that the patient form validates birthday is not in the future"""
        future_date = '2099-01-01'
        form_data = {
            'name': 'Future Person',
            'birthday': future_date,
            'status': Patient.Status.OUTPATIENT,
        }
        
        form = PatientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('birthday', form.errors)

class PatientHospitalRecordFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a test hospital
        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            code='TEST01',
            created_by=cls.user,
            updated_by=cls.user
        )
        
        # Create a test patient
        cls.patient = Patient.objects.create(
            name='John Doe',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )
    
    def test_hospital_record_form_valid_data(self):
        """Test that the hospital record form works with valid data"""
        form_data = {
            'hospital': self.hospital.id,
            'record_number': 'REC123456',
            'first_admission_date': '2023-01-15',
            'last_admission_date': '2023-02-20',
            'last_discharge_date': '2023-02-25',
            'notes': 'Test notes',
        }
        
        form = PatientHospitalRecordForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_hospital_record_form_invalid_data(self):
        """Test that the hospital record form validates required fields"""
        form_data = {
            # Missing required hospital field
            'record_number': 'REC123456',
        }
        
        form = PatientHospitalRecordForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('hospital', form.errors)
    
    def test_hospital_record_form_date_validation(self):
        """Test that the hospital record form validates date order"""
        form_data = {
            'hospital': self.hospital.id,
            'record_number': 'REC123456',
            'first_admission_date': '2023-03-15',  # Later than last_admission_date
            'last_admission_date': '2023-02-20',
            'last_discharge_date': '2023-02-25',
        }
        
        form = PatientHospitalRecordForm(data=form_data)
        self.assertFalse(form.is_valid())
        # Check that there's an error about date order

class AllowedTagFormTest(TestCase):
    def test_tag_form_valid_data(self):
        """Test that the tag form works with valid data"""
        form_data = {
            'name': 'New Tag',
            'slug': 'new-tag',
        }
        
        form = AllowedTagForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_tag_form_invalid_data(self):
        """Test that the tag form validates required fields"""
        form_data = {
            # Missing required name field
            'slug': 'new-tag',
        }
        
        form = AllowedTagForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_tag_form_auto_slug(self):
        """Test that the tag form auto-generates a slug if not provided"""
        form_data = {
            'name': 'Auto Slug Test',
            # No slug provided
        }
        
        form = AllowedTagForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Save the form to create the tag
        tag = form.save()
        
        # Check that a slug was auto-generated
        self.assertEqual(tag.slug, 'auto-slug-test')
````

### Step 3: Create View Tests

1. Create test_views.py:

````python path=apps/patients/tests/test_views.py mode=EDIT
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.patients.models import Patient, PatientHospitalRecord, AllowedTag
from apps.hospitals.models import Hospital

User = get_user_model()

class PatientViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a test hospital
        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            code='TEST01',
            created_by=cls.user,
            updated_by=cls.user
        )
        
        # Create a test tag
        cls.tag = AllowedTag.objects.create(
            name='Test Tag',
            slug='test-tag'
        )
        
        # Create test patients
        for i in range(5):
            patient = Patient.objects.create(
                name=f'Patient {i}',
                birthday='1980-01-01',
                status=Patient.Status.OUTPATIENT,
                created_by=cls.user,
                updated_by=cls.user
            )
            
            # Add tag to some patients
            if i % 2 == 0:
                patient.tags.add(cls.tag)
            
            # Create hospital record for each patient
            PatientHospitalRecord.objects.create(
                patient=patient,
                hospital=cls.hospital,
                record_number=f'REC{i}',
                created_by=cls.user,
                updated_by=cls.user
            )
    
    def setUp(self):
        # Log in for each test
        self.client.login(username='testuser', password='testpass123')
    
    def test_patient_list_view(self):
        """Test that the patient list view displays all patients"""
        url = reverse('patients:patient_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/patient_list.html')
        self.assertEqual(len(response.context['patients']), 5)
    
    def test_patient_detail_view(self):
        """Test that the patient detail view displays patient information"""
        patient = Patient.objects.first()
        url = reverse('patients:patient_detail', args=[patient.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/patient_detail.html')
        self.assertEqual(response.context['patient'], patient)
        
        # Check that hospital records are included
        self.assertIn('hospital_records', response.context)
        self.assertEqual(len(response.context['hospital_records']), 1)
    
    def test_patient_create_view(self):
        """Test that the patient create view works"""
        url = reverse('patients:patient_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/patient_form.html')
        
        # Test POST request
        patient_count = Patient.objects.count()
        post_data = {
            'name': 'New Patient',
            'birthday': '1990-05-15',
            'status': Patient.Status.OUTPATIENT,
            'tags': [self.tag.id],
        }
        
        response = self.client.post(url, post_data)
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Check that a new patient was created
        self.assertEqual(Patient.objects.count(), patient_count + 1)
        
        # Check that the new patient has the correct data
        new_patient = Patient.objects.latest('created_at')
        self.assertEqual(new_patient.name, 'New Patient')
        self.assertEqual(new_patient.tags.first(), self.tag)
    
    def test_patient_update_view(self):
        """Test that the patient update view works"""
        patient = Patient.objects.first()
        url = reverse('patients:patient_update', args=[patient.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/patient_form.html')
        
        # Test POST request
        post_data = {
            'name': 'Updated Patient Name',
            'birthday': patient.birthday.strftime('%Y-%m-%d'),
            'status': Patient.Status.INPATIENT,
            'tags': [self.tag.id],
        }
        
        response = self.client.post(url, post_data)
        
        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)
        
        # Refresh from database
        patient.refresh_from_db()
        
        # Check that the patient was updated
        self.assertEqual(patient.name, 'Updated Patient Name')
        self.assertEqual(patient.status, Patient.Status.INPATIENT)
    
    def test_patient_delete_view(self):
        """Test that the patient delete view works"""
        patient = Patient.objects.first()
        url = reverse('patients:patient_delete', args=[patient.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/patient_confirm_delete.html')
        
        # Test POST request
        patient_count = Patient.objects.count()
        response = self.client.post(url)
        
        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)
        
        # Check that the patient was deleted
        self.assertEqual(Patient.objects.count(), patient_count - 1)
        with self.assertRaises(Patient.DoesNotExist):
            Patient.objects.get(pk=patient.pk)
    
    def test_hospital_record_create_view(self):
        """Test that the hospital record create view works"""
        patient = Patient.objects.first()
        url = reverse('patients:hospital_record_create', args=[patient.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/hospital_record_form.html')
        
        # Test POST request
        record_count = PatientHospitalRecord.objects.filter(patient=patient).count()
        post_data = {
            'hospital': self.hospital.id,
            'record_number': 'NEW-REC',
            'first_admission_date': '2023-01-15',
        }
        
        response = self.client.post(url, post_data)
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Check that a new record was created
        self.assertEqual(
            PatientHospitalRecord.objects.filter(patient=patient).count(), 
            record_count + 1
        )
        
        # Check that the new record has the correct data
        new_record = PatientHospitalRecord.objects.filter(patient=patient).latest('created_at')
        self.assertEqual(new_record.record_number, 'NEW-REC')
        self.assertEqual(new_record.hospital, self.hospital)

class TagViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test tags
        for i in range(3):
            AllowedTag.objects.create(
                name=f'Tag {i}',
                slug=f'tag-{i}'
            )
    
    def setUp(self):
        # Log in for each test
        self.client.login(username='testuser', password='testpass123')
    
    def test_tag_list_view(self):
        """Test that the tag list view displays all tags"""
        url = reverse('patients:tag_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/tag_list.html')
        self.assertEqual(len(response.context['tags']), 3)
    
    def test_tag_create_view(self):
        """Test that the tag create view works"""
        url = reverse('patients:tag_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/tag_form.html')
        
        # Test POST request
        tag_count = AllowedTag.objects.count()
        post_data = {
            'name': 'New Tag',
            'slug': 'new-tag',
        }
        
        response = self.client.post(url, post_data)
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Check that a new tag was created
        self.assertEqual(AllowedTag.objects.count(), tag_count + 1)
        
        # Check that the new tag has the correct data
        new_tag = AllowedTag.objects.get(slug='new-tag')
        self.assertEqual(new_tag.name, 'New Tag')
    
    def test_tag_update_view(self):
        """Test that the tag update view works"""
        tag = AllowedTag.objects.first()
        url = reverse('patients:tag_update', args=[tag.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/tag_form.html')
        
        # Test POST request
        post_data = {
            'name': 'Updated Tag Name',
            'slug': tag.slug,
        }
        
        response = self.client.post(url, post_data)
        
        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)
        
        # Refresh from database
        tag.refresh_from_db()
        
        # Check that the tag was updated
        self.assertEqual(tag.name, 'Updated Tag Name')
    
    def test_tag_delete_view(self):
        """Test that the tag delete view works"""
        tag = AllowedTag.objects.first()
        url = reverse('patients:tag_delete', args=[tag.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'patients/tag_confirm_delete.html')
        
        # Test POST request
        tag_count = AllowedTag.objects.count()
        response = self.client.post(url)
        
        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)
        
        # Check that the tag was deleted
        self.assertEqual(AllowedTag.objects.count(), tag_count - 1)
        with self.assertRaises(AllowedTag.DoesNotExist):
            AllowedTag.objects.get(pk=tag.pk)
````

### Step 4: Create Documentation

1. Create a documentation file:

````markdown path=apps/patients/docs/README.md mode=EDIT
# Patients App Documentation

## Overview
The Patients app manages patient information, hospital records, and patient tags. It provides a comprehensive system for tracking patients across multiple hospitals.

## Models

### Patient
The `Patient` model stores basic patient information and current status.

**Fields:**
- `id` (UUID): Primary key
- `name` (CharField): Patient's full name
- `birthday` (DateField): Patient's date of birth
- `healthcard_number` (CharField, optional): Health card identification
- `id_number` (CharField, optional): Government ID number
- `fiscal_number` (CharField, optional): Tax/fiscal identification
- `phone` (CharField, optional): Contact phone number
- `address` (TextField, optional): Street address
- `city` (CharField, optional): City
- `state` (CharField, optional): State/province
- `zip_code` (CharField, optional): Postal/ZIP code
- `status` (IntegerField, choices): Current patient status (outpatient, inpatient, emergency, discharged, transferred)
- `current_hospital` (ForeignKey to Hospital, optional): Current hospital
- `ward` (ForeignKey to Ward, optional): Current ward
- `bed` (CharField, optional): Current bed identifier
- `last_admission_date` (DateField, optional): Date of last hospital admission
- `last_discharge_date` (DateField, optional): Date of last hospital discharge
- `tags` (ManyToManyField to AllowedTag): Tags associated with the patient
- `notes` (TextField, optional): Additional notes
- `created_at` (DateTimeField): Creation timestamp
- `updated_at` (DateTimeField): Last update timestamp
- `created_by` (ForeignKey to User): User who created the record
- `updated_by` (ForeignKey to User): User who last updated the record

### PatientHospitalRecord
The `PatientHospitalRecord` model tracks a patient's relationship with a specific hospital.

**Fields:**
- `id` (UUID): Primary key
- `patient` (ForeignKey to Patient): Associated patient
- `hospital` (ForeignKey to Hospital): Associated hospital
- `record_number` (CharField): Hospital's internal record number
- `first_admission_date` (DateField, optional): Date of first admission to this hospital
- `last_admission_date` (DateField, optional): Date of most recent admission
- `last_discharge_date` (DateField, optional): Date of most recent discharge
- `notes` (TextField, optional): Additional notes
- `created_at` (DateTimeField): Creation timestamp
- `updated_at` (DateTimeField): Last update timestamp
- `created_by` (ForeignKey to User): User who created the record
- `updated_by` (ForeignKey to User): User who last updated the record

### AllowedTag
The `AllowedTag` model defines tags that can be applied to patients.

**Fields:**
- `id` (AutoField): Primary key
- `name` (CharField): Tag name
- `slug` (SlugField): URL-friendly version of name
- `created_at` (DateTimeField): Creation timestamp
- `updated_at` (DateTimeField): Last update timestamp

## Views

### Patient Views
- `PatientListView`: Displays all patients with search and filtering
- `PatientDetailView`: Shows detailed information about a patient
- `PatientCreateView`: Form for creating a new patient
- `PatientUpdateView`: Form for updating an existing patient
- `PatientDeleteView`: Confirmation for deleting a patient

### Hospital Record Views
- `PatientHospitalRecordCreateView`: Form for adding a hospital record to a patient
- `PatientHospitalRecordUpdateView`: Form for updating a hospital record
- `PatientHospitalRecordDeleteView`: Confirmation for deleting a hospital record

### Tag Views
- `AllowedTagListView`: Displays all available tags
- `AllowedTagCreateView`: Form for creating a new tag
- `AllowedTagUpdateView`: Form for updating an existing tag
- `AllowedTagDeleteView`: Confirmation for deleting a tag

## Forms
- `PatientForm`: Form for creating/updating patients
- `PatientHospitalRecordForm`: Form for creating/updating hospital records
- `AllowedTagForm`: Form for creating/updating tags

## URLs
All URLs are prefixed with `patients/` and include:
- `''`: Patient list
- `create/`: Create new patient
- `<uuid:pk>/`: Patient detail
- `<uuid:pk>/update/`: Update patient
- `<uuid:pk>/delete/`: Delete patient
- `<uuid:patient_pk>/records/create/`: Create hospital record
- `records/<uuid:pk>/update/`: Update hospital record
- `records/<uuid:pk>/delete/`: Delete hospital record
- `tags/`: Tag list
- `tags/create/`: Create tag
- `tags/<int:pk>/update/`: Update tag
- `tags/<int:pk>/delete/`: Delete tag

## Templates
- `patient_base.html`: Base template for patients app
- `patient_list.html`: List of patients
- `patient_detail.html`: Patient details
- `patient_form.html`: Form for creating/updating patients
- `patient_confirm_delete.html`: Confirmation for deleting patients
- `hospital_record_form.html`: Form for creating/updating hospital records
- `hospital_record_confirm_delete.html`: Confirmation for deleting hospital records
- `tag_list.html`: List of tags
- `tag_form.html`: Form for creating/updating tags
- `tag_confirm_delete.html`: Confirmation for deleting tags

## Usage Examples

### Creating a Patient
```python
from apps.patients.models import Patient
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username='admin')

patient = Patient.objects.create(
    name='John Doe',
    birthday='1980-01-01',
    status=Patient.Status.OUTPATIENT,
    created_by=user,
    updated_by=user
)
```

### Adding a Hospital Record
```python
from apps.patients.models import Patient, PatientHospitalRecord
from apps.hospitals.models import Hospital

patient = Patient.objects.get(name='John Doe')
hospital = Hospital.objects.get(name='General Hospital')
user = patient.created_by

record = PatientHospitalRecord.objects.create(
    patient=patient,
    hospital=hospital,
    record_number='GH12345',
    created_by=user,
    updated_by=user
)
```

### Searching for Patients
```python
# Search by name
patients = Patient.objects.filter(name__icontains='doe')

# Filter by status
inpatients = Patient.objects.filter(status=Patient.Status.INPATIENT)

# Filter by hospital
hospital = Hospital.objects.get(name='General Hospital')
hospital_patients = Patient.objects.filter(current_hospital=hospital)

# Filter by tag
from apps.patients.models import AllowedTag
tag = AllowedTag.objects.get(name='Priority')
priority_patients = Patient.objects.filter(tags=tag)
```
````

## Vertical Slice 6: Integration and Final Testing

### Step 1: Integrate with Main Navigation

1. Update the main navigation template to include patients app links:

````html path=templates/includes/sidebar.html mode=EDIT
<!-- Patients Section -->
<li class="nav-item">
  <a class="nav-link collapsed" href="#" data-bs-toggle="collapse" data-bs-target="#collapsePatients" aria-expanded="false" aria-controls="collapsePatients">
    <i class="bi bi-people-fill"></i>
    <span>Patients</span>
  </a>
  <div id="collapsePatients" class="collapse" aria-labelledby="headingPatients" data-bs-parent="#accordionSidebar">
    <div class="bg-white py-2 collapse-inner rounded">
      <h6 class="collapse-header">Patient Management:</h6>
      <a class="collapse-item" href="{% url 'patients:patient_list' %}">
        <i class="bi bi-list-ul me-2"></i> All Patients
      </a>
      <a class="collapse-item" href="{% url 'patients:patient_create' %}">
        <i class="bi bi-person-plus me-2"></i> Add Patient
      </a>
      <a class="collapse-item" href="{% url 'patients:tag_list' %}">
        <i class="bi bi-tags me-2"></i> Manage Tags
      </a>
    </div>
  </div>
</li>
````

### Step 2: Create Dashboard Widgets

1. Create a dashboard widget for recent patients:

````html path=templates/patients/widgets/recent_patients.html mode=EDIT
{% load humanize %}

<div class="card shadow mb-4">
  <div class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
    <h6 class="m-0 font-weight-bold text-primary">Recent Patients</h6>
    <a href="{% url 'patients:patient_list' %}" class="btn btn-sm btn-primary">
      <i class="bi bi-list"></i> View All
    </a>
  </div>
  <div class="card-body">
    {% if recent_patients %}
      <div class="table-responsive">
        <table class="table table-hover table-sm mb-0">
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Added</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {% for patient in recent_patients %}
              <tr>
                <td>
                  <a href="{% url 'patients:patient_detail' patient.pk %}">
                    {{ patient.name }}
                  </a>
                </td>
                <td>
                  <span class="badge bg-{{ patient.get_status_color }}">
                    {{ patient.get_status_display }}
                  </span>
                </td>
                <td>{{ patient.created_at|naturaltime }}</td>
                <td class="text-end">
                  <a href="{% url 'patients:patient_detail' patient.pk %}" class="btn btn-sm btn-outline-primary">
                    <i class="bi bi-eye"></i>
                  </a>
                </td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    {% else %}
      <div class="text-center py-4">
        <i class="bi bi-people text-muted" style="font-size: 2rem;"></i>
        <p class="text-muted mt-2">No patients added yet</p>
        <a href="{% url 'patients:patient_create' %}" class="btn btn-sm btn-primary">
          <i class="bi bi-person-plus"></i> Add Patient
        </a>
      </div>
    {% endif %}
  </div>
</div>
````

1. Create a dashboard widget for patient statistics:

````html path=templates/patients/widgets/patient_stats.html mode=EDIT
<div class="row">
  <!-- Total Patients Card -->
  <div class="col-xl-3 col-md-6 mb-4">
    <div class="card border-left-primary shadow h-100 py-2">
      <div class="card-body">
        <div class="row no-gutters align-items-center">
          <div class="col mr-2">
            <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">
              Total Patients
            </div>
            <div class="h5 mb-0 font-weight-bold text-gray-800">{{ total_patients }}</div>
          </div>
          <div class="col-auto">
            <i class="bi bi-people-fill fa-2x text-gray-300"></i>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Inpatients Card -->
  <div class="col-xl-3 col-md-6 mb-4">
    <div class="card border-left-success shadow h-100 py-2">
      <div class="card-body">
        <div class="row no-gutters align-items-center">
          <div class="col mr-2">
            <div class="text-xs font-weight-bold text-success text-uppercase mb-1">
              Current Inpatients
            </div>
            <div class="h5 mb-0 font-weight-bold text-gray-800">{{ inpatient_count }}</div>
          </div>
          <div class="col-auto">
            <i class="bi bi-hospital fa-2x text-gray-300"></i>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Emergency Patients Card -->
  <div class="col-xl-3 col-md-6 mb-4">
    <div class="card border-left-warning shadow h-100 py-2">
      <div class="card-body">
        <div class="row no-gutters align-items-center">
          <div class="col mr-2">
            <div class="text-xs font-weight-bold text-warning text-uppercase mb-1">
              Emergency Patients
            </div>
            <div class="h5 mb-0 font-weight-bold text-gray-800">{{ emergency_count }}</div>
          </div>
          <div class="col-auto">
            <i class="bi bi-exclamation-triangle fa-2x text-gray-300"></i>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Outpatients Card -->
  <div class="col-xl-3 col-md-6 mb-4">
    <div class="card border-left-info shadow h-100 py-2">
      <div class="card-body">
        <div class="row no-gutters align-items-center">
          <div class="col mr-2">
            <div class="text-xs font-weight-bold text-info text-uppercase mb-1">
              Outpatients
            </div>
            <div class="h5 mb-0 font-weight-bold text-gray-800">{{ outpatient_count }}</div>
          </div>
          <div class="col-auto">
            <i class="bi bi-calendar-check fa-2x text-gray-300"></i>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
````

### Step 3: Update Dashboard View

1. Update the dashboard view to include patient data:

````python path=apps/core/views.py mode=EDIT
from apps.patients.models import Patient

def dashboard(request):
    """Dashboard view showing system overview."""
    context = {
        'page_title': 'Dashboard',
    }
    
    # Add patient statistics if the app is installed
    if 'apps.patients' in settings.INSTALLED_APPS:
        context.update({
            'total_patients': Patient.objects.count(),
            'inpatient_count': Patient.objects.filter(status=Patient.Status.INPATIENT).count(),
            'emergency_count': Patient.objects.filter(status=Patient.Status.EMERGENCY).count(),
            'outpatient_count': Patient.objects.filter(status=Patient.Status.OUTPATIENT).count(),
            'recent_patients': Patient.objects.order_by('-created_at')[:5],
        })
    
    return render(request, 'core/dashboard.html', context)
````

1. Update the dashboard template to include patient widgets:

````html path=templates/core/dashboard.html mode=EDIT
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
````

### Step 4: Add Template Tags for Patient Data

1. Create template tags file:

````python path=apps/patients/templatetags/patient_tags.py mode=EDIT
from django import template
from django.utils.safestring import mark_safe
from apps.patients.models import Patient

register = template.Library()

@register.filter
def status_badge(patient):
    """Return a Bootstrap badge for patient status."""
    status_colors = {
        Patient.Status.OUTPATIENT: 'info',
        Patient.Status.INPATIENT: 'success',
        Patient.Status.EMERGENCY: 'danger',
        Patient.Status.DISCHARGED: 'secondary',
        Patient.Status.TRANSFERRED: 'warning',
    }
    
    color = status_colors.get(patient.status, 'secondary')
    status_text = patient.get_status_display()
    
    return mark_safe(f'<span class="badge bg-{color}">{status_text}</span>')

@register.simple_tag
def patient_count_by_status(status):
    """Return count of patients with given status."""
    return Patient.objects.filter(status=status).count()

@register.inclusion_tag('patients/tags/patient_tag_list.html')
def render_patient_tags(patient):
    """Render the tags for a patient."""
    return {'tags': patient.tags.all()}
````

1. Create template for rendering patient tags:

````html path=templates/patients/tags/patient_tag_list.html mode=EDIT
{% if tags %}
  <div class="patient-tags">
    {% for tag in tags %}
      <span class="badge bg-secondary me-1">
        <i class="bi bi-tag-fill me-1"></i>{{ tag.name }}
      </span>
    {% endfor %}
  </div>
{% endif %}
````

### Step 5: Final Integration Testing

1. Create an integration test file:

````python path=apps/patients/tests/test_integration.py mode=EDIT
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.patients.models import Patient, PatientHospitalRecord, AllowedTag
from apps.hospitals.models import Hospital, Ward

User = get_user_model()

class PatientIntegrationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a test hospital
        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            code='TEST01',
            created_by=cls.user,
            updated_by=cls.user
        )
        
        # Create a test ward
        cls.ward = Ward.objects.create(
            name='Test Ward',
            code='TW01',
            hospital=cls.hospital,
            created_by=cls.user,
            updated_by=cls.user
        )
        
        # Create a test tag
        cls.tag = AllowedTag.objects.create(
            name='Test Tag',
            slug='test-tag'
        )
        
        # Create a test patient
        cls.patient = Patient.objects.create(
            name='John Doe',
            birthday='1980-01-01',
            status=Patient.Status.INPATIENT,
            current_hospital=cls.hospital,
            ward=cls.ward,
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.patient.tags.add(cls.tag)
        
        # Create a test hospital record
        cls.hospital_record = PatientHospitalRecord.objects.create(
            patient=cls.patient,
            hospital=cls.hospital,
            record_number='REC123',
            created_by=cls.user,
            updated_by=cls.user
        )
    
    def setUp(self):
        # Log in for each test
        self.client.login(username='testuser', password='testpass123')
    
    def test_dashboard_includes_patient_data(self):
        """Test that the dashboard includes patient statistics"""
        url = reverse('core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that patient data is in the context
        self.assertIn('total_patients', response.context)
        self.assertEqual(response.context['total_patients'], 1)
        self.assertIn('inpatient_count', response.context)
        self.assertEqual(response.context['inpatient_count'], 1)
    
    def test_patient_hospital_integration(self):
        """Test that patient and hospital data are properly integrated"""
        url = reverse('patients:patient_detail', args=[self.patient.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that hospital information is displayed
        self.assertContains(response, self.hospital.name)
        self.assertContains(response, self.ward.name)
        
        # Check that hospital record is displayed
        self.assertContains(response, self.hospital_record.record_number)
    
    def test_patient_tag_integration(self):
        """Test that patient tags are properly displayed"""
        url = reverse('patients:patient_detail', args=[self.patient.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that tag is displayed
        self.assertContains(response, self.tag.name)
    
    def test_patient_workflow(self):
        """Test a complete patient workflow"""
        # 1. Create a new patient
        create_url = reverse('patients:patient_create')
        patient_data = {
            'name': 'Jane Smith',
            'birthday': '1985-05-15',
            'status': Patient.Status.EMERGENCY,
            'tags': [self.tag.id],
        }
        
        response = self.client.post(create_url, patient_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Get the new patient
        new_patient = Patient.objects.get(name='Jane Smith')
        
        # 2. Add a hospital record
        record_url = reverse('patients:hospital_record_create', args=[new_patient.pk])
        record_data = {
            'hospital': self.hospital.id,
            'record_number': 'EMERG123',
            'first_admission_date': '2023-05-15',
        }
        
        response = self.client.post(record_url, record_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # 3. Update patient status to inpatient
        update_url = reverse('patients:patient_update', args=[new_patient.pk])
        update_data = {
            'name': 'Jane Smith',
            'birthday': '1985-05-15',
            'status': Patient.Status.INPATIENT,
            'current_hospital': self.hospital.id,
            'ward': self.ward.id,
            'tags': [self.tag.id],
        }
        
        response = self.client.post(update_url, update_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Refresh from database
        new_patient.refresh_from_db()
        
        # Check that status was updated
        self.assertEqual(new_patient.status, Patient.Status.INPATIENT)
        self.assertEqual(new_patient.current_hospital, self.hospital)
        self.assertEqual(new_patient.ward, self.ward)
````

### Step 6: Add Permissions and Groups

1. Create a migration to add patient-specific permissions and groups:

````python path=apps/patients/migrations/0002_add_patient_permissions.py mode=EDIT
from django.db import migrations
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

def create_patient_permissions(apps, schema_editor):
    """Create patient-specific permissions and groups."""
    # Get content types
    Patient = apps.get_model('patients', 'Patient')
    PatientHospitalRecord = apps.get_model('patients', 'PatientHospitalRecord')
    AllowedTag = apps.get_model('patients', 'AllowedTag')
    
    patient_ct = ContentType.objects.get_for_model(Patient)
    record_ct = ContentType.objects.get_for_model(PatientHospitalRecord)
    tag_ct = ContentType.objects.get_for_model(AllowedTag)
    
    # Create patient manager group
    patient_managers, _ = Group.objects.get_or_create(name='Patient Managers')
    
    # Add all patient-related permissions to the group
    for ct in [patient_ct, record_ct, tag_ct]:
        permissions = Permission.objects.filter(content_type=ct)
        for perm in permissions:
            patient_managers.permissions.add(perm)
    
    # Create patient viewer group (read-only)
    patient_viewers, _ = Group.objects.get_or_create(name='Patient Viewers')
    
    # Add view permissions to the viewer group
    for ct in [patient_ct, record_ct, tag_ct]:
        view_perm = Permission.objects.get(content_type=ct, codename__startswith='view_')
        patient_viewers.permissions.add(view_perm)

def remove_patient_permissions(apps, schema_editor):
    """Remove patient-specific groups."""
    Group.objects.filter(name__in=['Patient Managers', 'Patient Viewers']).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_patient_permissions, remove_patient_permissions),
    ]
````

## Vertical Slice 7: Final Documentation and Deployment

### Step 1: Update Project README

1. Add patients app information to the main project README:

````markdown path=README.md mode=EDIT
## Patients App

The Patients app provides functionality for managing patient information, hospital records, and patient tags.

### Features
- Patient management with detailed profiles
- Hospital record tracking
- Tag-based categorization
- Status tracking (outpatient, inpatient, emergency, etc.)
- Ward and bed assignment
- Integration with Hospitals app

### Setup
```bash
# Run migrations
python manage.py migrate patients

# Load initial data (if available)
python manage.py loaddata initial_patient_data
```

### Usage
Access the patients module through the sidebar navigation or directly at `/patients/`.
````

### Step 2: Create User Guide

1. Create a user guide for the patients app:

````markdown path=docs/user_guides/patients_app.md mode=EDIT
# Patients App User Guide

## Overview
The Patients app allows you to manage patient information, track hospital records, and categorize patients with tags.

## Patient Management

### Viewing Patients
1. Navigate to **Patients > All Patients** in the sidebar
2. Use the search box to find specific patients
3. Click on a patient's name to view their details

### Adding a New Patient
1. Navigate to **Patients > Add Patient** in the sidebar
2. Fill in the required fields (name, birthday, status)
3. Add optional information as needed
4. Click **Save** to create the patient

### Editing a Patient
1. Navigate to the patient's detail page
2. Click the **Edit** button
3. Update the patient information
4. Click **Save** to update the patient

### Deleting a Patient
1. Navigate to the patient's detail page
2. Click the **Delete** button
3. Confirm the deletion

## Hospital Records

### Adding a Hospital Record
1. Navigate to the patient's detail page
2. Click the **Add Hospital Record** button
3. Select the hospital and enter the record number
4. Add admission and discharge dates if available
5. Click **Save** to create the record

### Editing a Hospital Record
1. Navigate to the patient's detail page
2. Find the hospital record in the list
3. Click the **Edit** button next to the record
4. Update the record information
5. Click **Save** to update the record

### Deleting a Hospital Record
1. Navigate to the patient's detail page
2. Find the hospital record in the list
3. Click the **Delete** button next to the record
4. Confirm the deletion

## Patient Tags

### Viewing Tags
1. Navigate to **Patients > Manage Tags** in the sidebar
2. View the list of available tags

### Adding a New Tag
1. Navigate to **Patients > Manage Tags** in the sidebar
2. Click the **Add Tag** button
3. Enter the tag name and optional slug
4. Click **Save** to create the tag

### Editing a Tag
1. Navigate to **Patients > Manage Tags** in the sidebar
2. Find the tag in the list
3. Click the **Edit** button next to the tag
4. Update the tag information
5. Click **Save** to update the tag

### Deleting a Tag
1. Navigate to **Patients > Manage Tags** in the sidebar
2. Find the tag in the list
3. Click the **Delete** button next to the tag
4. Confirm the deletion

## Patient Status

Patients can have one of the following statuses:

- **Outpatient**: Patient receiving care without being admitted
- **Inpatient**: Patient currently admitted to a hospital
- **Emergency**: Patient in emergency care
- **Discharged**: Patient recently discharged from a hospital
- **Transferred**: Patient transferred to another facility

The status is indicated by a colored badge on the patient list and detail pages.
````

### Step 3: Final Deployment Checklist

1. Create a deployment checklist:

````markdown path=docs/deployment/patients_app_checklist.md mode=EDIT
# Patients App Deployment Checklist

## Pre-Deployment

- [ ] Run all tests: `python manage.py test apps.patients`
- [ ] Check for missing migrations: `python manage.py makemigrations --check`
- [ ] Verify permissions are correctly set up
- [ ] Ensure all templates render correctly
- [ ] Check for any hardcoded URLs or paths
- [ ] Verify integration with Hospitals app

## Deployment Steps

1. **Update Code**
   - [ ] Pull latest code from repository
   - [ ] Install any new dependencies: `uv sync`

2. **Database Updates**
   - [ ] Run migrations: `python manage.py migrate patients`
   - [ ] Load initial data if needed: `python manage.py loaddata initial_patient_data`

3. **Static Files**
   - [ ] Collect static files: `python manage.py collectstatic --noinput`

4. **Permissions**
   - [ ] Verify groups are created: `python manage.py shell -c "from django.contrib.auth.models import Group; print(Group.objects.filter(name__in=['Patient Managers', 'Patient Viewers']).exists())"`

5. **Cache**
   - [ ] Clear cache if using: `python manage.py clear_cache`

## Post-Deployment

- [ ] Verify patients list page loads correctly
- [ ] Test creating a new patient
- [ ] Test adding a hospital record
- [ ] Test patient search functionality
- [ ] Verify dashboard widgets display correctly
- [ ] Check mobile responsiveness
- [ ] Verify permissions work as expected
````

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
