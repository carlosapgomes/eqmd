## Vertical Slice 3: Patient Forms and Basic Views

### Step 1: Create Patient Forms

1. Create forms.py:

   ```python
   from django import forms
   from crispy_forms.helper import FormHelper
   from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML
   from .models import Patient, PatientHospitalRecord, AllowedTag
   ```

2. Implement PatientForm:

   ```python
   class PatientForm(forms.ModelForm):
       class Meta:
           model = Patient
           fields = ['name', 'birthday', 'gender', 'id_number', 'fiscal_number',
                     'healthcard_number', 'status', 'current_hospital', 'bed', 'tags']
           widgets = {
               'birthday': forms.DateInput(attrs={'type': 'date'}),
           }

       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.helper = FormHelper()
           self.helper.form_method = 'post'
           self.helper.layout = Layout(
               Fieldset(
                   'Patient Information',
                   Row(
                       Column('name', css_class='col-md-6'),
                       Column('birthday', css_class='col-md-3'),
                       Column('gender', css_class='col-md-3'),
                   ),
                   Row(
                       Column('id_number', css_class='col-md-4'),
                       Column('fiscal_number', css_class='col-md-4'),
                       Column('healthcard_number', css_class='col-md-4'),
                   ),
               ),
               Fieldset(
                   'Hospital Information',
                   Row(
                       Column('status', css_class='col-md-4'),
                       Column('current_hospital', css_class='col-md-4'),
                       Column('bed', css_class='col-md-4'),
                   ),
                   'tags',
               ),
               Submit('submit', 'Save', css_class='btn btn-primary mt-3')
           )
   ```

3. Implement PatientHospitalRecordForm:

   ```python
   class PatientHospitalRecordForm(forms.ModelForm):
       class Meta:
           model = PatientHospitalRecord
           fields = ['patient', 'hospital', 'record_number', 'admission_date', 'discharge_date']
           widgets = {
               'admission_date': forms.DateInput(attrs={'type': 'date'}),
               'discharge_date': forms.DateInput(attrs={'type': 'date'}),
           }

       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.helper = FormHelper()
           self.helper.form_method = 'post'
           self.helper.layout = Layout(
               Fieldset(
                   'Hospital Record',
                   Row(
                       Column('patient', css_class='col-md-6'),
                       Column('hospital', css_class='col-md-6'),
                   ),
                   Row(
                       Column('record_number', css_class='col-md-4'),
                       Column('admission_date', css_class='col-md-4'),
                       Column('discharge_date', css_class='col-md-4'),
                   ),
               ),
               Submit('submit', 'Save', css_class='btn btn-primary mt-3')
           )
   ```

4. Implement AllowedTagForm:

   ```python
   class AllowedTagForm(forms.ModelForm):
       class Meta:
           model = AllowedTag
           fields = ['name', 'slug']

       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.helper = FormHelper()
           self.helper.form_method = 'post'
           self.helper.layout = Layout(
               Fieldset(
                   'Tag Information',
                   Row(
                       Column('name', css_class='col-md-6'),
                       Column('slug', css_class='col-md-6'),
                   ),
               ),
               Submit('submit', 'Save', css_class='btn btn-primary mt-3')
           )

           # Auto-populate slug from name if creating a new tag
           if not kwargs.get('instance'):
               self.fields['slug'].required = False
   ```

5. Verify form functionality in Django shell:

   ```bash
   python manage.py shell -c "from apps.patients.forms import PatientForm; form = PatientForm(); print(form.fields)"
   ```

### Step 2: Create Base Templates

1. Create patient_base.html template:

   ```html
   {% extends "base.html" %} {% block content %}
   <div class="container-fluid">
     <div class="row">
       <!-- Sidebar -->
       <div class="col-md-3 col-lg-2 d-md-block bg-light sidebar">
         <div class="position-sticky pt-3">
           <ul class="nav flex-column">
             <li class="nav-item">
               <a
                 class="nav-link {% if request.resolver_match.url_name == 'patient_list' %}active{% endif %}"
                 href="{% url 'patients:patient_list' %}"
               >
                 <i class="bi bi-people"></i> All Patients
               </a>
             </li>
             <li class="nav-item">
               <a
                 class="nav-link {% if request.resolver_match.url_name == 'patient_create' %}active{% endif %}"
                 href="{% url 'patients:patient_create' %}"
               >
                 <i class="bi bi-person-plus"></i> Add Patient
               </a>
             </li>
             <li class="nav-item">
               <a
                 class="nav-link {% if request.resolver_match.url_name == 'tag_list' %}active{% endif %}"
                 href="{% url 'patients:tag_list' %}"
               >
                 <i class="bi bi-tags"></i> Manage Tags
               </a>
             </li>
           </ul>
         </div>
       </div>

       <!-- Main content -->
       <div class="col-md-9 ms-sm-auto col-lg-10 px-md-4">
         {% if messages %}
         <div class="messages mt-3">
           {% for message in messages %}
           <div
             class="alert alert-{{ message.tags }} alert-dismissible fade show"
             role="alert"
           >
             {{ message }}
             <button
               type="button"
               class="btn-close"
               data-bs-dismiss="alert"
               aria-label="Close"
             ></button>
           </div>
           {% endfor %}
         </div>
         {% endif %} {% block patient_content %}{% endblock %}
       </div>
     </div>
   </div>
   {% endblock %}
   ```

