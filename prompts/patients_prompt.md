# Create a new app called "patients" in the current project

- this new app should be created in the `apps` directory
- this new app should be added to the `INSTALLED_APPS` list in the `config/settings.py` file
- to create this new app, run `uv run python manage.py startapp accounts apps/accounts`

## New models

- all models in this app should be created in the `models.py` file in the `apps/accounts` directory

### Create a New Model `Patient`

- this model should extend the `models.Model` model from `django.db.models`

- this model should have the following extra fields:
    ```python
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

    ```
    - update  `accounts/forms.py` to include the new fields
    - update  `accounts/views.py` to include the new fields
    - update  `accounts/admin.py` to include the new fields

##  Documentation

Write documentation for this app in the `docs` directory in the `apps/accounts` directory
Write documentation for the new models and views in the `docs` directory in the `apps/accounts` directory



Do not use crispy forms in the templates, like:
`{% crispy form form.helper %}`

When creating the forms, follow the /home/carlos/projects/eq/equipemed style
and build a manual form structure like in the templates from the folders:

- /home/carlos/projects/eq/equipemed/apps/simplenotes/templates/patients/
- /home/carlos/projects/eq/equipemed/apps/patients/templates/patients/
- /home/carlos/projects/eq/equipemed/apps/hospitals/templates/hospitals/

Remember to add Bootstrap classes to all fields in the forms.py file, like:

```python
                # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
```
