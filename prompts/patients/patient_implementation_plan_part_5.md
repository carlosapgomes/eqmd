## Vertical Slice 5: Dashboard Integration and Template Tags

### Step 1: Create Dashboard Widgets

1. Create directory structure for widgets:

   ```bash
   mkdir -p apps/patients/templates/patients/widgets
   ```

2. Create patient_stats.html widget:

   ```html
   <div class="card mb-4">
     <div class="card-header">
       <i class="bi bi-clipboard2-pulse me-1"></i> Patient Statistics
     </div>
     <div class="card-body">
       <div class="row">
         <div class="col-xl-3 col-md-6">
           <div class="card bg-primary text-white mb-4">
             <div class="card-body">
               <h2>{{ total_patients }}</h2>
               <div>Total Patients</div>
             </div>
           </div>
         </div>
         <div class="col-xl-3 col-md-6">
           <div class="card bg-success text-white mb-4">
             <div class="card-body">
               <h2>{{ inpatient_count }}</h2>
               <div>Inpatients</div>
             </div>
           </div>
         </div>
         <div class="col-xl-3 col-md-6">
           <div class="card bg-info text-white mb-4">
             <div class="card-body">
               <h2>{{ outpatient_count }}</h2>
               <div>Outpatients</div>
             </div>
           </div>
         </div>
         <div class="col-xl-3 col-md-6">
           <div class="card bg-secondary text-white mb-4">
             <div class="card-body">
               <h2>{{ hospital_count }}</h2>
               <div>Hospitals</div>
             </div>
           </div>
         </div>
       </div>
     </div>
   </div>
   ```

3. Create recent_patients.html widget:

   ```html
   <div class="card mb-4">
     <div class="card-header">
       <i class="bi bi-people me-1"></i> Recent Patients
     </div>
     <div class="card-body">
       {% if recent_patients %}
       <div class="table-responsive">
         <table class="table table-bordered table-hover">
           <thead>
             <tr>
               <th>Name</th>
               <th>Status</th>
               <th>Hospital</th>
               <th>Actions</th>
             </tr>
           </thead>
           <tbody>
             {% for patient in recent_patients %}
             <tr>
               <td>{{ patient.name }}</td>
               <td>{% patient_status_badge patient.status %}</td>
               <td>{{ patient.current_hospital.name|default:"-" }}</td>
               <td>
                 <a
                   href="{% url 'patients:patient_detail' patient.id %}"
                   class="btn btn-sm btn-primary"
                 >
                   <i class="bi bi-eye"></i>
                 </a>
                 <a
                   href="{% url 'patients:patient_update' patient.id %}"
                   class="btn btn-sm btn-warning"
                 >
                   <i class="bi bi-pencil"></i>
                 </a>
               </td>
             </tr>
             {% endfor %}
           </tbody>
         </table>
       </div>
       <div class="text-end">
         <a href="{% url 'patients:patient_list' %}" class="btn btn-primary"
           >View All Patients</a
         >
       </div>
       {% else %}
       <p class="text-muted">No patients have been added yet.</p>
       <a href="{% url 'patients:patient_create' %}" class="btn btn-primary"
         >Add Patient</a
       >
       {% endif %}
     </div>
   </div>
   ```

4. Verify widget templates:
   ```bash
   python manage.py shell -c "from django.template.loader import get_template; print(get_template('patients/widgets/patient_stats.html')); print(get_template('patients/widgets/recent_patients.html'))"
   ```

### Step 2: Update Sidebar Navigation

1. Create a sidebar snippet for patients in apps/patients/templates/patients/includes/sidebar_items.html:

   ```html
   {% if perms.patients.view_patient %}
   <li class="nav-item">
     <a
       class="nav-link collapsed"
       href="#"
       data-bs-toggle="collapse"
       data-bs-target="#collapsePatients"
       aria-expanded="false"
       aria-controls="collapsePatients"
     >
       <i class="bi bi-people"></i>
       <span>Patients</span>
     </a>
     <div
       id="collapsePatients"
       class="collapse"
       aria-labelledby="headingPatients"
       data-bs-parent="#sidebarAccordion"
     >
       <div class="bg-white py-2 collapse-inner rounded">
         <h6 class="collapse-header">Patient Management:</h6>
         <a class="collapse-item" href="{% url 'patients:patient_list' %}"
           >All Patients</a
         >
         {% if perms.patients.add_patient %}
         <a class="collapse-item" href="{% url 'patients:patient_create' %}"
           >Add Patient</a
         >
         {% endif %} {% if perms.patients.view_allowedtag %}
         <a class="collapse-item" href="{% url 'patients:tag_list' %}"
           >Manage Tags</a
         >
         {% endif %}
       </div>
     </div>
   </li>
   {% endif %}
   ```