2. Verify template existence:

   ```bash
   ls -la apps/patients/templates/patients/patient_base.html
   ```

### Step 3: Create Patient List Template

1. Create patient_list.html:

   ```html
   {% extends "patients/patient_base.html" %} {% load static %} {% block title
   %}Patients{% endblock %} {% block patient_content %}
   <div
     class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom"
   >
     <h1 class="h2">Patients</h1>
     <div class="btn-toolbar mb-2 mb-md-0">
       <a
         href="{% url 'patients:patient_create' %}"
         class="btn btn-sm btn-outline-primary"
       >
         <i class="bi bi-person-plus"></i> Add Patient
       </a>
     </div>
   </div>

   <!-- Search form -->
   <form method="get" class="mb-4">
     <div class="input-group">
       <input
         type="text"
         name="q"
         class="form-control"
         placeholder="Search patients..."
         value="{{ request.GET.q|default:'' }}"
       />
       <button class="btn btn-outline-secondary" type="submit">
         <i class="bi bi-search"></i> Search
       </button>
     </div>
   </form>

   <!-- Patient list -->
   {% if patient_list %}
   <div class="table-responsive">
     <table class="table table-striped table-hover">
       <thead>
         <tr>
           <th>Name</th>
           <th>Birthday</th>
           <th>Status</th>
           <th>Hospital</th>
           <th>Actions</th>
         </tr>
       </thead>
       <tbody>
         {% for patient in patient_list %}
         <tr>
           <td>{{ patient.name }}</td>
           <td>{{ patient.birthday|date:"d/m/Y" }}</td>
           <td>
             {% if patient.status == 0 %}
             <span class="badge bg-primary">Inpatient</span>
             {% elif patient.status == 1 %}
             <span class="badge bg-success">Outpatient</span>
             {% elif patient.status == 2 %}
             <span class="badge bg-secondary">Deceased</span>
             {% endif %}
           </td>
           <td>{{ patient.current_hospital|default:"-" }}</td>
           <td>
             <a
               href="{% url 'patients:patient_detail' pk=patient.pk %}"
               class="btn btn-sm btn-outline-info"
             >
               <i class="bi bi-eye"></i>
             </a>
             <a
               href="{% url 'patients:patient_update' pk=patient.pk %}"
               class="btn btn-sm btn-outline-primary"
             >
               <i class="bi bi-pencil"></i>
             </a>
           </td>
         </tr>
         {% endfor %}
       </tbody>
     </table>
   </div>

   <!-- Pagination -->
   {% if is_paginated %}
   <nav aria-label="Page navigation">
     <ul class="pagination justify-content-center">
       {% if page_obj.has_previous %}
       <li class="page-item">
         <a
           class="page-link"
           href="?page=1{% if request.GET.q %}&q={{ request.GET.q }}{% endif %}"
           >First</a
         >
       </li>
       <li class="page-item">
         <a
           class="page-link"
           href="?page={{ page_obj.previous_page_number }}{% if request.GET.q %}&q={{ request.GET.q }}{% endif %}"
           >Previous</a
         >
       </li>
       {% endif %}

       <li class="page-item active">
         <span class="page-link"
           >Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages
           }}</span
         >
       </li>

       {% if page_obj.has_next %}
       <li class="page-item">
         <a
           class="page-link"
           href="?page={{ page_obj.next_page_number }}{% if request.GET.q %}&q={{ request.GET.q }}{% endif %}"
           >Next</a
         >
       </li>
       <li class="page-item">
         <a
           class="page-link"
           href="?page={{ page_obj.paginator.num_pages }}{% if request.GET.q %}&q={{ request.GET.q }}{% endif %}"
           >Last</a
         >
       </li>
       {% endif %}
     </ul>
   </nav>
   {% endif %} {% else %}
   <div class="alert alert-info">
     No patients found.
     <a href="{% url 'patients:patient_create' %}">Add a new patient</a>.
   </div>
   {% endif %} {% endblock %}
   ```

2. Verify template existence:

   ```bash
   ls -la apps/patients/templates/patients/patient_list.html
   ```

### Step 4: Create Patient Detail Template

