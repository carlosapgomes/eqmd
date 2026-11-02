"""S4 R2-R4: atomic tag audit writes, stable references and immutability."""

from __future__ import annotations

import threading
from datetime import timedelta
from io import StringIO
from typing import Any

from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import MedicalSpecialty, UserSpecialty
from apps.accounts.tests.helpers import create_navigation_user
from apps.core.permissions.utils import can_delete_event, can_edit_event
from apps.events.models import (
    Event,
    TagAddedEvent,
    TagBulkRemoveEvent,
    TagRemovedEvent,
)
from apps.patients.models import AllowedTag, Patient, Tag
from apps.patients.services import tag_catalogue

CLINICAL_PERMISSIONS = ("change_patient", "view_patient")

EVENTS_BEFORE = "0005_patientprofilechangeevent_alter_event_event_type_and_more"
EVENTS_REFERENCE = "0006_tageventreference"
EVENTS_BACKFILL = "0007_tageventreference_backfill"
PATIENTS_LEAF = "0005_allowedtag_lifecycle_responsibility"
ACCOUNTS_LEAF = "0007_medicalspecialty_principal_tag"
BEFORE = [
    ("events", EVENTS_BEFORE),
    ("patients", PATIENTS_LEAF),
    ("accounts", ACCOUNTS_LEAF),
]
AFTER = [
    ("events", EVENTS_BACKFILL),
    ("patients", PATIENTS_LEAF),
    ("accounts", ACCOUNTS_LEAF),
]


def make_user(
    username: str,
    *,
    permissions: tuple[str, ...] | None = CLINICAL_PERMISSIONS,
    is_staff: bool = False,
    is_superuser: bool = False,
):
    """Create an active account with the requested clinical permissions."""
    user = create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="audit-pass",
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
    if permissions:
        user.user_permissions.add(
            *[Permission.objects.get(codename=codename) for codename in permissions]
        )
    return user


def make_specialty(abbreviation: str) -> MedicalSpecialty:
    """Create one specialty team namespace."""
    return MedicalSpecialty.objects.create(
        name=f"Equipe {abbreviation}", abbreviation=abbreviation
    )


def make_tag(actor: Any, name: str, **overrides: Any) -> AllowedTag:
    """Create a catalogue row without form validation (database path)."""
    return AllowedTag.objects.create(
        name=name, created_by=actor, updated_by=actor, **overrides
    )


def make_patient(actor: Any, name: str = "Paciente Auditoria") -> Patient:
    """Create an outpatient record for tag audits."""
    return Patient.objects.create(
        name=name,
        birthday="1980-05-05",
        status=Patient.Status.OUTPATIENT,
        created_by=actor,
        updated_by=actor,
    )


def tag_references(event: Any):
    """Return the S4 catalogue references recorded for one event."""
    return event.tag_references.all()


