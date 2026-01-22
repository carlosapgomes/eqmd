import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta
from simple_history.models import HistoricalRecords

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
    
    # Security: Force password change for admin-created users
    password_change_required = models.BooleanField(
        default=True,  # New users must change password
        help_text="User must change password before accessing the system"
    )
    
    # Terms acceptance for legal compliance
    terms_accepted = models.BooleanField(
        default=False,
        help_text="User has accepted the terms of use"
    )
    terms_accepted_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the user accepted the terms"
    )
    
    # Research access field
    is_researcher = models.BooleanField(
        default=False,
        verbose_name="Pesquisador Clínico",
        help_text="Permite acesso à funcionalidade de pesquisa clínica em evoluções"
    )
    
    # === Essential User Lifecycle Fields ===

    # Core Expiration Management
    access_expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When user access automatically expires (NULL = no expiration)"
    )
    expiration_reason = models.CharField(
        max_length=100,
        choices=[
            ('end_of_internship', 'End of Internship/Residency'),
            ('end_of_rotation', 'End of Clinical Rotation'),
            ('employment_end', 'Employment Termination'),
            ('leave_of_absence', 'Leave of Absence'),
            ('administrative', 'Administrative Decision'),
            ('inactivity', 'Account Inactivity'),
        ],
        blank=True,
        help_text="Reason for access expiration"
    )

    # Simple Activity Tracking (timestamp only, no complex scoring)
    last_meaningful_activity = models.DateTimeField(
        null=True, blank=True,
        help_text="Last time user performed meaningful action (not just login)"
    )

    # Account Lifecycle Status
    account_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('expiring_soon', 'Expiring Soon (30 days)'),
            ('expired', 'Access Expired'),
            ('inactive', 'Inactive (no recent activity)'),
            ('suspended', 'Administratively Suspended'),
            ('departed', 'No longer with institution'),
            ('renewal_required', 'Renewal Required'),
        ],
        default='active',
        db_index=True,
        help_text="Current account lifecycle status"
    )

    # Role-Specific Fields for Auto-Expiration
    internship_start_date = models.DateField(
        null=True, blank=True,
        help_text="Start date for internship/residency (for automatic expiration calculation)"
    )
    expected_duration_months = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Expected duration in months (for residents/students)"
    )

    # Supervisor for Approval Workflows
    supervisor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='supervised_users',
        help_text="Direct supervisor for renewal approvals"
    )

    # Basic Notification Tracking
    expiration_warning_sent = models.DateTimeField(
        null=True, blank=True,
        help_text="When expiration warning was last sent"
    )
    
    # History tracking
    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
        excluded_fields=['last_login', 'password'],
    )

    @property
    def days_until_expiration(self):
        """Calculate days until access expires"""
        if not self.access_expires_at:
            return None
        delta = self.access_expires_at.date() - timezone.now().date()
        return delta.days

    @property
    def is_expiring_soon(self):
        """Check if user expires within 30 days"""
        days = self.days_until_expiration
        return days is not None and 0 <= days <= 30

    @property
    def is_expired(self):
        """Check if user access has expired"""
        if not self.access_expires_at:
            return False
        return timezone.now() >= self.access_expires_at

    @property
    def days_since_last_activity(self):
        """Calculate days since last meaningful activity"""
        if not self.last_meaningful_activity:
            return None
        delta = timezone.now().date() - self.last_meaningful_activity.date()
        return delta.days

    @property
    def is_inactive(self):
        """Check if user has been inactive for 90+ days"""
        days = self.days_since_last_activity
        return days is not None and days >= 90

    def calculate_role_based_expiration(self):
        """Calculate expiration date based on professional role"""
        if not self.internship_start_date or not self.expected_duration_months:
            return None

        from dateutil.relativedelta import relativedelta
        return self.internship_start_date + relativedelta(months=self.expected_duration_months)

    def update_activity_timestamp(self):
        """Update last meaningful activity timestamp (simplified - no scoring)"""
        self.last_meaningful_activity = timezone.now()

    def extend_access(self, days, reason, extended_by_user):
        """Extend user access by specified days"""
        if not self.access_expires_at:
            self.access_expires_at = timezone.now() + timedelta(days=days)
        else:
            self.access_expires_at += timedelta(days=days)

        self._change_reason = f"Access extended by {days} days. Reason: {reason}"

        # Reset notification tracking
        self.expiration_warning_sent = None

        # Update status if needed
        if self.account_status in ['expired', 'expiring_soon']:
            self.account_status = 'active'

    @property
    def specialties(self):
        """Return all specialties assigned to this user."""
        return [
            us.specialty
            for us in self.user_specialties.filter(specialty__is_active=True)
        ]

    @property
    def primary_specialty(self):
        """Return the user's primary specialty."""
        try:
            return self.user_specialties.get(is_primary=True).specialty
        except UserSpecialty.DoesNotExist:
            # Return first specialty if no primary is set
            specialties = self.specialties
            return specialties[0] if specialties else None

    @property
    def specialty_display(self):
        """Return display string for current/primary specialty."""
        specialty = self.primary_specialty
        return specialty.name if specialty else ""
    