1. Create patient_detail.html:

   ```html
   {% extends "patients/patient_base.html" %} {% load static %} {% block title
   %}{{ patient.name }}{% endblock %} {% block patient_content %}
   <div
     class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom"
   >
     <h1 class="h2">{{ patient.name }}</h1>
     <div class="btn-toolbar mb-2 mb-md-0">
       <a
         href="{% url 'patients:patient_update' pk=patient.pk %}"
         class="btn btn-sm btn-outline-primary me-2"
       >
         <i class="bi bi-pencil"></i> Edit
       </a>
       <a
         href="{% url 'patients:patient_delete' pk=patient.pk %}"
         class="btn btn-sm btn-outline-danger"
       >
         <i class="bi bi-trash"></i> Delete
       </a>
     </div>
   </div>

   <div class="row mb-4">
     <!-- Patient Information -->
     <div class="col-md-6">
       <div class="card">
         <div class="card-header">
           <h5 class="card-title mb-0">Patient Information</h5>
         </div>
         <div class="card-body">
           <dl class="row">
             <dt class="col-sm-4">Birthday:</dt>
             <dd class="col-sm-8">{{ patient.birthday|date:"d/m/Y" }}</dd>

             <dt class="col-sm-4">Gender:</dt>
             <dd class="col-sm-8">{{ patient.get_gender_display }}</dd>

             <dt class="col-sm-4">ID Number:</dt>
             <dd class="col-sm-8">{{ patient.id_number|default:"-" }}</dd>

             <dt class="col-sm-4">Fiscal Number:</dt>
             <dd class="col-sm-8">{{ patient.fiscal_number|default:"-" }}</dd>

             <dt class="col-sm-4">Health Card:</dt>
             <dd class="col-sm-8">
               {{ patient.healthcard_number|default:"-" }}
             </dd>

             <dt class="col-sm-4">Status:</dt>
             <dd class="col-sm-8">
               {% if patient.status == 0 %}
               <span class="badge bg-primary">Inpatient</span>
               {% elif patient.status == 1 %}
               <span class="badge bg-success">Outpatient</span>
               {% elif patient.status == 2 %}
               <span class="badge bg-secondary">Deceased</span>
               {% endif %}
             </dd>
           </dl>
         </div>
       </div>
     </div>

     <!-- Hospital Information -->
     <div class="col-md-6">
       <div class="card">
         <div class="card-header">
           <h5 class="card-title mb-0">Hospital Information</h5>
         </div>
         <div class="card-body">
           <dl class="row">
             <dt class="col-sm-4">Current Hospital:</dt>
             <dd class="col-sm-8">
               {{ patient.current_hospital|default:"-" }}
             </dd>

             <dt class="col-sm-4">Bed:</dt>
             <dd class="col-sm-8">{{ patient.bed|default:"-" }}</dd>

             <dt class="col-sm-4">Tags:</dt>
             <dd class="col-sm-8">
               {% for tag in patient.tags.all %}
               <span class="badge bg-secondary">{{ tag.name }}</span>
               {% empty %} - {% endfor %}
             </dd>
           </dl>
         </div>
       </div>
     </div>
   </div>

   <!-- Hospital Records -->
   <div class="card mb-4">
     <div class="card-header d-flex justify-content-between align-items-center">
       <h5 class="card-title mb-0">Hospital Records</h5>
       <a
         href="{% url 'patients:hospital_record_create' %}?patient={{ patient.pk }}"
         class="btn btn-sm btn-outline-primary"
       >
         <i class="bi bi-plus"></i> Add Record
       </a>
     </div>
     <div class="card-body">
       {% if patient.patienthospitalrecord_set.all %}
       <div class="table-responsive">
         <table class="table table-striped">
           <thead>
             <tr>
               <th>Hospital</th>
               <th>Record Number</th>
               <th>Admission Date</th>
               <th>Discharge Date</th>
               <th>Actions</th>
             </tr>
           </thead>
           <tbody>
             {% for record in patient.patienthospitalrecord_set.all %}
             <tr>
               <td>{{ record.hospital }}</td>
               <td>{{ record.record_number }}</td>
               <td>{{ record.admission_date|date:"d/m/Y" }}</td>
               <td>{{ record.discharge_date|date:"d/m/Y"|default:"-" }}</td>
               <td>
                 <a
                   href="{% url 'patients:hospital_record_update' pk=record.pk %}"
                   class="btn btn-sm btn-outline-primary"
                 >
                   <i class="bi bi-pencil"></i>
                 </a>
                 <a
                   href="{% url 'patients:hospital_record_delete' pk=record.pk %}"
                   class="btn btn-sm btn-outline-danger"
                 >
                   <i class="bi bi-trash"></i>
                 </a>
               </td>
             </tr>
             {% endfor %}
           </tbody>
         </table>
       </div>
       {% else %}
       <p class="text-muted">No hospital records found.</p>
       {% endif %}
     </div>
   </div>

   <!-- Metadata -->
   <div class="card mb-4">
     <div class="card-header">
       <h5 class="card-title mb-0">Metadata</h5>
     </div>
     <div class="card-body">
       <dl class="row">
         <dt class="col-sm-3">Created:</dt>
         <dd class="col-sm-9">
           {{ patient.created_at|date:"d/m/Y H:i" }} by {{ patient.created_by }}
         </dd>

         <dt class="col-sm-3">Last Updated:</dt>
         <dd class="col-sm-9">
           {{ patient.updated_at|date:"d/m/Y H:i" }} by {{ patient.updated_by }}
         </dd>
       </dl>
     </div>
   </div>
   {% endblock %}
   ```

2. Verify template existence:

   ```bash
   ls -la apps/patients/templates/patients/patient_detail.html
   ```

### Step 5: Create Form Templates

