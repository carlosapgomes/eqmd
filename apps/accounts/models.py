import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class EqmdCustomUser(AbstractUser):
    MEDICAL_DOCTOR = 0
    RESIDENT = 1
    NURSE = 2
    PHYSIOTERAPIST = 3
    STUDENT = 4

    PROFESSION_CHOICES = (
        (MEDICAL_DOCTOR, "Médico"),
        (RESIDENT, "Residente"),
        (NURSE, "Enfermeiro"),
        (PHYSIOTERAPIST, "Fisioterapeuta"),
        (STUDENT, "Estudante"),
    )

    # Custom fields
    profession_type = models.PositiveSmallIntegerField(
        choices=PROFESSION_CHOICES, null=True, blank=True
    )
    professional_registration_number = models.CharField(max_length=20, blank=True)
    country_id_number = models.CharField(max_length=20, blank=True)
    fiscal_number = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # Hospital relationships
    hospitals = models.ManyToManyField(
        'hospitals.Hospital', 
        related_name='members', 
        blank=True,
        help_text="Hospitals this user is a member of"
    )
    last_hospital = models.ForeignKey(
        'hospitals.Hospital', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='last_logged_users',
        help_text="Last hospital context this user was in"
    )
    
    def get_default_hospital(self):
        """Get user's default hospital context"""
        if self.last_hospital and self.hospitals.filter(id=self.last_hospital.id).exists():
            return self.last_hospital
        return self.hospitals.first()
    
    def is_hospital_member(self, hospital):
        """Check if user is a member of the given hospital"""
        if not hospital:
            return False
        return self.hospitals.filter(id=hospital.id).exists()

class UserProfile(models.Model):
    user = models.OneToOneField(EqmdCustomUser, on_delete=models.CASCADE, related_name='profile')
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)

    # Read-only properties exposing user fields
    @property
    def is_active(self):
        return self.user.is_active
    
    @property
    def is_staff(self):
        return self.user.is_staff
    
    @property
    def is_superuser(self):
        return self.user.is_superuser
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def first_name(self):
        return self.user.first_name
    
    @property
    def last_name(self):
        return self.user.last_name
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.user.username
    
    @property
    def profession(self):
        if self.user.profession_type is not None:
            return self.user.get_profession_type_display()
        return ""

    def __str__(self):
        return self.display_name or self.full_name
