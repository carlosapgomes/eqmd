import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.base import ContentFile
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
    
    # Create a mock PDF file
    pdf_file = factory.LazyAttribute(
        lambda obj: ContentFile(
            b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n192\n%%EOF',
            name=f'template_{obj.name.replace(" ", "_").lower()}.pdf'
        )
    )
    
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
        'clinical_notes': 'Sample clinical notes for testing'
    })
    
    # Create a mock generated PDF file
    generated_pdf = factory.LazyAttribute(
        lambda obj: ContentFile(
            b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n192\n%%EOF',
            name=f"completed_{obj.form_template.name.replace(' ', '_').lower()}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
    )
    
    original_filename = factory.LazyAttribute(lambda obj: f"{obj.form_template.name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    file_size = factory.Faker('random_int', min=1024, max=1024*1024)  # 1KB to 1MB