1. Create patient_form.html:

   ```html
   {% extends "patients/patient_base.html" %} {% load crispy_forms_tags %} {%
   block title %}{% if form.instance.pk %}Edit{% else %}Add{% endif %} Patient{%
   endblock %} {% block patient_content %}
   <div
     class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom"
   >
     <h1 class="h2">
       {% if form.instance.pk %}Edit{% else %}Add{% endif %} Patient
     </h1>
   </div>

   <div class="card">
     <div class="card-body">{% crispy form %}</div>
   </div>

   <div class="mt-3">
     <a
       href="{% if form.instance.pk %}{% url 'patients:patient_detail' pk=form.instance.pk %}{% else %}{% url 'patients:patient_list' %}{% endif %}"
       class="btn btn-outline-secondary"
     >
       Cancel
     </a>
   </div>
   {% endblock %}
   ```

2. Create hospital_record_form.html:

   ```html
   {% extends "patients/patient_base.html" %} {% load crispy_forms_tags %} {%
   block title %}{% if form.instance.pk %}Edit{% else %}Add{% endif %} Hospital
   Record{% endblock %} {% block patient_content %}
   <div
     class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom"
   >
     <h1 class="h2">
       {% if form.instance.pk %}Edit{% else %}Add{% endif %} Hospital Record
     </h1>
   </div>

   <div class="card">
     <div class="card-body">{% crispy form %}</div>
   </div>

   <div class="mt-3">
     <a
       href="{% if form.instance.patient %}{% url 'patients:patient_detail' pk=form.instance.patient.pk %}{% else %}{% url 'patients:patient_list' %}{% endif %}"
       class="btn btn-outline-secondary"
     >
       Cancel
     </a>
   </div>
   {% endblock %}
   ```

3. Create tag_form.html:

   ```html
   {% extends "patients/patient_base.html" %} {% load crispy_forms_tags %} {%
   block title %}{% if form.instance.pk %}Edit{% else %}Add{% endif %} Tag{%
   endblock %} {% block patient_content %}
   <div
     class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom"
   >
     <h1 class="h2">
       {% if form.instance.pk %}Edit{% else %}Add{% endif %} Tag
     </h1>
   </div>

   <div class="card">
     <div class="card-body">{% crispy form %}</div>
   </div>

   <div class="mt-3">
     <a href="{% url 'patients:tag_list' %}" class="btn btn-outline-secondary">
       Cancel
     </a>
   </div>
   {% endblock %}
   ```

4. Create confirmation templates:

   a. Create patient_confirm_delete.html:

   ```html
   {% extends "patients/patient_base.html" %} {% block title %}Delete Patient{%
   endblock %} {% block patient_content %}
   <div
     class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom"
   >
     <h1 class="h2">Delete Patient</h1>
   </div>

   <div class="alert alert-danger">
     <p>Are you sure you want to delete the patient "{{ object.name }}"?</p>
     <p>This action cannot be undone.</p>
   </div>

   <form method="post">
     {% csrf_token %}
     <div class="d-flex">
       <a
         href="{% url 'patients:patient_detail' pk=object.pk %}"
         class="btn btn-outline-secondary me-2"
         >Cancel</a
       >
       <button type="submit" class="btn btn-danger">Confirm Delete</button>
     </div>
   </form>
   {% endblock %}
   ```

   b. Create hospital_record_confirm_delete.html:

   ```html
   {% extends "patients/patient_base.html" %} {% block title %}Delete Hospital
   Record{% endblock %} {% block patient_content %}
   <div
     class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom"
   >
     <h1 class="h2">Delete Hospital Record</h1>
   </div>

   <div class="alert alert-danger">
     <p>
       Are you sure you want to delete the hospital record for "{{
       object.patient.name }}" at "{{ object.hospital.name }}"?
     </p>
     <p>This action cannot be undone.</p>
   </div>

   <form method="post">
     {% csrf_token %}
     <div class="d-flex">
       <a
         href="{% url 'patients:patient_detail' pk=object.patient.pk %}"
         class="btn btn-outline-secondary me-2"
         >Cancel</a
       >
       <button type="submit" class="btn btn-danger">Confirm Delete</button>
     </div>
   </form>
   {% endblock %}
   ```

   c. Create tag_confirm_delete.html:

   ```html
   {% extends "patients/patient_base.html" %} {% block title %}Delete Tag{%
   endblock %} {% block patient_content %}
   <div
     class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom"
   >
     <h1 class="h2">Delete Tag</h1>
   </div>

   <div class="alert alert-danger">
     <p>Are you sure you want to delete the tag "{{ object.name }}"?</p>
     <p>This action cannot be undone.</p>
   </div>

   <form method="post">
     {% csrf_token %}
     <div class="d-flex">
       <a
         href="{% url 'patients:tag_list' %}"
         class="btn btn-outline-secondary me-2"
         >Cancel</a
       >
       <button type="submit" class="btn btn-danger">Confirm Delete</button>
     </div>
   </form>
   {% endblock %}
   ```

