# Update the app "events" in the current project

- this app should be added to the `INSTALLED_APPS` list in the `config/settings.py` file

## New models

- all models in this app should be created in the `models.py` file in the `apps/events` directory

### Create a New Model `Event`

- this model should extend the `models.Model` model from `django.db.models`
- this model should be added to the `admin.py` file in the `apps/events` directory
- this model should be added to the `forms.py` file in the `apps/events` directory
- this model should be added to the `views.py` file in the `apps/events` directory
- this model should have the following fields:

  ```python
    HISTORY_AND_PHYSICAL_EVENT = 0
    DAILY_NOTE_EVENT = 1
    SIMPLE_NOTE_EVENT = 2
    PHOTO_EVENT = 3
    EXAM_RESULT_EVENT = 4
    EXAMS_REQUEST_EVENT = 5
    DISCHARGE_REPORT_EVENT = 6
    OUTPT_PRESCRIPTION_EVENT = 7
    REPORT_EVENT = 8
    PHOTO_SERIES_EVENT = 9

    EVENT_TYPE_CHOICES = (
        (HISTORY_AND_PHYSICAL_EVENT, "Anamnese e Exame Físico"),
        (DAILY_NOTE_EVENT, "Evolução"),
        (SIMPLE_NOTE_EVENT, "Nota/Observação"),
        (PHOTO_EVENT, "Imagem"),
        (EXAM_RESULT_EVENT, "Resultado de Exame"),
        (EXAMS_REQUEST_EVENT, "Requisição de Exame"),
        (DISCHARGE_REPORT_EVENT, "Relatório de Alta"),
        (OUTPT_PRESCRIPTION_EVENT, "Receita"),
        (REPORT_EVENT, "Relatório"),
        (PHOTO_SERIES_EVENT, "Série de Fotos"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.PositiveSmallIntegerField(
        choices=EVENT_TYPE_CHOICES, verbose_name="Tipo de Evento"
    )
    event_datetime = models.DateTimeField(verbose_name="Data e Hora do Evento")
    description = models.CharField(max_length=255, verbose_name="Descrição")
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, verbose_name="Paciente"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="event_set",
        verbose_name="Criado por",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="event_updated",
        verbose_name="Atualizado por",
    )

    objects = InheritanceManager()
  ```

- this model should have the following methods:

  ```python
  def __str__(self):
      return str(self.description)
  ```

- this model should have the following meta class:

  ```python
  class Meta:
      ordering = ["-created_at"]
      verbose_name = "Evento"
      verbose_name_plural = "Eventos"
      permissions = [
          ("edit_own_event_24h", "Can edit own events within 24 hours"),
          ("delete_own_event_24h", "Can delete own events within 24 hours"),
      ]
  ```

  ## Urls, views, forms and templates

This app is a base app from which several specific events will inherit from (as daily notes, history and physical, exam requests, exam results, wound photos, external exam reports, discharge reports, outpatient prescriptions, referring reports, etc.)
Because of that, we will only need to create the urls, views, forms and templates for the listing events from a specific patient and events created or updated by a specific user, with pagination.
All other crud operations will be implemented latter in the specific event apps.
