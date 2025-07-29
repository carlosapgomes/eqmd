import factory
from factory import fuzzy
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
import random

from apps.patients.models import Patient
from apps.drugtemplates.models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem
from apps.outpatientprescriptions.models import OutpatientPrescription, PrescriptionItem
from apps.sample_content.models import SampleContent
from apps.events.models import Event

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating User instances with medical professions."""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    profession = fuzzy.FuzzyChoice([1, 2, 3, 4, 5])  # Medical professions
    is_active = True
    
    @factory.post_generation
    def set_password(obj, create, extracted, **kwargs):
        if create:
            obj.set_password('testpass123')
            obj.save()


class DoctorFactory(UserFactory):
    """Factory for creating Doctor users."""
    profession = 1  # Doctor
    first_name = factory.Faker('first_name_male')
    last_name = factory.Faker('last_name')
    

class ResidentFactory(UserFactory):
    """Factory for creating Resident users."""
    profession = 2  # Resident
    

class NurseFactory(UserFactory):
    """Factory for creating Nurse users."""
    profession = 3  # Nurse
    

class PhysiotherapistFactory(UserFactory):
    """Factory for creating Physiotherapist users."""
    profession = 4  # Physiotherapist
    

class StudentFactory(UserFactory):
    """Factory for creating Student users."""
    profession = 5  # Student




class PatientFactory(factory.django.DjangoModelFactory):
    """Factory for creating Patient instances."""
    
    class Meta:
        model = Patient
    
    name = factory.Faker('name')
    birthday = factory.Faker('date_of_birth', minimum_age=18, maximum_age=90)
    gender = factory.LazyFunction(
        lambda: random.choices(
            [Patient.GenderChoices.MALE, Patient.GenderChoices.FEMALE, 
             Patient.GenderChoices.OTHER, Patient.GenderChoices.NOT_INFORMED],
            weights=[48, 48, 2, 2]
        )[0]
    )
    
    # Patient statuses from Patient model
    status = fuzzy.FuzzyChoice([1, 2, 3, 4, 5, 6])  # Various patient statuses
    
    # Health card and fiscal numbers
    health_card_number = factory.Sequence(lambda n: f'HC{n:08d}')
    fiscal_number = factory.Sequence(lambda n: f'FN{n:09d}')
    
    created_by = factory.SubFactory(DoctorFactory)
    updated_by = factory.SelfAttribute('created_by')
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class OutpatientFactory(PatientFactory):
    """Factory for creating outpatient Patient instances."""
    status = 1  # Outpatient


class InpatientFactory(PatientFactory):
    """Factory for creating inpatient Patient instances."""
    status = 2  # Inpatient


class DrugTemplateFactory(factory.django.DjangoModelFactory):
    """Factory for creating DrugTemplate instances."""
    
    class Meta:
        model = DrugTemplate
    
    name = factory.Faker('word')
    presentation = factory.LazyFunction(
        lambda: f'{random.randint(5, 1000)}mg {random.choice(["comprimidos", "cápsulas", "xarope", "gotas"])}'
    )
    usage_instructions = factory.Faker('text', max_nb_chars=200)
    creator = factory.SubFactory(DoctorFactory)
    is_public = fuzzy.FuzzyChoice([True, False])
    usage_count = factory.LazyFunction(lambda: random.randint(0, 100))
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class PublicDrugTemplateFactory(DrugTemplateFactory):
    """Factory for creating public DrugTemplate instances."""
    is_public = True


class PrivateDrugTemplateFactory(DrugTemplateFactory):
    """Factory for creating private DrugTemplate instances."""
    is_public = False


class PrescriptionTemplateFactory(factory.django.DjangoModelFactory):
    """Factory for creating PrescriptionTemplate instances."""
    
    class Meta:
        model = PrescriptionTemplate
    
    name = factory.Faker('sentence', nb_words=4)
    creator = factory.SubFactory(DoctorFactory)
    is_public = fuzzy.FuzzyChoice([True, False])
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class PrescriptionTemplateItemFactory(factory.django.DjangoModelFactory):
    """Factory for creating PrescriptionTemplateItem instances."""
    
    class Meta:
        model = PrescriptionTemplateItem
    
    template = factory.SubFactory(PrescriptionTemplateFactory)
    drug_name = factory.Faker('word')
    presentation = factory.LazyFunction(
        lambda: f'{random.randint(5, 1000)}mg {random.choice(["comprimidos", "cápsulas", "ml"])}'
    )
    usage_instructions = factory.Faker('text', max_nb_chars=150)
    quantity = factory.LazyFunction(
        lambda: f'{random.randint(10, 90)} {random.choice(["comprimidos", "cápsulas", "ml"])}'
    )
    order = factory.Sequence(lambda n: n + 1)
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class OutpatientPrescriptionFactory(factory.django.DjangoModelFactory):
    """Factory for creating OutpatientPrescription instances."""
    
    class Meta:
        model = OutpatientPrescription
    
    event_datetime = factory.LazyFunction(timezone.now)
    description = factory.Faker('sentence', nb_words=6)
    instructions = factory.Faker('text', max_nb_chars=300)
    status = fuzzy.FuzzyChoice(['draft', 'finalized'])
    prescription_date = factory.LazyFunction(lambda: timezone.now().date())
    patient = factory.SubFactory(OutpatientFactory)
    created_by = factory.SubFactory(DoctorFactory)
    updated_by = factory.SelfAttribute('created_by')
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class DraftPrescriptionFactory(OutpatientPrescriptionFactory):
    """Factory for creating draft OutpatientPrescription instances."""
    status = 'draft'


class FinalizedPrescriptionFactory(OutpatientPrescriptionFactory):
    """Factory for creating finalized OutpatientPrescription instances."""
    status = 'finalized'


class RecentPrescriptionFactory(OutpatientPrescriptionFactory):
    """Factory for creating recent OutpatientPrescription instances (within 24 hours)."""
    event_datetime = factory.LazyFunction(
        lambda: timezone.now() - timedelta(hours=random.randint(1, 23))
    )
    prescription_date = factory.LazyFunction(
        lambda: (timezone.now() - timedelta(hours=random.randint(1, 23))).date()
    )


class OldPrescriptionFactory(OutpatientPrescriptionFactory):
    """Factory for creating old OutpatientPrescription instances (older than 24 hours)."""
    event_datetime = factory.LazyFunction(
        lambda: timezone.now() - timedelta(days=random.randint(2, 30))
    )
    prescription_date = factory.LazyFunction(
        lambda: (timezone.now() - timedelta(days=random.randint(2, 30))).date()
    )


class PrescriptionItemFactory(factory.django.DjangoModelFactory):
    """Factory for creating PrescriptionItem instances."""
    
    class Meta:
        model = PrescriptionItem
    
    prescription = factory.SubFactory(OutpatientPrescriptionFactory)
    drug_name = factory.Faker('word')
    presentation = factory.LazyFunction(
        lambda: f'{random.randint(5, 1000)}mg {random.choice(["comprimidos", "cápsulas", "ml"])}'
    )
    usage_instructions = factory.Faker('text', max_nb_chars=150)
    quantity = factory.LazyFunction(
        lambda: f'{random.randint(10, 90)} {random.choice(["comprimidos", "cápsulas", "ml"])}'
    )
    order = factory.Sequence(lambda n: n + 1)
    source_template = factory.SubFactory(DrugTemplateFactory, _create_via=factory.Maybe(
        factory.Faker('boolean', chance_of_getting_true=30),  # 30% chance of having source template
        yes_declaration=factory.SubFactory(DrugTemplateFactory),
        no_declaration=None
    ))


class SampleContentFactory(factory.django.DjangoModelFactory):
    """Factory for creating SampleContent instances."""
    
    class Meta:
        model = SampleContent
    
    title = factory.Faker('sentence', nb_words=4)
    content = factory.Faker('text', max_nb_chars=500)
    event_type = Event.OUTPT_PRESCRIPTION_EVENT  # Prescription event type
    created_by = factory.SubFactory(DoctorFactory)
    updated_by = factory.SelfAttribute('created_by')
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


# Trait factories for creating related objects together

class PrescriptionWithItemsFactory(OutpatientPrescriptionFactory):
    """Factory for creating OutpatientPrescription with related items."""
    
    @factory.post_generation
    def items(self, create, extracted, **kwargs):
        if not create:
            return
        
        if extracted:
            # If a number is passed, create that many items
            for _ in range(extracted):
                PrescriptionItemFactory(prescription=self)
        else:
            # Default: create 2-4 items
            for i in range(random.randint(2, 4)):
                PrescriptionItemFactory(prescription=self, order=i + 1)


class PrescriptionTemplateWithItemsFactory(PrescriptionTemplateFactory):
    """Factory for creating PrescriptionTemplate with related items."""
    
    @factory.post_generation
    def items(self, create, extracted, **kwargs):
        if not create:
            return
        
        if extracted:
            # If a number is passed, create that many items
            for i in range(extracted):
                PrescriptionTemplateItemFactory(template=self, order=i + 1)
        else:
            # Default: create 2-3 items
            for i in range(random.randint(2, 3)):
                PrescriptionTemplateItemFactory(template=self, order=i + 1)


class CompleteTestDataFactory:
    """Factory for creating complete test data sets."""
    
    @staticmethod
    def create_staff_users():
        """Create various staff members."""
        doctor = DoctorFactory()
        resident = ResidentFactory()
        nurse = NurseFactory()
        physiotherapist = PhysiotherapistFactory()
        student = StudentFactory()
        
        return {
            'doctor': doctor,
            'resident': resident,
            'nurse': nurse,
            'physiotherapist': physiotherapist,
            'student': student,
        }
    
    @staticmethod
    def create_prescription_scenario():
        """Create a complete prescription scenario with all related objects."""
        doctor = DoctorFactory()
        patient = OutpatientFactory(created_by=doctor)
        
        # Create drug templates
        drug_template1 = PublicDrugTemplateFactory(creator=doctor)
        drug_template2 = PrivateDrugTemplateFactory(creator=doctor)
        
        # Create prescription template
        prescription_template = PrescriptionTemplateWithItemsFactory(
            creator=doctor, items=3
        )
        
        # Create prescription with items
        prescription = PrescriptionWithItemsFactory(
            patient=patient,
            created_by=doctor,
            items=3
        )
        
        # Create sample content
        sample_content = SampleContentFactory(created_by=doctor)
        
        return {
            'doctor': doctor,
            'patient': patient,
            'drug_template1': drug_template1,
            'drug_template2': drug_template2,
            'prescription_template': prescription_template,
            'prescription': prescription,
            'sample_content': sample_content,
        }
    
    @staticmethod
    def create_permission_test_data():
        """Create test data for permission testing."""
        # Create users with different professions
        doctor = DoctorFactory()
        resident = ResidentFactory()
        nurse = NurseFactory()
        student = StudentFactory()
        
        # Create patients with different statuses
        outpatient = OutpatientFactory(created_by=doctor)
        inpatient = InpatientFactory(created_by=doctor)
        
        # Create prescriptions by different users
        doctor_prescription = RecentPrescriptionFactory(
            patient=outpatient, created_by=doctor
        )
        resident_prescription = RecentPrescriptionFactory(
            patient=outpatient, created_by=resident
        )
        old_prescription = OldPrescriptionFactory(
            patient=outpatient, created_by=doctor
        )
        
        return {
            'users': {
                'doctor': doctor,
                'resident': resident,
                'nurse': nurse,
                'student': student,
            },
            'patients': {
                'outpatient': outpatient,
                'inpatient': inpatient,
            },
            'prescriptions': {
                'doctor_prescription': doctor_prescription,
                'resident_prescription': resident_prescription,
                'old_prescription': old_prescription,
            }
        }


# Utility functions for tests

def create_prescription_with_template_data():
    """Create a prescription using data from a template."""
    doctor = DoctorFactory()
    patient = OutpatientFactory(created_by=doctor)
    
    # Create template with items
    template = PrescriptionTemplateWithItemsFactory(creator=doctor, items=2)
    
    # Create prescription
    prescription = OutpatientPrescriptionFactory(
        patient=patient,
        created_by=doctor,
        description=f'Based on template: {template.name}'
    )
    
    # Copy template data to prescription
    prescription.copy_from_prescription_template(template)
    
    return {
        'doctor': doctor,
        'patient': patient,
        'template': template,
        'prescription': prescription,
    }


def create_prescription_with_drug_templates():
    """Create a prescription with items based on drug templates."""
    doctor = DoctorFactory()
    patient = OutpatientFactory(created_by=doctor)
    prescription = OutpatientPrescriptionFactory(patient=patient, created_by=doctor)
    
    # Create drug templates
    templates = [
        PublicDrugTemplateFactory(creator=doctor),
        PublicDrugTemplateFactory(creator=doctor),
    ]
    
    # Create prescription items based on templates
    items = []
    for i, template in enumerate(templates):
        item = PrescriptionItem(
            prescription=prescription,
            quantity=f'{random.randint(20, 60)} comprimidos',
            order=i + 1
        )
        item.copy_from_drug_template(template)
        item.save()
        items.append(item)
    
    return {
        'doctor': doctor,
        'patient': patient,
        'prescription': prescription,
        'templates': templates,
        'items': items,
    }


def create_multi_user_test_scenario():
    """Create a scenario with multiple users and cross-permissions."""
    
    # Create users
    doctor1 = DoctorFactory()
    doctor2 = DoctorFactory()
    resident = ResidentFactory()
    nurse = NurseFactory()
    
    # Create patients
    patient1 = OutpatientFactory(created_by=doctor1)
    patient2 = InpatientFactory(created_by=doctor2)
    
    # Create prescriptions by different users
    prescriptions = [
        RecentPrescriptionFactory(patient=patient1, created_by=doctor1),
        RecentPrescriptionFactory(patient=patient1, created_by=resident),
        OldPrescriptionFactory(patient=patient2, created_by=doctor2),
    ]
    
    # Add items to prescriptions
    for prescription in prescriptions:
        PrescriptionItemFactory.create_batch(
            random.randint(1, 3), prescription=prescription
        )
    
    return {
        'users': {
            'doctor1': doctor1,
            'doctor2': doctor2,
            'resident': resident,
            'nurse': nurse,
        },
        'patients': {
            'patient1': patient1,
            'patient2': patient2,
        },
        'prescriptions': prescriptions,
    }