5. Create tag_list.html:

   ```html
   {% extends "patients/patient_base.html" %} {% block title %}Tags{% endblock
   %} {% block patient_content %}
   <div
     class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom"
   >
     <h1 class="h2">Tags</h1>
     <div class="btn-toolbar mb-2 mb-md-0">
       <a
         href="{% url 'patients:tag_create' %}"
         class="btn btn-sm btn-outline-primary"
       >
         <i class="bi bi-plus"></i> Add Tag
       </a>
     </div>
   </div>

   {% if tag_list %}
   <div class="table-responsive">
     <table class="table table-striped table-hover">
       <thead>
         <tr>
           <th>Name</th>
           <th>Slug</th>
           <th>Actions</th>
         </tr>
       </thead>
       <tbody>
         {% for tag in tag_list %}
         <tr>
           <td>{{ tag.name }}</td>
           <td>{{ tag.slug }}</td>
           <td>
             <a
               href="{% url 'patients:tag_update' pk=tag.pk %}"
               class="btn btn-sm btn-outline-primary"
             >
               <i class="bi bi-pencil"></i>
             </a>
             <a
               href="{% url 'patients:tag_delete' pk=tag.pk %}"
               class="btn btn-sm btn-outline-danger"
             >
               <i class="bi bi-trash"></i>
             </a>
           </td>
         </tr>
         {% endfor %}
       </tbody>
     </table>
   </div>
   {% else %}
   <div class="alert alert-info">
     No tags found. <a href="{% url 'patients:tag_create' %}">Add a new tag</a>.
   </div>
   {% endif %} {% endblock %}
   ```

6. Verify template existence:

   ```bash
   ls -la apps/patients/templates/patients/
   ```

### Step 6: Test Template Rendering

1. Create test_templates.py:

   ```python
   from django.test import TestCase
   from django.template.loader import render_to_string
   from django.urls import reverse
   from django.contrib.auth import get_user_model
   from .models import Patient, PatientHospitalRecord, AllowedTag

   User = get_user_model()

   class TemplateTests(TestCase):
       @classmethod
       def setUpTestData(cls):
           cls.user = User.objects.create_user(
               username='testuser',
               email='test@example.com',
               password='testpassword'
           )

           cls.tag = AllowedTag.objects.create(
               name='Test Tag',
               slug='test-tag'
           )

           cls.patient = Patient.objects.create(
               name='Test Patient',
               birthday='1980-01-01',
               status=Patient.OUTPATIENT,
               created_by=cls.user,
               updated_by=cls.user
           )
           cls.patient.tags.add(cls.tag)

       def test_template_existence(self):
           """Test that all required templates exist"""
           templates = [
               'patients/patient_base.html',
               'patients/patient_list.html',
               'patients/patient_detail.html',
               'patients/patient_form.html',
               'patients/hospital_record_form.html',
               'patients/patient_confirm_delete.html',
               'patients/hospital_record_confirm_delete.html',
               'patients/tag_form.html',
               'patients/tag_confirm_delete.html',
               'patients/tag_list.html',
           ]

           for template in templates:
               self.assertTrue(render_to_string(template, {'request': None}))

       def test_template_inheritance(self):
           """Test that templates properly extend base templates"""
           self.client.force_login(self.user)
           response = self.client.get(reverse('patients:patient_list'))
           self.assertTemplateUsed(response, 'patients/patient_base.html')
           self.assertTemplateUsed(response, 'patients/patient_list.html')

       def test_template_context_variables(self):
           """Test that templates receive expected context variables"""
           self.client.force_login(self.user)
           response = self.client.get(reverse('patients:patient_detail', kwargs={'pk': self.patient.pk}))
           self.assertEqual(response.context['patient'], self.patient)
   ```

2. Run template tests:

   ```bash
   python manage.py test apps.patients.tests.test_templates
   ```

3. Verify template rendering in browser:

   ```bash
   python manage.py runserver
   ```

   Then visit <http://localhost:8000/patients/> in your browser.

### Additional Recommendations

1. **For Forms**:

   - Test validation with both valid and invalid data
   - Verify error messages are displayed correctly
   - Test form submission with missing required fields

2. **For Templates**:

   - Verify responsive design on different screen sizes
   - Test accessibility features
   - Ensure consistent styling with the rest of the application

3. **For Integration**:

   - Verify form-template integration by testing the complete submission flow
   - Test form validation error display in templates
   - Ensure all required JavaScript and CSS assets are properly loaded

4. **For Performance**:

   - Consider using form prefill for related records
   - Implement client-side validation where appropriate
   - Use select_related/prefetch_related for form querysets

5. **For Accessibility**:
   - Add proper ARIA attributes to form elements
   - Ensure form error messages are accessible to screen readers
   - Test keyboard navigation through all form fields

### Step 7: Create Basic Views

1. Create views.py:

   ```python
   from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
   from django.urls import reverse_lazy
   from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
   from django.contrib import messages
   from django.shortcuts import get_object_or_404, redirect
   from django.db.models import Q

   from .models import Patient, PatientHospitalRecord, AllowedTag
   from .forms import PatientForm, PatientHospitalRecordForm, AllowedTagForm
   ```