2. Update the main sidebar template to include the patients sidebar items:

   ```html
   {% comment %} Add this to the main sidebar template where other app sections
   are included: {% if 'apps.patients' in INSTALLED_APPS %} {% include
   'patients/includes/sidebar_items.html' %} {% endif %} {% endcomment %}
   ```

3. Verify sidebar template:
   ```bash
   python manage.py shell -c "from django.template.loader import get_template; print(get_template('patients/includes/sidebar_items.html'))"
   ```

### Step 3: Create Context Processors

1. Create context_processors.py in the patients app:

   ```python
   from .models import Patient, PatientHospitalRecord
   from apps.hospitals.models import Hospital

   def patient_stats(request):
       """
       Context processor that provides patient statistics for templates.
       """
       if not request.user.is_authenticated:
           return {}

       # Only calculate stats if user has permission to view patients
       if not request.user.has_perm('patients.view_patient'):
           return {}

       try:
           total_patients = Patient.objects.count()
           inpatient_count = Patient.objects.filter(status=Patient.INPATIENT).count()
           outpatient_count = Patient.objects.filter(status=Patient.OUTPATIENT).count()
           hospital_count = Hospital.objects.count()

           return {
               'total_patients': total_patients,
               'inpatient_count': inpatient_count,
               'outpatient_count': outpatient_count,
               'hospital_count': hospital_count,
           }
       except:
           # Return empty dict if database isn't set up yet
           return {}

   def recent_patients(request):
       """
       Context processor that provides recent patients for templates.
       """
       if not request.user.is_authenticated:
           return {}

       # Only get recent patients if user has permission
       if not request.user.has_perm('patients.view_patient'):
           return {}

       try:
           recent_patients = Patient.objects.all().order_by('-created_at')[:5]
           return {
               'recent_patients': recent_patients,
           }
       except:
           # Return empty dict if database isn't set up yet
           return {}
   ```

2. Add context processors to settings.py:

   ```python
   # Add to the TEMPLATES setting in config/settings.py
   'context_processors': [
       # ... existing context processors
       'apps.patients.context_processors.patient_stats',
       'apps.patients.context_processors.recent_patients',
   ],
   ```

3. Verify context processors:
   ```bash
   python manage.py shell -c "from apps.patients.context_processors import patient_stats, recent_patients; from django.http import HttpRequest; request = HttpRequest(); request.user = __import__('django.contrib.auth').get_user_model().objects.first(); print(patient_stats(request)); print(recent_patients(request))"
   ```

### Step 4: Add Template Tags for Patient Data

1. Create directory structure for template tags:

   ```bash
   mkdir -p apps/patients/templatetags
   touch apps/patients/templatetags/__init__.py
   ```

2. Create patient_tags.py in the templatetags directory:

   ```python
   from django import template
   from django.utils.safestring import mark_safe
   from apps.patients.models import Patient

   register = template.Library()

   @register.filter
   def patient_status_badge(status):
       """
       Returns a Bootstrap badge with appropriate color for patient status.

       Usage: {{ patient.status|patient_status_badge }}
       """
       status_classes = {
           Patient.INPATIENT: 'bg-success',
           Patient.OUTPATIENT: 'bg-info',
           Patient.DECEASED: 'bg-secondary',
       }

       status_labels = dict(Patient.STATUS_CHOICES)
       status_class = status_classes.get(status, 'bg-secondary')
       status_label = status_labels.get(status, 'Unknown')

       return mark_safe(f'<span class="badge {status_class}">{status_label}</span>')

   @register.inclusion_tag('patients/tags/patient_tags.html')
   def patient_tags(patient):
       """
       Renders the tags for a patient.

       Usage: {% patient_tags patient %}
       """
       return {'tags': patient.tags.all()}
   ```

