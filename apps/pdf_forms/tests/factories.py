import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.pdf_forms.models import PDFFormTemplate, PDFFormSubmission
from apps.patients.models import Patient
from apps.events.models import Event

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    username = factory.Sequence(lambda n: f'user{n}')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True


class PDFFormTemplateFactory(DjangoModelFactory):
    class Meta:
        model = PDFFormTemplate

    name = factory.Sequence(lambda n: f'Form Template {n}')
    description = factory.Faker('text', max_nb_chars=200)
    
    # PDF template file path (points to actual template files in tests)
    pdf_file = factory.Sequence(lambda n: f'/fake/path/to/template_{n}.pdf')
    
    form_fields = factory.LazyAttribute(lambda obj: {
        'patient_name': {
            'type': 'text',
            'required': True,
            'label': 'Patient Name',
            'max_length': 100,
            'x': 5.0,
            'y': 10.0,
            'width': 10.0,
            'height': 0.7,
            'font_size': 12
        },
        'date_of_birth': {
            'type': 'date',
            'required': True,
            'label': 'Date of Birth',
            'x': 5.0,
            'y': 11.5,
            'width': 5.0,
            'height': 0.7,
            'font_size': 12
        }
    })
    hospital_specific = True
    is_active = True
    created_by = factory.SubFactory(UserFactory)
    
    @factory.post_generation
    def skip_validation(obj, create, extracted, **kwargs):
        if create:
            obj._skip_validation = True


class PatientFactory(DjangoModelFactory):
    class Meta:
        model = Patient

    name = factory.Faker('name')
    birthday = factory.Faker('date_of_birth', minimum_age=18, maximum_age=90)
    fiscal_number = factory.Sequence(lambda n: f'{n:011d}')
    healthcard_number = factory.Sequence(lambda n: f'HC{n:09d}')
    status = Patient.Status.OUTPATIENT
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.SubFactory(UserFactory)


class PDFFormSubmissionFactory(DjangoModelFactory):
    class Meta:
        model = PDFFormSubmission

    form_template = factory.SubFactory(PDFFormTemplateFactory)
    patient = factory.SubFactory(PatientFactory)
    created_by = factory.SubFactory(UserFactory)
    event_datetime = factory.LazyFunction(timezone.now)
    event_type = Event.PDF_FORM_EVENT
    description = factory.LazyAttribute(lambda obj: f"Formulário PDF: {obj.form_template.name}")
    
    form_data = factory.LazyAttribute(lambda obj: {
        'patient_name': obj.patient.name,
        'date_of_birth': obj.patient.birthday.strftime('%Y-%m-%d') if obj.patient.birthday else '',
        'clinical_notes': 'Sample clinical notes for testing',
        'blood_type': 'O+',
        'urgent': False,
        'additional_notes': 'Generated test data for PDF form submission'
    })