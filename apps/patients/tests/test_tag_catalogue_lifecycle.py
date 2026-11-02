"""S3 catalogue lifecycle: canonical states, identity and attribution."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import MedicalSpecialty
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import (
    AllowedTag,
    AllowedTagTransition,
    Patient,
    Tag,
)
from apps.patients.services import tag_catalogue

User = get_user_model()


def make_admin(username: str = "lifecycle-admin") -> User:
    """Create an authorized catalogue administrator."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="lifecycle-pass",
        is_staff=True,
        is_superuser=True,
    )


def make_staff(username: str = "lifecycle-staff") -> User:
    """Create a staff account without catalogue permissions."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="lifecycle-pass",
        is_staff=True,
    )


def make_specialty(abbreviation: str = "CIRGER") -> MedicalSpecialty:
    """Create a specialty team namespace."""
    return MedicalSpecialty.objects.create(
        name=f"Especialidade {abbreviation}", abbreviation=abbreviation
    )


def make_tag(actor: User, name: str, **overrides: Any) -> AllowedTag:
    """Create a catalogue row without form validation (database path)."""
    return AllowedTag.objects.create(
        name=name, created_by=actor, updated_by=actor, **overrides
    )


def make_patient(actor: User) -> Patient:
    """Create a patient owned by the acting administrator."""
    return Patient.objects.create(
        name="Paciente Ciclo de Vida",
        birthday="1980-01-01",
        created_by=actor,
        updated_by=actor,
    )


def admin_payload(**overrides: Any) -> dict[str, Any]:
    """Build a catalogue admin change payload with editable fields only."""
    payload: dict[str, Any] = {
        "name": "Reavaliar",
        "description": "Catalogue entry",
        "color": "#123456",
        "origin": AllowedTag.Origin.CUSTOM,
        "visibility": AllowedTag.Visibility.PUBLIC,
        "specialty": "",
        "_save": "Salvar",
    }
    payload.update(overrides)
    return payload


def post_action(
    client: Client, action: str, tags: list[AllowedTag]
) -> Any:
    """Post a Django admin bulk action for the given catalogue rows."""
    return client.post(
        reverse("admin:patients_allowedtag_changelist"),
        {
            "action": action,
            "_selected_action": [str(tag.pk) for tag in tags],
            "index": "0",
        },
    )


class LifecycleStateModelTests(TestCase):
    """R1: active/inactive/archived on one identity, restore stays inactive."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = make_admin()
        cls.specialty = make_specialty()
        cls.patient = make_patient(cls.admin)

    def _restricted_tag(self, name: str = "Reavaliar") -> AllowedTag:
        return make_tag(
            self.admin,
            name,
            specialty=self.specialty,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )

    def _association(self, tag: AllowedTag) -> Tag:
        return self.patient.patient_tags.create(
            allowed_tag=tag, created_by=self.admin, updated_by=self.admin
        )

    def test_fresh_tag_is_active(self) -> None:
        tag = self._restricted_tag()
        self.assertEqual(tag.lifecycle_state, AllowedTag.LifecycleState.ACTIVE)
        self.assertTrue(tag.is_active)
        self.assertFalse(tag.is_deleted)

    def test_deactivate_then_reactivate_preserve_identity(self) -> None:
        tag = self._restricted_tag()
        association = self._association(tag)
        tag_catalogue.deactivate_tag(actor=self.admin, tag=tag)
        tag.refresh_from_db()
        self.assertEqual(tag.lifecycle_state, AllowedTag.LifecycleState.INACTIVE)
        self.assertEqual(tag.pk, association.allowed_tag_id)
        self.assertEqual(tag.deactivated_by_id, self.admin.pk)
        self.assertIsNotNone(tag.deactivated_at)
        self.assertTrue(tag.tag_instances.filter(pk=association.pk).exists())

        tag_catalogue.reactivate_tag(actor=self.admin, tag=tag)
        tag.refresh_from_db()
        self.assertEqual(tag.lifecycle_state, AllowedTag.LifecycleState.ACTIVE)
        self.assertEqual(tag.reactivated_by_id, self.admin.pk)
        self.assertIsNotNone(tag.reactivated_at)
        self.assertTrue(tag.is_active)
        self.assertFalse(tag.is_deleted)

    def test_archive_is_soft_delete_and_forces_inactive(self) -> None:
        tag = self._restricted_tag()
        association = self._association(tag)
        tag_catalogue.archive_tag(actor=self.admin, tag=tag, reason="")

        archived = AllowedTag.all_objects.get(pk=tag.pk)
        self.assertEqual(
            archived.lifecycle_state, AllowedTag.LifecycleState.ARCHIVED
        )
        self.assertTrue(archived.is_deleted)
        self.assertFalse(archived.is_active)
        self.assertEqual(archived.deleted_by_id, self.admin.pk)
        self.assertIsNotNone(archived.deleted_at)
        self.assertFalse(AllowedTag.objects.filter(pk=tag.pk).exists())
        self.assertTrue(
            AllowedTagTransition.objects.filter(
                tag_id=tag.pk, action=AllowedTagTransition.Action.ARCHIVE
            ).exists()
        )
        self.assertTrue(tag.tag_instances.filter(pk=association.pk).exists())

    def test_restore_returns_same_row_inactive_never_reactivates(self) -> None:
        tag = self._restricted_tag()
        association = self._association(tag)
        tag_catalogue.deactivate_tag(actor=self.admin, tag=tag)
        tag_catalogue.archive_tag(actor=self.admin, tag=tag)
        rows_before = AllowedTag.all_objects.count()

        tag_catalogue.restore_tag(actor=self.admin, tag=tag)
        restored = AllowedTag.all_objects.get(pk=tag.pk)

        self.assertEqual(AllowedTag.all_objects.count(), rows_before)
        self.assertEqual(restored.pk, tag.pk)
        self.assertEqual(restored.name, "Reavaliar")
        self.assertEqual(restored.lifecycle_state, AllowedTag.LifecycleState.INACTIVE)
        self.assertFalse(restored.is_deleted)
        self.assertFalse(restored.is_active)
        self.assertIsNone(restored.deleted_at)
        self.assertIsNone(restored.deleted_by_id)
        self.assertEqual(restored.restored_by_id, self.admin.pk)
        self.assertIsNotNone(restored.restored_at)
        self.assertTrue(restored.tag_instances.filter(pk=association.pk).exists())
        self.assertEqual(AllowedTag.objects.filter(pk=tag.pk).count(), 1)

    def test_associations_and_principal_mapping_survive_every_state(self) -> None:
        tag = make_tag(self.admin, "Principal", specialty=self.specialty)
        self.specialty.principal_tag = tag
        self.specialty.save(update_fields=["principal_tag"])
        association = self._association(tag)

        tag_catalogue.deactivate_tag(actor=self.admin, tag=tag)
        self._assert_preserved(tag, association)
        tag_catalogue.reactivate_tag(actor=self.admin, tag=tag)
        self._assert_preserved(tag, association)
        tag_catalogue.archive_tag(actor=self.admin, tag=tag)
        self._assert_preserved(tag, association)
        tag_catalogue.restore_tag(actor=self.admin, tag=tag)
        self._assert_preserved(tag, association)

    def _assert_preserved(self, tag: AllowedTag, association: Tag) -> None:
        self.specialty.refresh_from_db()
        tag.refresh_from_db()
        self.assertEqual(self.specialty.principal_tag_id, tag.pk)
        self.assertEqual(tag.tag_instances.filter(pk=association.pk).count(), 1)
        self.assertEqual(tag.name, "Principal")

    def test_names_reserved_in_inactive_and_archived_states(self) -> None:
        tag = make_tag(self.admin, "Reavaliar", specialty=self.specialty)
        tag_catalogue.deactivate_tag(actor=self.admin, tag=tag)
        self._assert_duplicate_rejected("  REAVALIAR  ")

        tag_catalogue.archive_tag(actor=self.admin, tag=tag)
        self._assert_duplicate_rejected("reavaliar")

    def _assert_duplicate_rejected(self, name: str) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_tag(self.admin, name, specialty=self.specialty)

    def test_database_rejects_archived_but_active_row(self) -> None:
        tag = make_tag(self.admin, "Inconsistente", specialty=self.specialty)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AllowedTag.all_objects.filter(pk=tag.pk).update(
                is_deleted=True, is_active=True
            )

    def test_direct_model_restore_forces_inactive(self) -> None:
        tag = make_tag(self.admin, "Direta", specialty=self.specialty)
        tag.delete(deleted_by=self.admin, reason="legacy")
        tag.restore(restored_by=self.admin)
        tag.refresh_from_db()
        self.assertFalse(tag.is_deleted)
        self.assertFalse(tag.is_active)

    def test_lifecycle_state_property_matrix(self) -> None:
        tag = make_tag(self.admin, "Matriz", specialty=self.specialty)
        self.assertEqual(tag.lifecycle_state, AllowedTag.LifecycleState.ACTIVE)
        tag.is_active = False
        self.assertEqual(tag.lifecycle_state, AllowedTag.LifecycleState.INACTIVE)
        tag.is_deleted = True
        self.assertEqual(tag.lifecycle_state, AllowedTag.LifecycleState.ARCHIVED)


