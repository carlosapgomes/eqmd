# Update the app "patients" in the current project

- this app should be added to the `INSTALLED_APPS` list in the `config/settings.py` file

## New models

- all models in this app should be created in the `models.py` file in the `apps/patients` directory

### Create a New Model `Patient`

- this model should extend the `models.Model` model from `django.db.models`
- this model should be added to the `admin.py` file in the `apps/patients` directory
- this model should be added to the `forms.py` file in the `apps/patients` directory
- this model should be added to the `views.py` file in the `apps/patients` directory
- this model should have the following fields:

  ```python
    objects = models.Manager()
    INPATIENT = 0
    OUTPATIENT = 1
    DECEASED = 2
    UNKNOWN = 0
    MALE = 1
    FEMALE = 2
    NOT_APPLICABLE = 9

    STATUS_CHOICES = (
        (INPATIENT, "Internado"),
        (OUTPATIENT, "Ambulatorial"),
        (DECEASED, "Falecido"),
    )
    GENDER_CHOICES = (
        (UNKNOWN, "Não informado"),
        (MALE, "Masculino"),
        (FEMALE, "Feminino"),
        (NOT_APPLICABLE, "Não se aplica"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=False, verbose_name="Nome")
    gender = models.PositiveSmallIntegerField(
        choices=GENDER_CHOICES, default=UNKNOWN, verbose_name="Gênero"
    )
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
    # Use the Ward model directly if available, otherwise use a string reference
    ward = models.ForeignKey(
        Ward if Ward is not None else "wards.Ward",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name="Enfermaria",
    )
    bed = models.CharField(max_length=10, blank=True, verbose_name="Leito")
    # record_number field removed

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
  ```

- this model should use django taggit for the `tags` field with a restrict allowed tags. Maybe you should create a new model for the tags as this example:

  ```python
  class AllowedTag(TagBase):
      class Meta:
          verbose_name = "Allowed Tag"
          verbose_name_plural = "Allowed Tags"
          ordering = ["name"]
  ```

  ```python
  class UUIDTaggedItem(GenericUUIDTaggedItemBase):
      tag = models.ForeignKey(
          AllowedTag, on_delete=models.CASCADE, related_name="tagged_items"
      )

      class Meta:
          verbose_name = "Tag"
          verbose_name_plural = "Tags"
  ```

- this model should have the following methods:

  ```python
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("patients:patient_detail", kwargs={"pk": self.pk})

    @property
    def status_display(self):
        return dict(self.STATUS_CHOICES)[self.status]

    @property
    def gender_display(self):
        return dict(self.GENDER_CHOICES)[self.gender]

    @property
    def hospital(self):
        """Get the hospital where the patient is currently admitted"""
        # First check direct hospital relationship
        if self.current_hospital:
            return self.current_hospital

        # Fall back to ward's hospital if available
        if self.ward and self.ward.hospital:
            return self.ward.hospital

        return None

    @property
    def is_inpatient(self):
        """Check if patient is currently an inpatient"""
        return self.status == self.INPATIENT

    @property
    def is_outpatient(self):
        """Check if patient is currently an outpatient"""
        return self.status == self.OUTPATIENT

    def get_record_number(self, hospital=None):
        """Get patient's record number at specified hospital or current hospital"""
        if hospital is None and self.ward and self.ward.hospital:
            hospital = self.ward.hospital

        if hospital:
            record = self.hospital_records.filter(hospital=hospital).first()
            if record:
                return record.record_number
        return None

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

        hospital = self.hospital

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
        if ward.hospital != self.current_hospital:
            # Update current_hospital to match ward's hospital
            self.current_hospital = ward.hospital

        self.ward = ward
        if bed:
            self.bed = bed

        if user:
            self.updated_by = user

        self.save()
        return True
  ```

### Create a New Model `PatientHospitalRecord`

- this model should extend the `models.Model` model from `django.db.models`
- this model should be added to the `admin.py` file in the `apps/patients` directory
- this model should be added to the `forms.py` file in the `apps/patients` directory
- this model should be added to the `views.py` file in the `apps/patients` directory
- this model should have the following fields:

  ```python
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
    total_admissions = models.PositiveIntegerField(
        default=0, verbose_name="Total de Admissões"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patient_hospital_records_created",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patient_hospital_records_updated",
    )

    class Meta:
        unique_together = ["patient", "hospital"]
        verbose_name = "Hospital Record"
        verbose_name_plural = "Hospital Records"
        indexes = [
            models.Index(fields=["patient", "hospital"]),
            models.Index(fields=["hospital", "record_number"]),
        ]
  ```

- this model should have the following methods:

  ```python
    def __str__(self):
        return f"{self.patient.name} - {self.hospital.name} ({self.record_number})"
  ```
