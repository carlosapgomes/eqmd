"""Canary: the sample-specialty seed must stay out of test databases.

Migration `accounts.0005_populate_sample_specialties` seeds 30 bootstrap
specialties into every newly migrated database. Test databases are migrated
too, so unless the seed is gated off, tests that create a specialty with a
bootstrap name/abbreviation collide with the seeded row.
"""

from __future__ import annotations

from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.test import TestCase, override_settings

from apps.accounts.models import MedicalSpecialty

create_sample_specialties = import_module(
    "apps.accounts.migrations.0005_populate_sample_specialties"
).create_sample_specialties

# The exact abbreviation list seeded by migration 0005, in migration order.
BOOTSTRAP_ABBREVIATIONS = (
    "CG",
    "CVASC",
    "CIRCARD",
    "TORACICA",
    "CARDIO",
    "PED",
    "ORTO",
    "GO",
    "CM",
    "EM",
    "UTI",
    "UTIPED",
    "ORL",
    "OFTALMO",
    "DERMA",
    "NEURO",
    "PQU",
    "INFECTO",
    "ENDOCRINO",
    "NEFRO",
    "GASTRO",
    "PNEUMO",
    "REUMATO",
    "URO",
    "ANESTESIO",
    "RADIO",
    "ONCO",
    "PLASTICA",
    "CIPE",
    "NEUROCIR",
)


def seeded_abbreviations() -> set[str]:
    """Return the bootstrap abbreviations currently present in the database."""
    return set(
        MedicalSpecialty.objects.filter(
            abbreviation__in=BOOTSTRAP_ABBREVIATIONS
        ).values_list("abbreviation", flat=True)
    )


class SampleSpecialtySeedAbsenceTestCase(TestCase):
    """R2/R3: a test database built with test settings holds no bootstrap rows."""

    def test_no_bootstrap_specialty_exists_in_test_database(self) -> None:
        for abbreviation in BOOTSTRAP_ABBREVIATIONS:
            with self.subTest(abbreviation=abbreviation):
                self.assertFalse(
                    MedicalSpecialty.objects.filter(abbreviation=abbreviation).exists(),
                    f"Seeded specialty {abbreviation} leaked into the test database",
                )


class SampleSpecialtySeedGuardTestCase(TestCase):
    """R1/D1: `create_sample_specialties` honours EQMD_SEED_SAMPLE_SPECIALTIES."""

    @override_settings(EQMD_SEED_SAMPLE_SPECIALTIES=False)
    def test_disabled_flag_creates_no_rows(self) -> None:
        create_sample_specialties(apps, None)

        self.assertEqual(seeded_abbreviations(), set())

    @override_settings(EQMD_SEED_SAMPLE_SPECIALTIES=True)
    def test_enabled_flag_creates_the_bootstrap_rows(self) -> None:
        create_sample_specialties(apps, None)

        self.assertEqual(seeded_abbreviations(), set(BOOTSTRAP_ABBREVIATIONS))

    def test_absent_flag_falls_back_to_default_seeding(self) -> None:
        with self.settings():
            del settings.EQMD_SEED_SAMPLE_SPECIALTIES

            create_sample_specialties(apps, None)

            self.assertEqual(seeded_abbreviations(), set(BOOTSTRAP_ABBREVIATIONS))