class AtomicAssignmentAuditTests(TestCase):
    """R2: association/event pairs are atomic and never duplicated."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = make_specialty("ATMTM")
        cls.actor = make_user("atomic-actor")
        UserSpecialty.objects.create(user=cls.actor, specialty=cls.team, is_active=True)
        cls.tag = make_tag(cls.actor, "Atômica")
        cls.second_tag = make_tag(cls.actor, "Segunda")

    def setUp(self) -> None:
        self.patient = make_patient(self.actor, "Paciente Atômico")
        self.client.force_login(self.actor)

    def _add_url(self) -> str:
        return reverse(
            "patients:patient_tag_add", kwargs={"patient_id": self.patient.pk}
        )

    def test_event_write_failure_leaves_no_changed_association(self) -> None:
        original_create = TagAddedEvent.objects.create

        def failing_create(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("event store unavailable")

        TagAddedEvent.objects.create = failing_create
        try:
            response = self.client.post(self._add_url(), {"tag_id": self.tag.pk})
        finally:
            TagAddedEvent.objects.create = original_create

        self.assertEqual(response.status_code, 500)
        self.assertFalse(
            Tag.objects.filter(
                patient=self.patient, allowed_tag_id=self.tag.pk
            ).exists()
        )
        self.assertFalse(TagAddedEvent.objects.filter(patient=self.patient).exists())
        self.assertFalse(TagAddedEvent.objects.exists())

    def test_bulk_event_write_failure_preserves_all_associations(self) -> None:
        Tag.objects.create(
            allowed_tag=self.tag,
            patient=self.patient,
            created_by=self.actor,
            updated_by=self.actor,
        )
        Tag.objects.create(
            allowed_tag=self.second_tag,
            patient=self.patient,
            created_by=self.actor,
            updated_by=self.actor,
        )
        original_create = TagBulkRemoveEvent.objects.create

        def failing_create(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("event store unavailable")

        TagBulkRemoveEvent.objects.create = failing_create
        try:
            response = self.client.post(
                reverse(
                    "patients:patient_tag_remove_all",
                    kwargs={"patient_id": self.patient.pk},
                )
            )
        finally:
            TagBulkRemoveEvent.objects.create = original_create

        self.assertEqual(response.status_code, 500)
        self.assertEqual(Tag.objects.filter(patient=self.patient).count(), 2)
        self.assertFalse(
            TagBulkRemoveEvent.objects.filter(patient=self.patient).exists()
        )

    def test_denied_assignment_has_no_side_effects(self) -> None:
        principal = make_tag(
            self.actor,
            "Principal",
            specialty=self.team,
            visibility=AllowedTag.Visibility.PUBLIC,
        )
        MedicalSpecialty.objects.filter(pk=self.team.pk).update(
            principal_tag_id=principal.pk
        )
        outsider = make_user("atomic-outsider")

        self.client.force_login(outsider)
        response = self.client.post(self._add_url(), {"tag_id": principal.pk})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            Tag.objects.filter(
                patient=self.patient, allowed_tag_id=principal.pk
            ).exists()
        )
        self.assertFalse(TagAddedEvent.objects.exists())

    def test_add_writes_paired_event_and_stable_reference(self) -> None:
        response = self.client.post(
            self._add_url(), {"tag_id": self.tag.pk, "notes": "audit note"}
        )

        self.assertEqual(response.status_code, 200)
        association = Tag.objects.get(patient=self.patient, allowed_tag_id=self.tag.pk)
        event = TagAddedEvent.objects.get(patient=self.patient)
        self.assertEqual(event.tag_name, association.allowed_tag.name)
        reference = tag_references(event).get()
        self.assertEqual(reference.tag_id, self.tag.pk)
        self.assertEqual(reference.action, "added")
        self.assertEqual(reference.tag_name, self.tag.name)
        self.assertEqual(reference.tag_color, self.tag.color)
        self.assertEqual(reference.tag_notes, "audit note")
        self.assertEqual(reference.tag_visibility, self.tag.visibility)
        self.assertIsNone(reference.specialty_id)
        self.assertEqual(reference.specialty_abbreviation, "")

    def test_bulk_removal_records_one_reference_per_removed_tag(self) -> None:
        for tag in (self.tag, self.second_tag):
            Tag.objects.create(
                allowed_tag=tag,
                patient=self.patient,
                created_by=self.actor,
                updated_by=self.actor,
            )

        response = self.client.post(
            reverse(
                "patients:patient_tag_remove_all",
                kwargs={"patient_id": self.patient.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        event = TagBulkRemoveEvent.objects.get(patient=self.patient)
        self.assertEqual(
            sorted(
                (reference.tag_id, reference.action)
                for reference in tag_references(event)
            ),
            sorted([(self.tag.pk, "removed"), (self.second_tag.pk, "removed")]),
        )
        self.assertEqual(event.tag_count, 2)
        self.assertIn(self.tag.name, event.tag_names)

    def test_duplicate_add_creates_no_second_event(self) -> None:
        self.client.post(self._add_url(), {"tag_id": self.tag.pk})
        response = self.client.post(self._add_url(), {"tag_id": self.tag.pk})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Tag.objects.filter(patient=self.patient).count(), 1)
        self.assertEqual(TagAddedEvent.objects.filter(patient=self.patient).count(), 1)
        self.assertEqual(tag_references(TagAddedEvent.objects.get()).count(), 1)

    def test_correction_appends_opposing_event(self) -> None:
        self.client.post(self._add_url(), {"tag_id": self.tag.pk})
        association = Tag.objects.get(patient=self.patient)

        response = self.client.post(
            reverse(
                "patients:patient_tag_remove",
                kwargs={
                    "patient_id": self.patient.pk,
                    "tag_id": association.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        added = TagAddedEvent.objects.get(patient=self.patient)
        removed = TagRemovedEvent.objects.get(patient=self.patient)
        self.assertTrue(TagAddedEvent.objects.filter(pk=added.pk).exists())
        self.assertEqual(tag_references(added).get().action, "added")
        self.assertEqual(tag_references(removed).get().action, "removed")
        self.assertEqual(tag_references(removed).get().tag_id, self.tag.pk)

    def test_admin_assignment_writes_timeline_event(self) -> None:
        admin = make_user(
            "atomic-admin", permissions=None, is_staff=True, is_superuser=True
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("admin:patients_tag_add"),
            {
                "allowed_tag": str(self.tag.pk),
                "patient": str(self.patient.pk),
                "notes": "admin assignment",
            },
        )

        self.assertEqual(response.status_code, 302)
        association = Tag.objects.get(patient=self.patient, allowed_tag_id=self.tag.pk)
        event = TagAddedEvent.objects.get(patient=self.patient)
        self.assertEqual(event.created_by, admin)
        self.assertEqual(tag_references(event).get().tag_id, self.tag.pk)

        delete_response = self.client.post(
            reverse("admin:patients_tag_delete", args=[association.pk]),
            {"post": "yes"},
        )

        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Tag.objects.filter(pk=association.pk).exists())
        removed = TagRemovedEvent.objects.get(patient=self.patient)
        self.assertEqual(removed.created_by, admin)

    def test_admin_bulk_delete_is_audited_per_association(self) -> None:
        admin = make_user(
            "bulk-admin", permissions=None, is_staff=True, is_superuser=True
        )
        first = Tag.objects.create(
            allowed_tag=self.tag,
            patient=self.patient,
            created_by=self.actor,
            updated_by=self.actor,
        )
        second = Tag.objects.create(
            allowed_tag=self.second_tag,
            patient=self.patient,
            created_by=self.actor,
            updated_by=self.actor,
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("admin:patients_tag_changelist"),
            {
                "action": "delete_selected",
                "_selected_action": [str(first.pk), str(second.pk)],
                "post": "yes",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Tag.objects.filter(patient=self.patient).exists())
        self.assertEqual(
            TagRemovedEvent.objects.filter(patient=self.patient).count(), 2
        )

    def test_admin_change_of_association_is_denied(self) -> None:
        admin = make_user(
            "change-admin", permissions=None, is_staff=True, is_superuser=True
        )
        association = Tag.objects.create(
            allowed_tag=self.tag,
            patient=self.patient,
            created_by=self.actor,
            updated_by=self.actor,
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("admin:patients_tag_change", args=[association.pk]),
            {
                "allowed_tag": str(self.second_tag.pk),
                "patient": str(self.patient.pk),
                "notes": "silent rewrite",
            },
        )

        self.assertEqual(response.status_code, 403)
        association.refresh_from_db()
        self.assertEqual(association.allowed_tag_id, self.tag.pk)
        self.assertEqual(association.notes, "")


class TagReferenceStabilityTests(TestCase):
    """R3: references keep catalogue identity, snapshots and team attribution."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.team = make_specialty("REFTM")
        cls.admin = make_user(
            "ref-admin", permissions=None, is_staff=True, is_superuser=True
        )
        cls.member = make_user("ref-member")
        UserSpecialty.objects.create(
            user=cls.member, specialty=cls.team, is_active=True
        )
        cls.tag = make_tag(
            cls.member,
            "Referência",
            specialty=cls.team,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )

    def setUp(self) -> None:
        self.patient = make_patient(self.member, "Paciente Referência")
        self.client.force_login(self.member)

    def _add(self) -> TagAddedEvent:
        response = self.client.post(
            reverse("patients:patient_tag_add", kwargs={"patient_id": self.patient.pk}),
            {"tag_id": self.tag.pk},
        )
        self.assertEqual(response.status_code, 200)
        return TagAddedEvent.objects.get(patient=self.patient)

    def test_reference_records_team_attribution(self) -> None:
        event = self._add()
        reference = tag_references(event).get()

        self.assertEqual(reference.specialty_id, self.team.pk)
        self.assertEqual(reference.specialty_abbreviation, self.team.abbreviation)

    def test_rename_does_not_detach_an_older_event(self) -> None:
        event = self._add()
        AllowedTag.objects.filter(pk=self.tag.pk).update(name="Referência Nova")

        reference = tag_references(event).get()
        reference_tag = AllowedTag.all_objects.get(pk=reference.tag_id)
        self.assertEqual(reference_tag.pk, self.tag.pk)
        self.assertEqual(reference.tag_name, "Referência")
        self.assertTrue(TagAddedEvent.objects.filter(pk=event.pk).exists())

    def test_archiving_preserves_references_and_associations(self) -> None:
        event = self._add()

        tag_catalogue.archive_tag(
            actor=self.admin,
            tag=AllowedTag.all_objects.get(pk=self.tag.pk),
        )

        self.assertTrue(Tag.objects.filter(patient=self.patient).exists())
        self.assertEqual(tag_references(event).get().tag_id, self.tag.pk)
        self.assertEqual(tag_references(event).get().tag_name, "Referência")


