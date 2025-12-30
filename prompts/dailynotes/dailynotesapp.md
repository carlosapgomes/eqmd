# Update the app "dailynotes" in the current project

- this app should be added to the `INSTALLED_APPS` list in the `config/settings.py` file

## New models

- all models in this app should be created in the `models.py` file in the `apps/dailynotes` directory

### Create a New Model `DailyNote`

- this model should extend the `apps.events.models.Event`
- this model should be added to the `admin.py` file in the `apps/dailynotes` directory
- this model should be added to the `forms.py` file in the `apps/dailynotes` directory
- this model should be added to the `views.py` file in the `apps/dailynotes` directory
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

Its create and update templates should use the easyMD editor for the content field.

The package easymde is already installed in the project. It can be used like this in the template:

```html
<link rel="stylesheet" href="{% static 'css/easymde.min.css' %}" />
```

And can be initialized in the template like this:

```html
<textarea id="id_content" name="content"></textarea>

<script src="{% static 'js/easymde.min.js' %}"></script>
<script>
  let easyMDE;
  document.addEventListener("DOMContentLoaded", function () {
    // Initialize EasyMDE editor
    easyMDE = new EasyMDE({
      element: document.getElementById("id_content"),
      spellChecker: false,
      placeholder: "Conteúdo da evolução...",
      hideIcons: ["link", "image", "side-by-side", "fullscreen"],
      status: false,
    });
  });
</script>
```

## Permissions

This app inherits all permissions from the `events` app.