2. Implement Patient views:

   ```python
   class PatientListView(LoginRequiredMixin, ListView):
       model = Patient
       paginate_by = 10

       def get_queryset(self):
           queryset = super().get_queryset()
           search_query = self.request.GET.get('q')

           if search_query:
               queryset = queryset.filter(
                   Q(name__icontains=search_query) |
                   Q(id_number__icontains=search_query) |
                   Q(fiscal_number__icontains=search_query) |
                   Q(healthcard_number__icontains=search_query)
               )

           return queryset


   class PatientDetailView(LoginRequiredMixin, DetailView):
       model = Patient


   class PatientCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
       model = Patient
       form_class = PatientForm
       permission_required = 'patients.add_patient'

       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.pk})

       def form_valid(self, form):
           form.instance.created_by = self.request.user
           form.instance.updated_by = self.request.user
           messages.success(self.request, f"Patient {form.instance.name} created successfully.")
           return super().form_valid(form)


   class PatientUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
       model = Patient
       form_class = PatientForm
       permission_required = 'patients.change_patient'

       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.pk})

       def form_valid(self, form):
           form.instance.updated_by = self.request.user
           messages.success(self.request, f"Patient {form.instance.name} updated successfully.")
           return super().form_valid(form)


   class PatientDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
       model = Patient
       success_url = reverse_lazy('patients:patient_list')
       permission_required = 'patients.delete_patient'

       def delete(self, request, *args, **kwargs):
           patient = self.get_object()
           messages.success(request, f"Patient {patient.name} deleted successfully.")
           return super().delete(request, *args, **kwargs)
   ```

3. Implement Hospital Record views:

   ```python
   class HospitalRecordCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
       model = PatientHospitalRecord
       form_class = PatientHospitalRecordForm
       permission_required = 'patients.add_patienthospitalrecord'

       def get_initial(self):
           initial = super().get_initial()
           patient_id = self.request.GET.get('patient')
           if patient_id:
               initial['patient'] = get_object_or_404(Patient, pk=patient_id)
           return initial

       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})

       def form_valid(self, form):
           form.instance.created_by = self.request.user
           form.instance.updated_by = self.request.user
           messages.success(self.request, "Hospital record created successfully.")
           return super().form_valid(form)


   class HospitalRecordUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
       model = PatientHospitalRecord
       form_class = PatientHospitalRecordForm
       permission_required = 'patients.change_patienthospitalrecord'

       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})

       def form_valid(self, form):
           form.instance.updated_by = self.request.user
           messages.success(self.request, "Hospital record updated successfully.")
           return super().form_valid(form)


   class HospitalRecordDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
       model = PatientHospitalRecord
       permission_required = 'patients.delete_patienthospitalrecord'

       def get_success_url(self):
           return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})

       def delete(self, request, *args, **kwargs):
           record = self.get_object()
           messages.success(request, f"Hospital record for {record.patient.name} deleted successfully.")
           return super().delete(request, *args, **kwargs)
   ```

4. Implement Tag views:

   ```python
   class TagListView(LoginRequiredMixin, ListView):
       model = AllowedTag
       context_object_name = 'tag_list'


   class TagCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
       model = AllowedTag
       form_class = AllowedTagForm
       permission_required = 'patients.add_allowedtag'
       success_url = reverse_lazy('patients:tag_list')

       def form_valid(self, form):
           messages.success(self.request, f"Tag {form.instance.name} created successfully.")
           return super().form_valid(form)


   class TagUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
       model = AllowedTag
       form_class = AllowedTagForm
       permission_required = 'patients.change_allowedtag'
       success_url = reverse_lazy('patients:tag_list')

       def form_valid(self, form):
           messages.success(self.request, f"Tag {form.instance.name} updated successfully.")
           return super().form_valid(form)


   class TagDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
       model = AllowedTag
       success_url = reverse_lazy('patients:tag_list')
       permission_required = 'patients.delete_allowedtag'

       def delete(self, request, *args, **kwargs):
           tag = self.get_object()
           messages.success(request, f"Tag {tag.name} deleted successfully.")
           return super().delete(request, *args, **kwargs)
   ```

5. Verify view functionality in Django shell:

   ```bash
   python manage.py shell -c "from apps.patients.views import PatientListView; print(PatientListView.as_view().__name__)"
   ```

### Step 8: Configure URLs

1. Create urls.py:

   ```python
   from django.urls import path
   from . import views

   app_name = 'patients'

   urlpatterns = [
       # Patient URLs
       path('', views.PatientListView.as_view(), name='patient_list'),
       path('<int:pk>/', views.PatientDetailView.as_view(), name='patient_detail'),
       path('create/', views.PatientCreateView.as_view(), name='patient_create'),
       path('<int:pk>/update/', views.PatientUpdateView.as_view(), name='patient_update'),
       path('<int:pk>/delete/', views.PatientDeleteView.as_view(), name='patient_delete'),

       # Hospital Record URLs
       path('records/create/', views.HospitalRecordCreateView.as_view(), name='hospital_record_create'),
       path('records/<int:pk>/update/', views.HospitalRecordUpdateView.as_view(), name='hospital_record_update'),
       path('records/<int:pk>/delete/', views.HospitalRecordDeleteView.as_view(), name='hospital_record_delete'),

       # Tag URLs
       path('tags/', views.TagListView.as_view(), name='tag_list'),
       path('tags/create/', views.TagCreateView.as_view(), name='tag_create'),
       path('tags/<int:pk>/update/', views.TagUpdateView.as_view(), name='tag_update'),
       path('tags/<int:pk>/delete/', views.TagDeleteView.as_view(), name='tag_delete'),
   ]
   ```

2. Add to project URLs in config/urls.py:

   ```python
   # Add to existing urlpatterns
   path('patients/', include('apps.patients.urls')),
   ```