class TagAuditImmutabilityTests(TestCase):
    """R4: ordinary tag-audit edit/delete is denied on every entry point."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.actor = make_user("immutable-actor")
        cls.admin = make_user(
            "immutable-admin", permissions=None, is_staff=True, is_superuser=True
        )
        cls.tag = make_tag(cls.actor, "Imutável")

    def setUp(self) -> None:
        self.patient = make_patient(self.actor, "Paciente Imutável")
        self.client.force_login(self.actor)
        response = self.client.post(
            reverse("patients:patient_tag_add", kwargs={"patient_id": self.patient.pk}),
            {"tag_id": self.tag.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.event = TagAddedEvent.objects.get(patient=self.patient)

    def test_permission_helpers_deny_edit_and_delete_for_the_creator(self) -> None:
        self.assertFalse(can_edit_event(self.actor, self.event))
        self.assertFalse(can_delete_event(self.actor, self.event))

    def test_model_delete_is_refused(self) -> None:
        with self.assertRaises(ValidationError):
            self.event.delete(deleted_by=self.actor, reason="cleanup")
        self.event.refresh_from_db()
        self.assertFalse(self.event.is_deleted)

    def test_queryset_delete_is_refused(self) -> None:
        with self.assertRaises(ValidationError):
            Event.objects.filter(pk=self.event.pk).delete()

        self.event.refresh_from_db()
        self.assertFalse(self.event.is_deleted)
        self.assertEqual(tag_references(self.event).count(), 1)

    def test_queryset_hard_delete_is_refused(self) -> None:
        with self.assertRaises(ValidationError):
            Event.all_objects.filter(pk=self.event.pk).hard_delete()

        self.assertTrue(Event.all_objects.filter(pk=self.event.pk).exists())
        self.assertEqual(tag_references(self.event).count(), 1)

    def test_queryset_delete_still_soft_deletes_ordinary_events(self) -> None:
        ordinary = Event.objects.create(
            patient=self.patient,
            event_type=Event.SIMPLE_NOTE_EVENT,
            event_datetime=timezone.now(),
            description="Nota comum para exclusão",
            created_by=self.actor,
            updated_by=self.actor,
        )

        Event.objects.filter(pk=ordinary.pk).delete()

        ordinary.refresh_from_db()
        self.assertTrue(ordinary.is_deleted)
        self.assertFalse(self.event.is_deleted)

    def test_admin_change_and_delete_are_denied(self) -> None:
        self.client.force_login(self.admin)
        change_response = self.client.post(
            reverse("admin:events_event_change", args=[self.event.pk]),
            {
                "event_type": self.event.event_type,
                "event_datetime_0": self.event.event_datetime.strftime("%Y-%m-%d"),
                "event_datetime_1": self.event.event_datetime.strftime("%H:%M:%S"),
                "patient": str(self.patient.pk),
                "description": "rewritten history",
            },
        )
        delete_response = self.client.post(
            reverse("admin:events_event_delete", args=[self.event.pk]),
            {"post": "yes"},
        )
        select_response = self.client.post(
            reverse("admin:events_event_changelist"),
            {
                "action": "delete_selected",
                "_selected_action": [str(self.event.pk)],
                "post": "yes",
            },
        )

        self.assertEqual(change_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.assertEqual(select_response.status_code, 403)
        self.event.refresh_from_db()
        self.assertNotEqual(self.event.description, "rewritten history")
        self.assertFalse(self.event.is_deleted)

    def test_admin_bulk_soft_delete_skips_tag_audit_events(self) -> None:
        ordinary = Event.objects.create(
            patient=self.patient,
            event_type=Event.SIMPLE_NOTE_EVENT,
            event_datetime=timezone.now(),
            description="Nota comum",
            created_by=self.actor,
            updated_by=self.actor,
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("admin:events_event_changelist"),
            {
                "action": "soft_delete_selected",
                "_selected_action": [str(self.event.pk), str(ordinary.pk)],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.event.refresh_from_db()
        ordinary.refresh_from_db()
        self.assertFalse(self.event.is_deleted)
        self.assertTrue(ordinary.is_deleted)


class ConcurrentAssignmentTests(TransactionTestCase):
    """R2: PostgreSQL uniqueness prevents duplicate associations/events."""

    def test_concurrent_duplicate_assignment_creates_one_pair(self) -> None:
        from apps.patients.services import tag_assignments

        actor = make_user("race-actor")
        tag = make_tag(actor, "Corrida")
        patient = make_patient(actor, "Paciente Corrida")
        barrier = threading.Barrier(2)
        outcomes: list[str] = []

        def worker() -> None:
            barrier.wait()
            try:
                tag_assignments.assign_tag(actor=actor, patient=patient, tag=tag)
                outcomes.append("assigned")
            except tag_assignments.TagAlreadyAssociated:
                outcomes.append("duplicate")
            # A thread failure must surface in the assertion message below.
            except Exception as error:  # noqa: BLE001
                outcomes.append(f"error:{type(error).__name__}:{error}")
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        self.assertEqual(sorted(outcomes), ["assigned", "duplicate"])
        self.assertEqual(Tag.objects.filter(patient=patient).count(), 1)
        self.assertEqual(TagAddedEvent.objects.filter(patient=patient).count(), 1)
        event = TagAddedEvent.objects.get(patient=patient)
        self.assertEqual(tag_references(event).count(), 1)


class LegacyReferenceBackfillTests(TransactionTestCase):
    """R3: legacy backfill resolves only unambiguous snapshot identities."""

    def migrate_to(self, targets: list[tuple[str, str]]) -> Any:
        """Migrate the catalogue and event apps to the requested nodes."""
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def _create_legacy_events(self, old_apps: Any) -> dict[str, Any]:
        user_model = old_apps.get_model("accounts", "EqmdCustomUser")
        user = user_model.objects.create(username="legacy-audit", password="x")
        specialty_model = old_apps.get_model("accounts", "MedicalSpecialty")
        specialty = specialty_model.objects.create(
            name="Equipe Legada Auditoria", abbreviation="LEGA"
        )
        tag_model = old_apps.get_model("patients", "AllowedTag")
        history_model = old_apps.get_model("patients", "HistoricalAllowedTag")
        patient_model = old_apps.get_model("patients", "Patient")
        patient = patient_model.objects.create(
            name="Paciente Legado Auditoria",
            birthday="1980-01-01",
            created_by_id=user.pk,
            updated_by_id=user.pk,
        )

        renamed = tag_model.objects.create(
            name="Avaliar Renomeada",
            specialty_id=specialty.pk,
            created_by_id=user.pk,
            updated_by_id=user.pk,
        )
        current = tag_model.objects.create(
            name="Compartilhada",
            specialty_id=specialty.pk,
            created_by_id=user.pk,
            updated_by_id=user.pk,
        )
        other = tag_model.objects.create(
            name="Compartilhada Outra",
            specialty_id=specialty.pk,
            created_by_id=user.pk,
            updated_by_id=user.pk,
        )
        past = timezone.now() - timedelta(days=10)
        for tag in (renamed, current, other):
            history_model.objects.create(
                id=tag.pk,
                name="Avaliar" if tag.pk == renamed.pk else "Compartilhada",
                color=tag.color,
                is_active=True,
                created_by_id=user.pk,
                updated_by_id=user.pk,
                created_at=past,
                updated_at=past,
                history_date=past,
                history_type="+",
                history_user_id=user.pk,
            )

        event_time = timezone.now() - timedelta(days=5)
        # The subclass row carries the snapshot fields used by the backfill.
        TagAddedEvent_model = old_apps.get_model("events", "TagAddedEvent")
        added_subclass = TagAddedEvent_model.objects.create(
            patient_id=patient.pk,
            event_type=20,
            event_datetime=event_time,
            description="Tag 'Avaliar' adicionada",
            created_by_id=user.pk,
            updated_by_id=user.pk,
            tag_name="Avaliar",
            tag_color="#123456",
            tag_notes="legacy",
            is_deleted=False,
        )
        ambiguous = TagAddedEvent_model.objects.create(
            patient_id=patient.pk,
            event_type=20,
            event_datetime=event_time,
            description="Tag 'Compartilhada' adicionada",
            created_by_id=user.pk,
            updated_by_id=user.pk,
            tag_name="Compartilhada",
            tag_color="#654321",
            tag_notes="",
            is_deleted=False,
        )
        unresolved = TagAddedEvent_model.objects.create(
            patient_id=patient.pk,
            event_type=20,
            event_datetime=event_time,
            description="Tag 'Inexistente' adicionada",
            created_by_id=user.pk,
            updated_by_id=user.pk,
            tag_name="Inexistente",
            tag_color="#111111",
            tag_notes="",
            is_deleted=False,
        )
        return {
            "user_pk": user.pk,
            "specialty_pk": specialty.pk,
            "renamed_pk": renamed.pk,
            "current_pk": current.pk,
            "patient_pk": patient.pk,
            "known_event_pk": added_subclass.pk,
            "ambiguous_event_pk": ambiguous.pk,
            "unresolved_event_pk": unresolved.pk,
            "known_description": added_subclass.description,
        }

    def test_backfill_resolves_known_and_leaves_ambiguous_unresolved(self) -> None:
        legacy: dict[str, Any] = {}
        try:
            old_apps = self.migrate_to(BEFORE)
            legacy = self._create_legacy_events(old_apps)
        finally:
            self.migrate_to(AFTER)

        known = TagAddedEvent.objects.get(pk=legacy["known_event_pk"])
        ambiguous = TagAddedEvent.objects.get(pk=legacy["ambiguous_event_pk"])
        unresolved = TagAddedEvent.objects.get(pk=legacy["unresolved_event_pk"])

        self.assertEqual(known.description, legacy["known_description"])
        self.assertEqual(
            [(ref.tag_id, ref.action, ref.tag_name) for ref in tag_references(known)],
            [(legacy["renamed_pk"], "added", "Avaliar")],
        )
        self.assertTrue(known.tag_name == "Avaliar")
        self.assertEqual(ambiguous.tag_name, "Compartilhada")
        self.assertEqual(tag_references(ambiguous).count(), 0)
        self.assertEqual(unresolved.tag_name, "Inexistente")
        self.assertEqual(tag_references(unresolved).count(), 0)

    def test_preflight_reports_legacy_resolution_without_guessing(self) -> None:
        output = StringIO()
        try:
            old_apps = self.migrate_to(BEFORE)
            self._create_legacy_events(old_apps)
            call_command("preflight_team_tags", stdout=output)
        finally:
            self.migrate_to(AFTER)

        report = output.getvalue()
        self.assertIn("read_only=yes", report)
        self.assertIn(
            "legacy_event_resolution=known=1 ambiguous=1 unresolved=1", report
        )


class LegacyPreflightClassificationTests(TestCase):
    """R3: preflight classifies legacy snapshots without guessing identity."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.actor = make_user("legacy-preflight")
        cls.team = make_specialty("LGPPF")
        cls.renamed = make_tag(
            cls.actor,
            "Avaliar Renomeada",
            specialty=cls.team,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.current = make_tag(
            cls.actor,
            "Compartilhada",
            specialty=cls.team,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.other = make_tag(
            cls.actor,
            "Compartilhada Outra",
            specialty=cls.team,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        past = timezone.now() - timedelta(days=10)
        history_model = AllowedTag.history.model
        for tag, historical_name in (
            (cls.renamed, "Avaliar"),
            (cls.current, "Compartilhada"),
            (cls.other, "Compartilhada"),
        ):
            history_model.objects.create(
                id=tag.pk,
                name=historical_name,
                color=tag.color,
                is_active=True,
                visibility=tag.visibility,
                specialty_id=tag.specialty_id,
                created_by_id=cls.actor.pk,
                updated_by_id=cls.actor.pk,
                created_at=past,
                updated_at=past,
                history_date=past,
                history_type="+",
                history_user_id=cls.actor.pk,
            )

    def _legacy_event(self, tag_name: str) -> TagAddedEvent:
        return TagAddedEvent.objects.create(
            patient=make_patient(self.actor, f"Paciente {tag_name}"),
            event_datetime=timezone.now() - timedelta(days=5),
            description=f"Tag '{tag_name}' adicionada",
            tag_name=tag_name,
            tag_color="#222222",
            tag_notes="",
            created_by=self.actor,
            updated_by=self.actor,
        )

    def test_preflight_counts_known_ambiguous_and_unresolved(self) -> None:
        self._legacy_event("Avaliar")
        self._legacy_event("Compartilhada")
        self._legacy_event("Inexistente")
        output = StringIO()

        call_command("preflight_team_tags", stdout=output)

        report = output.getvalue()
        self.assertIn("read_only=yes", report)
        self.assertIn(
            "legacy_event_resolution=known=1 ambiguous=1 unresolved=1", report
        )
        self.assertNotIn("deferred_s4", report)
