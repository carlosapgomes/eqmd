"""Compact tag selector: the server-rendered accessibility contract.

The search enhancement in `assets/js/tag-selector.js` can only announce and
navigate when the template exposes the matching hooks, so these assertions pin
the attributes the script depends on: the search field references the results
list, the list keeps its accessible name, the status region announces
atomically and "Carregar mais" stays outside the list. The native multi-select
fallback is asserted unchanged.
"""

from __future__ import annotations

import re
from typing import Any

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import MedicalSpecialty, UserSpecialty
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag, Patient, Tag

RESULTS_LIST = re.compile(r"<ul[^>]*data-tag-results[^>]*></ul>")
SEARCH_FIELD = re.compile(r"<input[^>]*id=\"tag-search\"[^>]*>")
STATUS_REGION = re.compile(r"<p[^>]*data-tag-status[^>]*>")
NATIVE_SELECT = re.compile(r"<select[^>]*data-tag-native[^>]*>")


def make_user(username: str) -> Any:
    """Create an active account allowed to read the patient list."""
    user = create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="tag-selector-template-pass",
    )
    user.user_permissions.add(Permission.objects.get(codename="view_patient"))
    return user


class TagSelectorTemplateTests(TestCase):
    """The patient list renders the selector hooks the script relies on."""

    owner: Any
    specialty: MedicalSpecialty
    team_tag: AllowedTag

    @classmethod
    def setUpTestData(cls) -> None:
        cls.owner = make_user("tag-selector-owner")
        cls.specialty = MedicalSpecialty.objects.create(
            name="Equipe CIRGER", abbreviation="CIRGER"
        )
        UserSpecialty.objects.create(
            user=cls.owner, specialty=cls.specialty, is_active=True
        )
        cls.team_tag = AllowedTag.objects.create(
            name="Cir Vascular",
            specialty=cls.specialty,
            visibility=AllowedTag.Visibility.RESTRICTED,
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        # Only catalogue entries already used by a patient stay in the legacy
        # option list (tag_projection.filter_tag_options).
        patient = Patient.objects.create(
            name="Paciente Fixture",
            birthday="1980-01-01",
            created_by=cls.owner,
            updated_by=cls.owner,
        )
        Tag.objects.create(
            allowed_tag=cls.team_tag,
            patient=patient,
            created_by=cls.owner,
            updated_by=cls.owner,
        )

    def setUp(self) -> None:
        self.client.force_login(self.owner)

    def component_markup(self) -> str:
        response = self.client.get(reverse("patients:patient_list"))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def matches(self, pattern: re.Pattern[str]) -> list[str]:
        found = pattern.findall(self.component_markup())
        self.assertEqual(len(found), 1, "the selector must render exactly once")
        return found

    def test_search_field_references_the_results_list(self) -> None:
        search = self.matches(SEARCH_FIELD)[0]

        self.assertIn('aria-controls="tag-search-results"', search)

    def test_results_list_keeps_its_accessible_name(self) -> None:
        results = self.matches(RESULTS_LIST)[0]

        self.assertIn('id="tag-search-results"', results)
        self.assertIn('role="list"', results)
        self.assertIn('aria-label="Resultados de tags"', results)

    def test_status_region_announces_atomically_and_politely(self) -> None:
        status = self.matches(STATUS_REGION)[0]

        self.assertIn('aria-live="polite"', status)
        self.assertIn('aria-atomic="true"', status)

    def test_pagination_stays_outside_the_results_list(self) -> None:
        markup = self.component_markup()

        list_end = markup.index("</ul>", markup.index("data-tag-results"))
        self.assertGreater(markup.index("data-tag-more"), list_end)
        self.assertLess(markup.index("Carregar mais"), markup.index("data-tag-status"))

    def test_native_multiselect_fallback_is_unchanged(self) -> None:
        select = self.matches(NATIVE_SELECT)[0]
        markup = self.component_markup()

        self.assertIn('name="tags"', select)
        self.assertIn("multiple", select)
        self.assertEqual(markup.count('name="tags"'), 1)
        self.assertIn(f'<option value="{self.team_tag.pk}"', markup)
        self.assertIn("Cir Vascular [CIRGER]", markup)
        self.assertIn('name="tag_filter"', markup)
        self.assertIn('name="tag_mode"', markup)
