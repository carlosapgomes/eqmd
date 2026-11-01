"""Resolve PWA branding names with hospital-independent overrides.

Precedence for ``short_name`` (Android home-screen label):
1. ``PWA_SHORT_NAME`` env (``PWA_CONFIG["short_name"]``) when non-blank.
2. Legacy ``HOSPITAL_SHORT_ID`` fallback (``{ShortId}Eqmd``) when set.
3. ``EquipeMed`` default.

Precedence for ``name`` (full install title):
1. ``PWA_NAME`` env (``PWA_CONFIG["name"]``) when non-blank.
2. ``EquipeMed - {hospital name}`` when a hospital short id is set.
3. ``EquipeMed - Plataforma Médica`` default.
"""

from django.conf import settings

DEFAULT_PWA_SHORT_NAME = "EquipeMed"
DEFAULT_PWA_NAME = "EquipeMed - Plataforma Médica"


def _clean(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def resolve_pwa_short_name(
    hospital_config: dict | None = None,
    pwa_config: dict | None = None,
) -> str:
    """Return the PWA ``short_name`` shown on the Android home screen."""
    if hospital_config is None:
        hospital_config = getattr(settings, "HOSPITAL_CONFIG", {})
    if pwa_config is None:
        pwa_config = getattr(settings, "PWA_CONFIG", {})

    override = _clean(pwa_config.get("short_name", ""))
    if override:
        return override

    short_id = _clean(hospital_config.get("short_identifier", "")).lower()
    if short_id:
        return f"{short_id.capitalize()}Eqmd"

    return DEFAULT_PWA_SHORT_NAME


def resolve_pwa_name(
    hospital_config: dict | None = None,
    pwa_config: dict | None = None,
) -> str:
    """Return the PWA ``name`` used as the full install title."""
    if hospital_config is None:
        hospital_config = getattr(settings, "HOSPITAL_CONFIG", {})
    if pwa_config is None:
        pwa_config = getattr(settings, "PWA_CONFIG", {})

    override = _clean(pwa_config.get("name", ""))
    if override:
        return override

    short_id = _clean(hospital_config.get("short_identifier", "")).lower()
    if short_id:
        hospital_name = _clean(hospital_config.get("name", ""))
        if hospital_name:
            return f"EquipeMed - {hospital_name}"
        return DEFAULT_PWA_NAME

    return DEFAULT_PWA_NAME


def resolve_pwa_names(
    hospital_config: dict | None = None,
    pwa_config: dict | None = None,
) -> dict[str, str]:
    """Return ``{"name": ..., "short_name": ...}`` for the PWA manifest."""
    return {
        "name": resolve_pwa_name(hospital_config, pwa_config),
        "short_name": resolve_pwa_short_name(hospital_config, pwa_config),
    }
