"""Tests for PWA branding resolution (PWA_CONFIG vs legacy hospital fallback)."""

import json

from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.core.services import pwa_branding
from apps.core.services.pwa_branding import (
    DEFAULT_PWA_NAME,
    DEFAULT_PWA_SHORT_NAME,
    resolve_pwa_name,
    resolve_pwa_names,
    resolve_pwa_short_name,
)
from apps.core.views import manifest_json


@override_settings(
    HOSPITAL_CONFIG={"name": "Hospital Teste", "short_identifier": "ihgrs"},
    PWA_CONFIG={"short_name": "", "name": ""},
)
class LegacyFallbackTests(SimpleTestCase):
    def test_short_name_uses_hospital_fallback(self) -> None:
        self.assertEqual(resolve_pwa_short_name(), "IhgrsEqmd")

    def test_name_uses_hospital_name(self) -> None:
        self.assertEqual(resolve_pwa_name(), "EquipeMed - Hospital Teste")


@override_settings(
    HOSPITAL_CONFIG={"name": "Hospital Teste", "short_identifier": "ihgrs"},
    PWA_CONFIG={"short_name": "EquipeMed", "name": ""},
)
class PwaShortNameOverrideTests(SimpleTestCase):
    def test_short_name_override_wins_over_hospital(self) -> None:
        self.assertEqual(resolve_pwa_short_name(), "EquipeMed")

    def test_names_dict_keeps_legacy_full_name(self) -> None:
        names = resolve_pwa_names()
        self.assertEqual(names["short_name"], "EquipeMed")
        self.assertEqual(names["name"], "EquipeMed - Hospital Teste")

    def test_manifest_view_uses_override(self) -> None:
        response = manifest_json(RequestFactory().get("/manifest.json"))
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["short_name"], "EquipeMed")


@override_settings(
    HOSPITAL_CONFIG={"name": "Hospital Teste", "short_identifier": "ihgrs"},
    PWA_CONFIG={"short_name": "EquipeMed", "name": "EquipeMed"},
)
class PwaFullOverrideTests(SimpleTestCase):
    def test_both_names_overridden(self) -> None:
        names = resolve_pwa_names()
        self.assertEqual(names, {"name": "EquipeMed", "short_name": "EquipeMed"})


@override_settings(
    HOSPITAL_CONFIG={"name": "Medical Center", "short_identifier": ""},
    PWA_CONFIG={"short_name": "", "name": ""},
)
class DefaultBrandingTests(SimpleTestCase):
    def test_defaults_without_any_config(self) -> None:
        self.assertEqual(resolve_pwa_short_name(), DEFAULT_PWA_SHORT_NAME)
        self.assertEqual(resolve_pwa_name(), DEFAULT_PWA_NAME)

    def test_blank_override_falls_back_to_default(self) -> None:
        self.assertEqual(
            pwa_branding.resolve_pwa_short_name(
                {"short_identifier": ""}, {"short_name": "   "}
            ),
            DEFAULT_PWA_SHORT_NAME,
        )
