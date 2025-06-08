# Update the app "dailynotes" in the current project

- this app should be added to the `INSTALLED_APPS` list in the `config/settings.py` file

## New models

- all models in this app should be created in the `models.py` file in the `apps/dailynotes` directory

### Create a New Model `DailyNote`

- this model should extend the `apps.events.models.Event`
- this model should be added to the `admin.py` file in the `apps/patients` directory
- this model should be added to the `forms.py` file in the `apps/patients` directory
- this model should be added to the `views.py` file in the `apps/patients` directory
- this model should have the following fields:

  ```python
    content = models.TextField(verbose_name="Conteúdo")
  ```

- this model should have the following methods:

  ```python
    def save(self, *args, **kwargs):
        self.event_type = Event.DAILY_NOTE_EVENT
        self.description = Event.EVENT_TYPE_CHOICES[self.event_type][1]
        return super().save(*args, **kwargs)

    def __str__(self):
        return str(self.description)
  ```
  - this model should have the following META class:

  ```python
    class Meta:
        verbose_name = "Evolução"
        verbose_name_plural = "Evoluções"
  ```

  ## Urls, views, forms and templates

Create all CRUD operations for the DailyNote model.

Create a urls.py file in the `apps/dailynotes` directory.
Add the urls to the main urls.py file in the `config` directory.
Create a `views.py` file in the `apps/dailynotes` directory.
Create a `forms.py` file in the `apps/dailynotes` directory.
Create a `templates/dailynotes` directory in the `apps/dailynotes` directory.  

Update its urls paths to perform all CRUD operations for the DailyNote model.
