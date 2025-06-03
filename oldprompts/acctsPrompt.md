# Create a new app called "accounts" in the current project

- this new app should be created in the `apps` directory
- this new app should be added to the `INSTALLED_APPS` list in the `config/settings.py` file
- to create this new app, run `uv run django-admin startapp accounts apps/accounts`

## New models

- all models in this app should be created in the `models.py` file in the `apps/accounts` directory

### Create a New Model `EqmdCustomUser`

- this model should extend the `AbstractUser` model from `django.contrib.auth.models`
- this model should be added to the `admin.py` file in the `apps/accounts` directory
- this model should be added to the `forms.py` file in the `apps/accounts` directory
- this model should be added to the `views.py` file in the `apps/accounts` directory
- update the `AUTH_USER_MODEL` setting in the `config/settings.py` file to `accounts.EqmdCustomUser`
- this model should have the following extra fields:
    ```python
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
    ```
    - update  `accounts/forms.py` to include the new fields
    - update  `accounts/views.py` to include the new fields
    - update  `accounts/admin.py` to include the new fields

### Create a One-to-One Profile Model:

    Define a `UserProfile` model with a `OneToOneField` linking to the `EqmdCustomUser` model.
    Include a unique, non-sensitive identifier (e.g., UUID) to use instead of the user ID, along with other fields you want to expose.
    In this model, expose the following `EqmdCustomUser` fields as `read-only-fields`:
        - `is_active`
        - `is_staff`
        - `is_superuser`
        - `email`
        - `first_name`
        - `last_name`


#### Example snippet to add to `accounts/models.py`:
```python
import uuid
from django.db import models
from django.contrib.auth import get_user_model

class UserProfile(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name='profile')
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"{self.display_name}'s profile"
```
#### Use Signals to Auto-Create Profiles:

    - Automatically create a UserProfile when a CustomUser is created to ensure every user has a profile.
    Example:
```python
# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile

@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=get_user_model())
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
```

- Connect signals in apps.py:

```python
# accounts/apps.py
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.signals
```
- Update settings.py:
```python
# config/settings.py

    INSTALLED_APPS = [
        ...
        'accounts.apps.AccountsConfig',
    ]
```

#### Update URLs to Use public_id:

    . Modify URL patterns to use the public_id from the UserProfile instead of the user ID.
```python
    # accounts/urls.py
    from django.urls import path
    from . import views

    app_name = 'accounts'

    urlpatterns = [
        path('profile/<uuid:public_id>/', views.profile_view, name='profile'),
    ]
```

#### Expose Only Safe Fields in Views and Serializers:

    In views (e.g., Django class-based views or Django REST Framework), query the UserProfile model instead of the CustomUser to expose only the intended fields.

    Example (Django REST Framework):
```python
# accounts/serializers.py
from rest_framework import serializers
from .models import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['public_id', 'display_name', 'bio']
```
```python
# accounts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import UserProfile
from .serializers import UserProfileSerializer

class ProfileView(APIView):
    def get(self, request, public_id):
        profile = UserProfile.objects.get(public_id=public_id)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
```

#### In templates, use the public_id with the url tag:
```html
    <!-- templates/profile.html -->
    <a href="{% url 'accounts:profile' public_id=user.profile.public_id %}">{{ user.profile.display_name }}</a>
```

#### Use reverse_lazy for Profile URLs:

    . In Python code, use reverse_lazy to resolve profile URLs with the public_id:
```python
from django.urls import reverse_lazy
from django.views.generic import RedirectView

class ProfileRedirectView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        return reverse_lazy('accounts:profile', kwargs={'public_id': self.request.user.profile.public_id})
```
##  Documentation

Write documentation for this app in the `docs` directory in the `apps/accounts` directory
Write documentation for the new models and views in the `docs` directory in the `apps/accounts` directory