class LifecycleAuthorityTests(TestCase):
    """R4: staff status alone cannot archive, restore or transfer."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = make_admin()
        cls.staff = make_staff()
        cls.view_staff = make_staff("lifecycle-viewer")
        cls.view_staff.user_permissions.add(
            Permission.objects.get(
                codename="view_allowedtag", content_type__app_label="patients"
            )
        )
        cls.specialty = make_specialty()

    def _tag(self, name: str = "Protegida") -> AllowedTag:
        return make_tag(self.admin, name, specialty=self.specialty)

    def test_staff_cannot_archive_or_restore_via_service(self) -> None:
        tag = self._tag()
        with self.assertRaises(PermissionDenied):
            tag_catalogue.archive_tag(actor=self.staff, tag=tag)
        tag.refresh_from_db()
        self.assertTrue(tag.is_active)
        self.assertFalse(tag.is_deleted)
        self.assertFalse(AllowedTagTransition.objects.exists())

        archived = self._tag("Arquivada")
        tag_catalogue.archive_tag(actor=self.admin, tag=archived)
        with self.assertRaises(PermissionDenied):
            tag_catalogue.restore_tag(actor=self.staff, tag=archived)
        archived.refresh_from_db()
        self.assertTrue(archived.is_deleted)

    def test_staff_status_alone_denied_in_admin(self) -> None:
        tag = self._tag()
        client = Client()
        client.force_login(self.staff)
        self.assertEqual(
            client.get(reverse("admin:patients_allowedtag_changelist")).status_code,
            403,
        )
        response = post_action(client, "archive_selected", [tag])
        self.assertEqual(response.status_code, 403)
        tag.refresh_from_db()
        self.assertFalse(tag.is_deleted)

    def test_view_only_staff_bulk_action_is_a_noop(self) -> None:
        tag = self._tag()
        client = Client()
        client.force_login(self.view_staff)
        self.assertEqual(
            client.get(reverse("admin:patients_allowedtag_changelist")).status_code,
            200,
        )
        response = post_action(client, "archive_selected", [tag])
        self.assertIn(response.status_code, (200, 302))
        tag.refresh_from_db()
        self.assertFalse(tag.is_deleted)
        self.assertTrue(tag.is_active)
        self.assertFalse(AllowedTagTransition.objects.exists())

    def test_staff_denied_on_restore_url(self) -> None:
        tag = self._tag()
        tag_catalogue.archive_tag(actor=self.admin, tag=tag)
        client = Client()
        client.force_login(self.staff)
        response = client.get(
            reverse("admin:patients_allowedtag_restore", args=[tag.pk])
        )
        self.assertEqual(response.status_code, 403)
        tag.refresh_from_db()
        self.assertTrue(tag.is_deleted)

    def test_change_permission_without_delete_cannot_archive(self) -> None:
        delegated = make_staff("lifecycle-delegated")
        delegated.user_permissions.add(
            Permission.objects.get(
                codename="change_allowedtag", content_type__app_label="patients"
            )
        )
        tag = self._tag()
        with self.assertRaises(PermissionDenied):
            tag_catalogue.archive_tag(actor=delegated, tag=tag)
        tag_catalogue.deactivate_tag(actor=delegated, tag=tag)
        tag.refresh_from_db()
        self.assertFalse(tag.is_active)
        self.assertEqual(tag.deactivated_by_id, delegated.pk)


class LifecycleAdminRouteTests(TestCase):
    """R1/R2: admin bulk routes use services and record actors."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = make_admin()
        cls.specialty = make_specialty()

    def setUp(self) -> None:
        self.client = Client()
        self.client.force_login(self.admin)

    def _tag(self, name: str = "Reavaliar") -> AllowedTag:
        return make_tag(self.admin, name, specialty=self.specialty)

    def test_admin_archive_and_restore_actions(self) -> None:
        tag = self._tag()
        self.assertEqual(post_action(self.client, "archive_selected", [tag]).status_code, 302)
        tag.refresh_from_db()
        self.assertTrue(tag.is_deleted)
        self.assertFalse(tag.is_active)
        archive = AllowedTagTransition.objects.get(
            tag_id=tag.pk, action=AllowedTagTransition.Action.ARCHIVE
        )
        self.assertEqual(archive.performed_by_id, self.admin.pk)

        self.assertEqual(post_action(self.client, "restore_selected", [tag]).status_code, 302)
        tag.refresh_from_db()
        self.assertFalse(tag.is_deleted)
        self.assertFalse(tag.is_active)
        restore = AllowedTagTransition.objects.get(
            tag_id=tag.pk, action=AllowedTagTransition.Action.RESTORE
        )
        self.assertEqual(restore.performed_by_id, self.admin.pk)
        self.assertEqual(restore.to_state, AllowedTag.LifecycleState.INACTIVE)

    def test_admin_archive_restore_activate_sequence_same_identity(self) -> None:
        tag = self._tag()
        tag_pk = tag.pk

        post_action(self.client, "archive_selected", [tag])
        tag.refresh_from_db()
        self.assertTrue(tag.is_deleted)
        self.assertFalse(tag.is_active)

        post_action(self.client, "restore_selected", [tag])
        tag.refresh_from_db()
        self.assertEqual(tag.pk, tag_pk)
        self.assertFalse(tag.is_deleted)
        self.assertFalse(tag.is_active)

        post_action(self.client, "reactivate_selected", [tag])
        tag.refresh_from_db()
        self.assertEqual(tag.pk, tag_pk)
        self.assertTrue(tag.is_active)
        self.assertFalse(tag.is_deleted)
        self.assertEqual(
            list(
                tag.transitions.order_by("performed_at", "pk").values_list(
                    "action", flat=True
                )
            ),
            [
                AllowedTagTransition.Action.ARCHIVE,
                AllowedTagTransition.Action.RESTORE,
                AllowedTagTransition.Action.ACTIVATE,
            ],
        )

    def test_admin_deactivate_and_reactivate_actions(self) -> None:
        tag = self._tag()
        post_action(self.client, "deactivate_selected", [tag])
        tag.refresh_from_db()
        self.assertFalse(tag.is_active)
        self.assertEqual(tag.deactivated_by_id, self.admin.pk)

        post_action(self.client, "reactivate_selected", [tag])
        tag.refresh_from_db()
        self.assertTrue(tag.is_active)
        self.assertEqual(tag.reactivated_by_id, self.admin.pk)

    def test_admin_bulk_action_rolls_back_on_invalid_row(self) -> None:
        active = self._tag("Valida")
        already = self._tag("Ja arquivada")
        tag_catalogue.archive_tag(actor=self.admin, tag=already)
        transitions_before = AllowedTagTransition.objects.count()

        response = post_action(self.client, "archive_selected", [active, already])
        self.assertEqual(response.status_code, 302)
        active.refresh_from_db()
        self.assertFalse(active.is_deleted)
        self.assertTrue(active.is_active)
        self.assertEqual(AllowedTagTransition.objects.count(), transitions_before)

    def test_admin_change_form_ignores_lifecycle_fields(self) -> None:
        tag = self._tag()
        response = self.client.post(
            reverse("admin:patients_allowedtag_change", args=[tag.pk]),
            admin_payload(
                name=tag.name,
                is_active="",
                is_deleted="on",
                deleted_at="2020-01-01 00:00:00",
            ),
        )
        self.assertEqual(response.status_code, 302)
        tag.refresh_from_db()
        self.assertTrue(tag.is_active)
        self.assertFalse(tag.is_deleted)
        self.assertFalse(AllowedTagTransition.objects.exists())

    def test_admin_changelist_labels_archive_and_restore(self) -> None:
        self._tag()
        response = self.client.get(reverse("admin:patients_allowedtag_changelist"))
        self.assertContains(response, "Arquivar tags selecionadas")
        self.assertContains(response, "Restaurar tags selecionadas")
        self.assertNotContains(response, "Excluir selecionados")


