# Update the app "hospitals" in the current project

- this app should be added to the `INSTALLED_APPS` list in the `config/settings.py` file

## New models

- all models in this app should be created in the `models.py` file in the `apps/hospitals` directory

### Create a New Model `Hospital`

- this model should extend the `models.Model` model from `django.db.models`
- this model should be added to the `admin.py` file in the `apps/hospitals` directory
- this model should be added to the `forms.py` file in the `apps/hospitals` directory
- this model should be added to the `views.py` file in the `apps/hospitals` directory
- this model should have the following fields:

  ```python
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  name = models.CharField(max_length=255)
  short_name = models.CharField(max_length=50, blank=True, help_text="Abbreviated or short name for the hospital")
  address = models.CharField(max_length=255, blank=True)
  city = models.CharField(max_length=50, blank=True)
  state = models.CharField(max_length=2, blank=True)
  zip_code = models.CharField(max_length=10, blank=True)
  phone = models.CharField(max_length=20, blank=True)
  created_at = models.DateTimeField(auto_now_add=True)
  created_by = models.ForeignKey(
      "apps.accounts.EqmdCustomUser", on_delete=models.PROTECT, related_name="hospital_created"
  )
  updated_at = models.DateTimeField(auto_now=True)
  updated_by = models.ForeignKey(
      "apps.accounts.EqmdCustomUser", on_delete=models.PROTECT, related_name="hospital_updated"
  ```

- this model should have the following methods:

  ```python
  def __str__(self):
      if self.short_name:
          return self.short_name
      return self.name
  ```

  ```python
  def get_absolute_url(self):
      return reverse("hospitals:hospital_detail", kwargs={"pk": self.pk})
  ```

- this model should have the following meta class:

  ```python
  class Meta:
      verbose_name = "Hospital"
      verbose_name_plural = "Hospitals"
      ordering = ["name"]
  ```

### Create a New Model `Ward`

- this model should extend the `models.Model` model from `django.db.models`
- this model should be added to the `admin.py` file in the `apps/hospitals` directory
- this model should be added to the `forms.py` file in the `apps/hospitals` directory
- this model should be added to the `views.py` file in the `apps/hospitals` directory
- this model should have the following fields:

  ```python
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  name = models.CharField(max_length=255)
  description = models.TextField(blank=True, verbose_name="Descrição")
  capacity = models.PositiveIntegerField(default=0, verbose_name="Capacidade de Leitos")
  is_active = models.BooleanField(default=True, verbose_name="Ativo")
  hospital = models.ForeignKey(
      "Hospital", on_delete=models.PROTECT, related_name="wards"
  )
  # Tracking fields
  created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
  created_by = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.PROTECT,
      related_name="ward_created",
      verbose_name="Criado por"
  )
  updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
  updated_by = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.PROTECT,
      related_name="ward_updated",
      verbose_name="Atualizado por"
  )
  ```

- this model should have the following methods:

  ```python
  def __str__(self):
      return self.name
  def get_absolute_url(self):
      return reverse("ward_detail", kwargs={"pk": self.pk})

  @property
  def patient_count(self):
      """
      Returns the number of patients currently in this ward.
      """
      try:
          from apps.patients.models import Patient
          return Patient.objects.filter(ward=self, status=Patient.INPATIENT).count()
      except (ImportError, AttributeError):
          # If Patient model is not available or doesn't have the expected attributes
          return 0

  @property
  def occupancy_rate(self):
      """
      Returns the occupancy rate as a percentage.
      """
      if self.capacity > 0:
          # Use the patient_count property to get the count
          count = self.patient_count
          return (count / self.capacity) * 100
      return 0
  ```

  ```python
  def get_absolute_url(self):
      return reverse("hospitals:ward_detail", kwargs={"pk": self.pk})
  ```

- this model should have the following meta class:

  ```python
  class Meta:
      verbose_name = "Enfermaria"
      verbose_name_plural = "Enfermarias"
      ordering = ["name"]
  ```

### Create a New Model `HospitalUser`

- this model should extend the `models.Model` model from `django.db.models`
- this model should be added to the `admin.py` file in the `apps/hospitals` directory
- this model should be added to the `forms.py` file in the `apps/hospitals` directory
- this model should be added to the `views.py` file in the `apps/hospitals` directory
- this model should have the following fields:

  ```python
    ACTIVE = 1
    INACTIVE = 0
    STATUS_CHOICES = (
        (ACTIVE, "Ativo"),
        (INACTIVE, "Inativo"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    user = models.ForeignKey("apps.accounts.EqmdCustomUser", on_delete=models.CASCADE, related_name="hospital_memberships")
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "apps.accounts.EqmdCustomUser",
        on_delete=models.PROTECT,
        related_name="hospital_user_created",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "apps.accounts.EqmdCustomUser",
        on_delete=models.PROTECT,
        related_name="hospital_user_updated",
    )
  ```

- this model should have the following methods:

  ```python
  def __str__(self):
      return f"{self.user} - {self.hospital}"
  ```

  ```python
  def get_absolute_url(self):
      return reverse("hospitals:hospital_user_detail", kwargs={"pk": self.pk})
  ```

- this model should have the following meta class:

  ```python
  class Meta:
      verbose_name = "Hospital User"
      verbose_name_plural = "Hospital Users"
      ordering = ["user__username"]
  ```