3. Verify URL configuration:

   ```bash
   python manage.py shell -c "from django.urls import reverse; print(reverse('patients:patient_list'))"
   ```

### Step 9: Verify App Configuration and Basic Functionality

1. **Verify App Configuration**:

   ```bash
   python manage.py check patients
   ```

2. **Test URL Resolution**:

   ```bash
   python manage.py shell -c "from django.urls import reverse; print(reverse('patients:patient_list'), reverse('patients:patient_create'))"
   ```

3. **Verify Template Loading**:

   ```bash
   python manage.py shell -c "from django.template.loader import get_template; print(get_template('patients/patient_list.html'))"
   ```

4. **Test Basic Model Creation Through Shell**:

   ```bash
   python manage.py shell -c "from apps.patients.models import Patient; from django.contrib.auth import get_user_model; User = get_user_model(); user = User.objects.first(); Patient.objects.create(name='Test Patient', birthday='1990-01-01', status=0, created_by=user, updated_by=user); print('Patient created successfully')"
   ```

5. **Verify Admin Interface Access**:

   ```bash
   python manage.py shell -c "from django.contrib import admin; from apps.patients.models import Patient; print('Patient registered:', Patient in admin.site._registry)"
   ```

### Step 10: Test View Functionality

1. Create test_views.py:

   ```python
   from django.test import TestCase
   from django.urls import reverse
   from django.contrib.auth import get_user_model
   from django.contrib.auth.models import Permission
   from django.contrib.contenttypes.models import ContentType
   from .models import Patient, PatientHospitalRecord, AllowedTag

   User = get_user_model()

   class PatientViewTests(TestCase):
       @classmethod
       def setUpTestData(cls):
           # Create test user
           cls.user = User.objects.create_user(
               username='testuser',
               email='test@example.com',
               password='testpassword'
           )

           # Add permissions
           content_type = ContentType.objects.get_for_model(Patient)
           permissions = Permission.objects.filter(content_type=content_type)
           cls.user.user_permissions.add(*permissions)

           # Create test data
           cls.tag = AllowedTag.objects.create(
               name='Test Tag',
               slug='test-tag'
           )

           cls.patient = Patient.objects.create(
               name='Test Patient',
               birthday='1980-01-01',
               status=Patient.Status.OUTPATIENT,
               created_by=cls.user,
               updated_by=cls.user
           )
           cls.patient.tags.add(cls.tag)

       def setUp(self):
           self.client.login(username='testuser', password='testpassword')

       def test_patient_list_view(self):
           response = self.client.get(reverse('patients:patient_list'))
           self.assertEqual(response.status_code, 200)
           self.assertContains(response, 'Test Patient')
           self.assertTemplateUsed(response, 'patients/patient_list.html')

       def test_patient_detail_view(self):
           response = self.client.get(
               reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
           )
           self.assertEqual(response.status_code, 200)
           self.assertContains(response, 'Test Patient')
           self.assertTemplateUsed(response, 'patients/patient_detail.html')

       def test_patient_create_view(self):
           response = self.client.get(reverse('patients:patient_create'))
           self.assertEqual(response.status_code, 200)
           self.assertTemplateUsed(response, 'patients/patient_form.html')

           # Test form submission
           response = self.client.post(reverse('patients:patient_create'), {
               'name': 'New Patient',
               'birthday': '1990-01-01',
               'gender': 'M',
               'status': Patient.Status.OUTPATIENT,
               'tags': [self.tag.id]
           })
           self.assertEqual(Patient.objects.filter(name='New Patient').count(), 1)

       def test_patient_update_view(self):
           response = self.client.get(
               reverse('patients:patient_update', kwargs={'pk': self.patient.pk})
           )
           self.assertEqual(response.status_code, 200)
           self.assertTemplateUsed(response, 'patients/patient_form.html')

           # Test form submission
           response = self.client.post(
               reverse('patients:patient_update', kwargs={'pk': self.patient.pk}),
               {
                   'name': 'Updated Patient',
                   'birthday': '1980-01-01',
                   'gender': 'M',
                   'status': Patient.Status.OUTPATIENT,
                   'tags': [self.tag.id]
               }
           )
           self.patient.refresh_from_db()
           self.assertEqual(self.patient.name, 'Updated Patient')

       def test_patient_delete_view(self):
           response = self.client.get(
               reverse('patients:patient_delete', kwargs={'pk': self.patient.pk})
           )
           self.assertEqual(response.status_code, 200)
           self.assertTemplateUsed(response, 'patients/patient_confirm_delete.html')

           # Test deletion
           response = self.client.post(
               reverse('patients:patient_delete', kwargs={'pk': self.patient.pk})
           )
           self.assertEqual(Patient.objects.filter(pk=self.patient.pk).count(), 0)
   ```

2. Run view tests:

   ```bash
   python manage.py test apps.patients.tests.test_views
   ```

