"""Project-owned compatibility AppConfigs for third-party applications.

``OpenIDConnectProviderCompatConfig`` keeps ``django-oidc-provider`` on
``django.db.models.AutoField`` for implicit primary keys.

Rationale: the vendor's ``0001_initial`` migration declares explicit
``AutoField`` PKs, its models/app config declare no ``default_auto_field``,
and the retained PostgreSQL columns are ``integer``. Django's global
``DEFAULT_AUTO_FIELD`` (``BigAutoField``) therefore makes runtime model state
drift from the vendor migrations, which ``makemigrations --check`` reports as
``AlterField id`` on six models. Pinning ``AutoField`` here aligns runtime
model state with the vendor migrations and the database schema without any
migration, package upgrade, or global setting change.
"""

from oidc_provider.apps import OIDCProviderConfig


class OpenIDConnectProviderCompatConfig(OIDCProviderConfig):
    """Vendor OIDC config with the legacy AutoField PK contract pinned."""

    default_auto_field = "django.db.models.AutoField"
