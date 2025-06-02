"""
Factory classes for creating test data for the accounts app.
"""
import factory
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating EqmdCustomUser instances."""
    
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    profession_type = factory.Faker('random_int', min=0, max=4)
    professional_registration_number = factory.Faker('numerify', text='CRM-####')
    country_id_number = factory.Faker('numerify', text='###.###.###-##')
    fiscal_number = factory.Faker('numerify', text='###.###.###-##')
    phone = factory.Faker('phone_number')
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """Set password for the user."""
        if not create:
            return
        
        password = extracted or 'testpass123'
        self.set_password(password)
        self.save()


class StaffUserFactory(UserFactory):
    """Factory for creating staff users."""
    
    is_staff = True
    profession_type = 0  # MEDICAL_DOCTOR


class SuperUserFactory(UserFactory):
    """Factory for creating superuser instances."""
    
    is_staff = True
    is_superuser = True
    profession_type = 0  # MEDICAL_DOCTOR


class UserProfileFactory(factory.django.DjangoModelFactory):
    """Factory for creating UserProfile instances.

    Note: Since profiles are automatically created via signals,
    this factory should be used carefully to avoid conflicts.
    """

    class Meta:
        model = UserProfile
        django_get_or_create = ('user',)  # Get existing profile if user already has one

    user = factory.SubFactory(UserFactory)
    display_name = factory.LazyAttribute(
        lambda obj: f"Dr. {obj.user.last_name}" if obj.user.profession_type == 0
        else f"{obj.user.first_name} {obj.user.last_name}"
    )
    bio = factory.Faker('text', max_nb_chars=200)


class DoctorFactory(UserFactory):
    """Factory for creating doctor users."""
    
    profession_type = 0  # MEDICAL_DOCTOR
    professional_registration_number = factory.Faker('numerify', text='CRM-#####')


class NurseFactory(UserFactory):
    """Factory for creating nurse users."""
    
    profession_type = 2  # NURSE
    professional_registration_number = factory.Faker('numerify', text='COREN-#####')


class StudentFactory(UserFactory):
    """Factory for creating student users."""
    
    profession_type = 4  # STUDENT
    professional_registration_number = factory.Faker('numerify', text='EST-#####')