class TransitionHistoryTests(TestCase):
    """R2: full ordered immutable history plus latest-action fields."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.first = make_admin("history-first")
        cls.second = make_admin("history-second")
        cls.specialty = make_specialty()

    def test_multiple_actors_retain_every_transition_in_order(self) -> None:
        tag = make_tag(self.first, "Ciclos", specialty=self.specialty)
        tag_catalogue.deactivate_tag(actor=self.first, tag=tag)
        tag_catalogue.reactivate_tag(actor=self.second, tag=tag)
        tag_catalogue.archive_tag(actor=self.first, tag=tag)
        tag_catalogue.restore_tag(actor=self.second, tag=tag)

        transitions = list(tag.transitions.order_by("performed_at", "pk"))
        self.assertEqual(
            [row.action for row in transitions],
            [
                AllowedTagTransition.Action.DEACTIVATE,
                AllowedTagTransition.Action.ACTIVATE,
                AllowedTagTransition.Action.ARCHIVE,
                AllowedTagTransition.Action.RESTORE,
            ],
        )
        self.assertEqual(
            [row.performed_by_id for row in transitions],
            [self.first.pk, self.second.pk, self.first.pk, self.second.pk],
        )
        for row in transitions:
            self.assertIsNotNone(row.performed_at)
            self.assertEqual(row.reason, "")

        tag.refresh_from_db()
        self.assertEqual(tag.deactivated_by_id, self.first.pk)
        self.assertEqual(tag.reactivated_by_id, self.second.pk)
        self.assertEqual(tag.archived_by_id, self.first.pk)
        self.assertIsNotNone(tag.archived_at)
        self.assertEqual(tag.restored_by_id, self.second.pk)
        self.assertFalse(tag.is_active)

    def test_failed_transition_has_no_partial_state_or_history(self) -> None:
        tag = make_tag(self.first, "Falha", specialty=self.specialty)
        tag_catalogue.archive_tag(actor=self.first, tag=tag)
        transitions_before = AllowedTagTransition.objects.count()

        with self.assertRaises(ValidationError):
            tag_catalogue.deactivate_tag(actor=self.first, tag=tag)

        tag.refresh_from_db()
        self.assertTrue(tag.is_deleted)
        self.assertEqual(AllowedTagTransition.objects.count(), transitions_before)

    def test_transition_history_is_immutable(self) -> None:
        tag = make_tag(self.first, "Imutavel", specialty=self.specialty)
        tag_catalogue.deactivate_tag(actor=self.first, tag=tag)
        transition = tag.transitions.get()

        transition.reason = "tampered"
        with self.assertRaises(ValidationError):
            transition.save()
        with self.assertRaises(ValidationError):
            transition.delete()

        transition.refresh_from_db()
        self.assertEqual(transition.reason, "")

    def test_simple_history_attributes_each_transition_actor(self) -> None:
        tag = make_tag(self.first, "Historico", specialty=self.specialty)
        tag_catalogue.deactivate_tag(actor=self.first, tag=tag)
        tag_catalogue.reactivate_tag(actor=self.second, tag=tag)

        history = list(tag.history.order_by("history_date", "history_id"))
        self.assertGreaterEqual(len(history), 3)
        self.assertEqual(history[-1].history_user_id, self.second.pk)
        self.assertIn(
            self.first.pk,
            {row.history_user_id for row in history},
        )
