from django.apps import AppConfig


class SampleContentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sample_content'
    verbose_name = 'Conteúdo de Exemplo'