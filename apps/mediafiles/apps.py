from django.apps import AppConfig


class MediafilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.mediafiles'
    verbose_name = 'Media Files'

    def ready(self):
        """
        Initialize the app when Django starts.
        This method is called when the app is ready.
        Can be used for signal registration if needed in the future.
        """
        pass
