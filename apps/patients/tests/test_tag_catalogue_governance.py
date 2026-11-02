"""S2 catalogue governance: classification, namespaces, principal and authority."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import MedicalSpecialty
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag

User = get_user_model()


def make_specialty(abbreviation: str, name: str | None = None) -> MedicalSpecialty:
    """Create a specialty team with a stable abbreviation."""
    return MedicalSpecialty.objects.create(
        name=name or f"Especialidade {abbreviation}", abbreviation=abbreviation
    )


def make_tag(actor: User, name: str, **kwargs: object) -> AllowedTag:
    """Create a catalogue row without form validation (database path)."""
    return AllowedTag.objects.create(
        name=name, created_by=actor, updated_by=actor, **kwargs
    )


def make_admin(username: str = "catalogue-admin") -> User:
    """Create an authorized Django-admin operator."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="catalogue-pass",
        is_staff=True,
        is_superuser=True,
    )


def admin_tags(**overrides: object) -> dict[str, object]:
    """Build an add/change payload for the catalogue admin form."""
    payload: dict[str, object] = {
        "name": "Reavaliar",
        "description": "Catalogue entry",
        "color": "#123456",
        "is_active": "on",
        "origin": AllowedTag.Origin.CUSTOM,
        "visibility": AllowedTag.Visibility.PUBLIC,
        "specialty": "",
        "_save": "Salvar",
    }
    payload.update(overrides)
    return payload


