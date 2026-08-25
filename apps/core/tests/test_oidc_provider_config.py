"""Focused regression tests for the OIDC provider primary-key contract.

The project keeps ``django-oidc-provider`` models on ``AutoField`` through a
project-owned compatibility ``AppConfig`` so that runtime model state matches
the vendor's ``0001_initial`` migration (explicit ``AutoField`` PKs) and the
retained PostgreSQL schema, without generating a migration.

These tests must fail while the models resolve to ``BigAutoField`` (the drift
detected by ``makemigrations --check``) and pass once the compatibility config
is selected in ``INSTALLED_APPS``.
"""

from django.apps import apps
from django.test import TestCase
from oidc_provider.models import Client, ResponseType

# The six vendor models whose implicit PK drifted to BigAutoField.
OIDC_MODELS = ("Client", "Code", "ResponseType", "RSAKey", "Token", "UserConsent")


class OIDCProviderConfigTests(TestCase):
    """The loaded OIDC app config must pin AutoField for its models."""

    def test_oidc_app_config_pins_autofield(self):
        config = apps.get_app_config("oidc_provider")
        self.assertEqual(
            config.default_auto_field,
            "django.db.models.AutoField",
            "oidc_provider AppConfig must pin AutoField (compat contract)",
        )

    def test_six_oidc_models_use_autofield_pk(self):
        for model_name in OIDC_MODELS:
            with self.subTest(model=model_name):
                model = apps.get_model("oidc_provider", model_name)
                self.assertEqual(
                    model._meta.pk.get_internal_type(),
                    "AutoField",
                    f"{model_name}.pk must be AutoField to match vendor migrations",
                )


class OIDCRelationCRUDTests(TestCase):
    """A synthetic client/response-type relation must support full CRUD."""

    def test_client_responsetype_relation_crud(self):
        response_type, _ = ResponseType.objects.get_or_create(
            value="code",
            defaults={"description": "Authorization code flow (slice-001a)"},
        )
        client = Client.objects.create(
            name="slice-001a-synthetic-client",
            client_id="slice-001a-client-id",
            client_secret="slice-001a-secret",
            _redirect_uris="http://localhost/callback/",
        )
        client.response_types.add(response_type)
        self.assertEqual(client.response_types.count(), 1)
        self.assertEqual(client.response_types.first(), response_type)
        client.response_types.remove(response_type)
        self.assertEqual(client.response_types.count(), 0)