3. Test with different user roles:

   ```python
   # Add to test_views.py

   def test_permission_required(self):
       # Create a user without permissions
       user_no_perms = User.objects.create_user(
           username='noperms',
           email='noperms@example.com',
           password='testpassword'
       )

       # Log in as the user without permissions
       self.client.logout()
       self.client.login(username='noperms', password='testpassword')

       # Test create view
       response = self.client.get(reverse('patients:patient_create'))
       self.assertEqual(response.status_code, 403)  # Permission denied

       # Test update view
       response = self.client.get(
           reverse('patients:patient_update', kwargs={'pk': self.patient.pk})
       )
       self.assertEqual(response.status_code, 403)  # Permission denied

       # Test delete view
       response = self.client.get(
           reverse('patients:patient_delete', kwargs={'pk': self.patient.pk})
       )
       self.assertEqual(response.status_code, 403)  # Permission denied
   ```

### Step 11: Test Form Submission

1. Create test_forms.py:

   ```python
   from django.test import TestCase
   from django.contrib.auth import get_user_model
   from .models import Patient, PatientHospitalRecord, AllowedTag
   from .forms import PatientForm, PatientHospitalRecordForm, AllowedTagForm

   User = get_user_model()

   class PatientFormTests(TestCase):
       @classmethod
       def setUpTestData(cls):
           cls.user = User.objects.create_user(
               username='testuser',
               email='test@example.com',
               password='testpassword'
           )

       def test_patient_form_valid(self):
           form = PatientForm({
               'name': 'Test Patient',
               'birthday': '1990-01-01',
               'gender': 'M',
               'status': Patient.Status.OUTPATIENT,
           })
           self.assertTrue(form.is_valid())

       def test_patient_form_invalid(self):
           # Missing required field (name)
           form = PatientForm({
               'birthday': '1990-01-01',
               'gender': 'M',
               'status': Patient.Status.OUTPATIENT,
           })
           self.assertFalse(form.is_valid())
           self.assertIn('name', form.errors)

       def test_patient_form_layout(self):
           form = PatientForm()
           self.assertIsNotNone(form.helper)
           self.assertEqual(form.helper.form_method, 'post')

           # Check that layout contains expected fieldsets
           layout_fields = [field.name for field in form.helper.layout.fields]
           self.assertIn('Patient Information', layout_fields)
           self.assertIn('Hospital Information', layout_fields)


   class HospitalRecordFormTests(TestCase):
       @classmethod
       def setUpTestData(cls):
           cls.user = User.objects.create_user(
               username='testuser',
               email='test@example.com',
               password='testpassword'
           )

           cls.patient = Patient.objects.create(
               name='Test Patient',
               birthday='1980-01-01',
               status=Patient.Status.OUTPATIENT,
               created_by=cls.user,
               updated_by=cls.user
           )

       def test_hospital_record_form_valid(self):
           form = PatientHospitalRecordForm({
               'patient': self.patient.id,
               'record_number': 'REC123',
               'admission_date': '2023-01-01',
           })
           self.assertTrue(form.is_valid())

       def test_hospital_record_form_invalid(self):
           # Missing required field (patient)
           form = PatientHospitalRecordForm({
               'record_number': 'REC123',
               'admission_date': '2023-01-01',
           })
           self.assertFalse(form.is_valid())
           self.assertIn('patient', form.errors)


   class AllowedTagFormTests(TestCase):
       def test_tag_form_valid(self):
           form = AllowedTagForm({
               'name': 'Test Tag',
               'slug': 'test-tag',
           })
           self.assertTrue(form.is_valid())

       def test_tag_form_invalid(self):
           # Missing required field (name)
           form = AllowedTagForm({
               'slug': 'test-tag',
           })
           self.assertFalse(form.is_valid())
           self.assertIn('name', form.errors)

       def test_tag_form_slug_autogeneration(self):
           # Test that slug is not required for new instances
           form = AllowedTagForm({
               'name': 'Test Tag',
           })
           self.assertTrue(form.is_valid())
   ```

2. Run form tests:

   ```bash
   python manage.py test apps.patients.tests.test_forms
   ```

### Step 12: Verify App Configuration and Basic Functionality

1. **Verify App Configuration**:

   ```bash
   python manage.py check patients
   ```

2. **Test URL Resolution**:

   ```bash
   python manage.py shell -c "from django.urls import reverse; print(reverse('patients:patient_list'), reverse('patients:patient_create'))"
   ```

3. **Verify Template Loading**:

   ```bash
   python manage.py shell -c "from django.template.loader import get_template; print(get_template('patients/patient_list.html'))"
   ```

4. **Test Basic Model Creation Through Shell**:

   ```bash
   python manage.py shell -c "from apps.patients.models import Patient; from django.contrib.auth import get_user_model; User = get_user_model(); user = User.objects.first(); Patient.objects.create(name='Test Patient', birthday='1990-01-01', status=0, created_by=user, updated_by=user); print('Patient created successfully')"
   ```

5. **Verify Admin Interface Access**:

   ```bash
   python manage.py shell -c "from django.contrib import admin; from apps.patients.models import Patient; print('Patient registered:', Patient in admin.site._registry)"
   ```

6. **Test Form Rendering**:

   ```bash
   python manage.py shell -c "from apps.patients.forms import PatientForm; form = PatientForm(); print(form.as_p()[:100])"
   ```

7. **Test View Access**:

   ```bash
   python manage.py runserver
   ```

   Then visit <http://localhost:8000/patients/> in your browser.

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

```




```