class CatalogueClassificationTests(TestCase):
    """R1: independent origin/visibility, namespace and identity."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = make_admin()
        cls.specialty = make_specialty("CIRGER", "Cirurgia Geral")

    def test_new_row_defaults_to_public_custom_global_namespace(self) -> None:
        tag = make_tag(self.admin, "Legacy Default")
        self.assertEqual(tag.origin, AllowedTag.Origin.CUSTOM)
        self.assertEqual(tag.visibility, AllowedTag.Visibility.PUBLIC)
        self.assertIsNone(tag.specialty_id)
        self.assertEqual(tag.display_name, "Legacy Default")

    def test_restricted_without_specialty_fails_validation(self) -> None:
        tag = AllowedTag(
            name="Restrita sem equipe",
            visibility=AllowedTag.Visibility.RESTRICTED,
            created_by=self.admin,
            updated_by=self.admin,
        )
        with self.assertRaises(ValidationError):
            tag.full_clean()

    def test_restricted_without_specialty_fails_database_constraint(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_tag(
                self.admin,
                "Restrita sem equipe",
                visibility=AllowedTag.Visibility.RESTRICTED,
            )

    def test_admin_creates_classified_namespaced_tag(self) -> None:
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:patients_allowedtag_add"),
            admin_tags(
                name="Reavaliar",
                origin=AllowedTag.Origin.SYSTEM,
                visibility=AllowedTag.Visibility.RESTRICTED,
                specialty=str(self.specialty.pk),
            ),
        )
        self.assertEqual(response.status_code, 302)
        tag = AllowedTag.all_objects.get(name="Reavaliar")
        self.assertEqual(tag.origin, AllowedTag.Origin.SYSTEM)
        self.assertEqual(tag.visibility, AllowedTag.Visibility.RESTRICTED)
        self.assertEqual(tag.specialty_id, self.specialty.pk)
        self.assertEqual(tag.created_by_id, self.admin.pk)
        self.assertEqual(tag.updated_by_id, self.admin.pk)
        self.assertEqual(tag.display_name, "Reavaliar [CIRGER]")

    def test_admin_rejects_restricted_without_specialty(self) -> None:
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:patients_allowedtag_add"),
            admin_tags(visibility=AllowedTag.Visibility.RESTRICTED),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AllowedTag.all_objects.filter(name="Reavaliar").exists())

    def test_admin_namespaces_and_rejects_conflicting_normalized_row(self) -> None:
        other = make_specialty("CARDIO", "Cardiologia")
        self.client.force_login(self.admin)
        add_url = reverse("admin:patients_allowedtag_add")
        first = self.client.post(
            add_url,
            admin_tags(name="Reavaliar", specialty=str(self.specialty.pk)),
        )
        second = self.client.post(
            add_url, admin_tags(name="reavaliar", specialty=str(other.pk))
        )
        conflict = self.client.post(
            add_url,
            admin_tags(name="  REAVALIAR  ", specialty=str(self.specialty.pk)),
        )
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(conflict.status_code, 200)
        self.assertEqual(
            AllowedTag.all_objects.filter(specialty=self.specialty).count(), 1
        )
        self.assertEqual(AllowedTag.all_objects.filter(specialty=other).count(), 1)

    def test_admin_edit_retains_identity_creator_and_associations(self) -> None:
        patient = self._patient()
        tag = make_tag(
            self.admin,
            "Triagem",
            specialty=self.specialty,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        association = patient.patient_tags.create(
            allowed_tag=tag, created_by=self.admin, updated_by=self.admin
        )
        other = make_specialty("CARDIO", "Cardiologia")
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:patients_allowedtag_change", args=[tag.pk]),
            admin_tags(
                name="Triagem",
                origin=AllowedTag.Origin.SYSTEM,
                visibility=AllowedTag.Visibility.RESTRICTED,
                specialty=str(other.pk),
                created_by=str(self.specialty.pk),
            ),
        )
        self.assertEqual(response.status_code, 302)
        tag.refresh_from_db()
        self.assertEqual(tag.name, "Triagem")
        self.assertEqual(tag.origin, AllowedTag.Origin.SYSTEM)
        self.assertEqual(tag.specialty_id, other.pk)
        self.assertEqual(tag.created_by_id, self.admin.pk)
        self.assertEqual(tag.updated_by_id, self.admin.pk)
        self.assertTrue(tag.tag_instances.filter(pk=association.pk).exists())

    def _patient(self):
        from apps.patients.models import Patient

        return Patient.objects.create(
            name="Paciente Catálogo",
            birthday="1980-01-01",
            created_by=self.admin,
            updated_by=self.admin,
        )


class PrincipalMappingTests(TestCase):
    """R3: one public same-namespace principal tag per specialty."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = make_admin()
        cls.cirger = make_specialty("CIRGER", "Cirurgia Geral")
        cls.cardio = make_specialty("CARDIO", "Cardiologia")

    def _set_principal(self, specialty: MedicalSpecialty, tag: AllowedTag) -> None:
        specialty.principal_tag = tag
        specialty.full_clean()
        specialty.save()

    def test_admin_configures_public_same_namespace_principal(self) -> None:
        tag = make_tag(self.admin, "Reavaliar", specialty=self.cirger)
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:accounts_medicalspecialty_change", args=[self.cirger.pk]),
            {
                "name": self.cirger.name,
                "abbreviation": self.cirger.abbreviation,
                "description": "",
                "is_active": "on",
                "principal_tag": str(tag.pk),
                "_save": "Salvar",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.cirger.refresh_from_db()
        self.assertEqual(self.cirger.principal_tag_id, tag.pk)

    def test_restricted_principal_rejected(self) -> None:
        tag = make_tag(
            self.admin,
            "Reavaliar",
            specialty=self.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        with self.assertRaises(ValidationError):
            self._set_principal(self.cirger, tag)

    def test_other_namespace_principal_rejected(self) -> None:
        tag = make_tag(self.admin, "Reavaliar", specialty=self.cardio)
        with self.assertRaises(ValidationError):
            self._set_principal(self.cirger, tag)

    def test_global_principal_rejected(self) -> None:
        tag = make_tag(self.admin, "Reavaliar")
        with self.assertRaises(ValidationError):
            self._set_principal(self.cirger, tag)

    def test_referenced_principal_cannot_be_made_restricted(self) -> None:
        from apps.patients.services import tag_catalogue

        tag = make_tag(self.admin, "Reavaliar", specialty=self.cirger)
        self._set_principal(self.cirger, tag)
        tag.visibility = AllowedTag.Visibility.RESTRICTED
        with self.assertRaises(ValidationError):
            tag.full_clean()
        with self.assertRaises(ValidationError):
            tag_catalogue.update_tag(
                actor=self.admin,
                tag=tag,
                visibility=AllowedTag.Visibility.RESTRICTED,
            )
        tag.refresh_from_db()
        self.assertEqual(tag.visibility, AllowedTag.Visibility.PUBLIC)

    def test_referenced_principal_cannot_change_namespace(self) -> None:
        from apps.patients.services import tag_catalogue

        tag = make_tag(self.admin, "Reavaliar", specialty=self.cirger)
        self._set_principal(self.cirger, tag)
        with self.assertRaises(ValidationError):
            tag_catalogue.update_tag(actor=self.admin, tag=tag, specialty=self.cardio)
        tag.refresh_from_db()
        self.assertEqual(tag.specialty_id, self.cirger.pk)

    def test_no_tag_or_mapping_is_inferred(self) -> None:
        count_before = AllowedTag.all_objects.count()
        self.assertIsNone(self.cirger.principal_tag_id)
        self.assertIsNone(self.cardio.principal_tag_id)
        self.assertEqual(AllowedTag.all_objects.count(), count_before)


class CatalogueAuthorityTests(TestCase):
    """R4: administrator authority, immutable creator, forged-field denial."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = make_admin()
        cls.staff = create_navigation_user(
            username="plain-staff",
            email="plain@example.com",
            password="plain-pass",
            is_staff=True,
        )
        cls.clinician = create_navigation_user(
            username="clinician",
            email="clinician@example.com",
            password="clinician-pass",
            profession_type=0,
        )
        cls.specialty = make_specialty("CIRGER", "Cirurgia Geral")

    def test_ordinary_staff_cannot_mutate_known_urls(self) -> None:
        tag = make_tag(self.admin, "Protegida")
        self.client.force_login(self.staff)
        add = self.client.get(reverse("patients:tag_create"))
        change = self.client.get(reverse("patients:tag_update", kwargs={"pk": tag.pk}))
        forged = self.client.post(
            reverse("patients:tag_create"),
            {"name": "Forjada", "description": "", "color": "#000000"},
        )
        self.assertEqual(add.status_code, 403)
        self.assertEqual(change.status_code, 403)
        self.assertEqual(forged.status_code, 403)
        self.assertFalse(AllowedTag.all_objects.filter(name="Forjada").exists())

    def test_clinical_user_with_permission_is_not_administrator(self) -> None:
        from django.contrib.auth.models import Permission

        permission = Permission.objects.get(
            codename="add_allowedtag",
            content_type__app_label="patients",
        )
        self.clinician.user_permissions.add(permission)
        self.client.force_login(self.clinician)
        response = self.client.get(reverse("patients:tag_create"))
        self.assertEqual(response.status_code, 403)

    def test_delegated_staff_with_catalogue_permission_is_allowed(self) -> None:
        from django.contrib.auth.models import Permission

        permission = Permission.objects.get(
            codename="add_allowedtag",
            content_type__app_label="patients",
        )
        self.staff.user_permissions.add(permission)
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("patients:tag_create"),
            {
                "name": "Delegada",
                "description": "delegated",
                "color": "#00aa00",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        tag = AllowedTag.all_objects.get(name="Delegada")
        self.assertEqual(tag.created_by_id, self.staff.pk)

    def test_leader_without_permissions_cannot_mutate(self) -> None:
        from apps.accounts.models import UserSpecialty

        UserSpecialty.objects.create(
            user=self.staff,
            specialty=self.specialty,
            is_active=True,
            is_leader=True,
        )
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("patients:tag_create"),
            {"name": "Lider", "description": "", "color": "#000000"},
        )
        self.assertEqual(response.status_code, 403)

    def test_forged_fields_cannot_escalate_or_reassign_creator(self) -> None:
        from django.contrib.auth.models import Permission

        permission = Permission.objects.get(
            codename="add_allowedtag",
            content_type__app_label="patients",
        )
        self.staff.user_permissions.add(permission)
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("patients:tag_create"),
            {
                "name": "Forja",
                "description": "",
                "color": "#000000",
                "created_by": str(self.admin.pk),
                "updated_by": str(self.admin.pk),
                "origin": AllowedTag.Origin.SYSTEM,
                "visibility": AllowedTag.Visibility.RESTRICTED,
                "specialty": str(self.specialty.pk),
            },
        )
        self.assertEqual(response.status_code, 302)
        tag = AllowedTag.all_objects.get(name="Forja")
        self.assertEqual(tag.created_by_id, self.staff.pk)
        self.assertEqual(tag.updated_by_id, self.staff.pk)
        self.assertEqual(tag.origin, AllowedTag.Origin.CUSTOM)
        self.assertEqual(tag.visibility, AllowedTag.Visibility.PUBLIC)
        self.assertIsNone(tag.specialty_id)

    def test_anonymous_catalogue_routes_redirect_to_login(self) -> None:
        client = Client()
        response = client.get(reverse("patients:tag_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_service_denies_non_administrator_actor(self) -> None:
        from apps.patients.services import tag_catalogue

        with self.assertRaises(PermissionDenied):
            tag_catalogue.create_tag(actor=self.staff, name="Bloqueada")
        self.assertFalse(AllowedTag.all_objects.filter(name="Bloqueada").exists())