class UserProfile(models.Model):
    user = models.OneToOneField(EqmdCustomUser, on_delete=models.CASCADE, related_name='profile')
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    matrix_localpart = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[a-z0-9][a-z0-9._-]{0,63}$",
                message="Matrix localpart must use lowercase letters, numbers, dots, underscores, or hyphens.",
            )
        ],
        help_text="Matrix localpart without @ or domain (e.g., joao.silva).",
    )
    matrix_provisioned_at = models.DateTimeField(null=True, blank=True)
    matrix_provisioned_by = models.ForeignKey(
        EqmdCustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matrix_provisioned_profiles",
    )
    current_specialty = models.ForeignKey(
        'MedicalSpecialty',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_users',
        verbose_name="Especialidade Atual",
        help_text="Especialidade selecionada pelo usuário para uso atual"
    )

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

    @property
    def current_specialty_display(self):
        """Return display name of current specialty."""
        if self.current_specialty:
            return self.current_specialty.name
        return self.user.specialty_display

    def _normalize_matrix_localpart(self):
        if self.matrix_localpart is None:
            return
        localpart = self.matrix_localpart.strip()
        if not localpart:
            self.matrix_localpart = None
            return
        self.matrix_localpart = localpart.lower()

    def clean(self):
        self._normalize_matrix_localpart()
        super().clean()

    def save(self, *args, **kwargs):
        self._normalize_matrix_localpart()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name or self.full_name


class MedicalSpecialty(models.Model):
    """Registry of medical specialties available in the system."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome da Especialidade",
        help_text="Ex: Cirurgia Vascular, Cirurgia Geral"
    )
    abbreviation = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="Sigla",
        help_text="Ex: CIRVASC, CIRGER"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descrição",
        help_text="Descrição detalhada da especialidade"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Ativa",
        help_text="Se desmarcado, esta especialidade não estará disponível para seleção"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Especialidade Médica"
        verbose_name_plural = "Especialidades Médicas"
        ordering = ['name']

    def __str__(self):
        return self.name


class UserSpecialty(models.Model):
    """Association between users and their medical specialties."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        EqmdCustomUser,
        on_delete=models.CASCADE,
        related_name='user_specialties',
        verbose_name="Usuário"
    )
    specialty = models.ForeignKey(
        MedicalSpecialty,
        on_delete=models.PROTECT,  # Prevent deletion if assigned to users
        related_name='users',
        verbose_name="Especialidade"
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name="Especialidade Principal",
        help_text="Marque como especialidade principal (ex: do residente)"
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="Atribuída em")
    assigned_by = models.ForeignKey(
        EqmdCustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_specialties',
        verbose_name="Atribuída por"
    )

    class Meta:
        verbose_name = "Especialidade do Usuário"
        verbose_name_plural = "Especialidades dos Usuários"
        unique_together = ['user', 'specialty']  # One user can't have same specialty twice
        ordering = ['-is_primary', 'specialty__name']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.specialty.name}"