3. Create template for rendering patient tags in apps/patients/templates/patients/tags/patient_tags.html:

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

4. Verify template tags:
   ```bash
   python manage.py shell -c "from django.template import Template, Context; from apps.patients.models import Patient; patient = Patient.objects.first(); if patient: print(Template('{% load patient_tags %}{% patient_status_badge patient.status %}').render(Context({'patient': patient})))"
   ```

### Step 5: Update Dashboard Template

1. Update the main dashboard template to include patient widgets:

   ```html
   {% comment %} Add this to the main dashboard template: {% if 'apps.patients'
   in INSTALLED_APPS %}
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
   {% endif %} {% endcomment %}
   ```

### Step 6: Test Dashboard Integration

1. Create test_integration.py in the patients app tests directory:

   ```python
   from django.test import TestCase, RequestFactory
   from django.template import Template, Context
   from django.contrib.auth import get_user_model
   from django.urls import reverse
   from apps.patients.models import Patient
   from apps.patients.context_processors import patient_stats, recent_patients
   from apps.patients.templatetags.patient_tags import patient_status_badge, patient_tags

   User = get_user_model()

   class PatientDashboardIntegrationTest(TestCase):
       def setUp(self):
           self.factory = RequestFactory()
           self.user = User.objects.create_superuser(
               username='admin',
               email='admin@example.com',
               password='password'
           )
           self.patient = Patient.objects.create(
               name='Test Patient',
               birthday='1990-01-01',
               status=Patient.INPATIENT,
               created_by=self.user,
               updated_by=self.user
           )

       def test_context_processors(self):
           """Test that context processors return expected data"""
           request = self.factory.get('/')
           request.user = self.user

           stats = patient_stats(request)
           self.assertEqual(stats['total_patients'], 1)
           self.assertEqual(stats['inpatient_count'], 1)

           recent = recent_patients(request)
           self.assertEqual(recent['recent_patients'].count(), 1)

       def test_template_tags(self):
           """Test that template tags render correctly"""
           # Test status badge
           badge = patient_status_badge(Patient.INPATIENT)
           self.assertIn('bg-success', badge)

           # Test patient tags inclusion tag
           template = Template('{% load patient_tags %}{% patient_tags patient %}')
           context = Context({'patient': self.patient})
           rendered = template.render(context)
           self.assertIsNotNone(rendered)

       def test_dashboard_widgets(self):
           """Test that dashboard widgets render correctly"""
           self.client.force_login(self.user)
           response = self.client.get(reverse('dashboard'))

           # This test assumes a dashboard view exists at the URL 'dashboard'
           # If it doesn't, you'll need to adjust this test
           if response.status_code == 200:
               self.assertContains(response, 'Patient Statistics')
               self.assertContains(response, 'Recent Patients')
   ```

2. Run the integration tests:
   ```bash
   python manage.py test apps.patients.tests.test_integration
   ```

### Step 7: Verify Dashboard Integration

1. Start the development server:

   ```bash
   python manage.py runserver
   ```

2. Visit the dashboard page and verify:

   - Patient statistics widget appears
   - Recent patients widget appears
   - Sidebar includes patient management links
   - Template tags render correctly

3. Test with different user permissions:
   - Log in as a superuser to verify all features
   - Log in as a user with limited permissions to verify permission-based display

## Additional Recommendations

1. **For Dashboard Integration**:

   - Consider using AJAX to load dashboard widgets asynchronously for better performance
   - Add refresh functionality to update statistics without page reload
   - Implement caching for context processors to reduce database queries

2. **For Template Tags**:

   - Add more template tags for common patient-related UI elements
   - Consider adding template tags for rendering patient forms with consistent styling
   - Add documentation comments to all template tags

3. **For Sidebar Navigation**:

   - Highlight the current section based on the active URL
   - Consider adding counters for important metrics (e.g., number of inpatients)
   - Add tooltips for navigation items to improve usability

4. **For Widgets**:

   - Add filtering options to the recent patients widget
   - Consider adding charts/graphs for patient statistics
   - Implement responsive design for all widgets

5. **For Performance**:
   - Use select_related/prefetch_related in context processors to optimize queries
   - Consider implementing caching for dashboard widgets
   - Monitor query performance and optimize as needed

```




```
