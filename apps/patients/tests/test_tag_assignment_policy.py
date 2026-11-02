"""S4 R1: per-tag assignment policy on every patient and bulk write path."""

from __future__ import annotations

import threading
import time
from datetime import timedelta
from typing import Any

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import MedicalSpecialty, UserSpecialty
from apps.accounts.tests.helpers import create_navigation_user
from apps.events.models import TagAddedEvent, TagBulkRemoveEvent, TagRemovedEvent
from apps.events.tag_event_reference import TagEventReference
from apps.patients.models import AllowedTag, Patient, PatientAdmission, Tag

CLINICAL_PERMISSIONS = ("change_patient", "view_patient")


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
        password="assignment-pass",
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


def join_team(
    user: Any,
    specialty: MedicalSpecialty,
    *,
    is_leader: bool = False,
    active: bool = True,
) -> UserSpecialty:
    """Create a retained membership row for one team."""
    return UserSpecialty.objects.create(
        user=user, specialty=specialty, is_active=active, is_leader=is_leader
    )


def make_tag(actor: Any, name: str, **overrides: Any) -> AllowedTag:
    """Create a catalogue row without form validation (database path)."""
    return AllowedTag.objects.create(
        name=name, created_by=actor, updated_by=actor, **overrides
    )


def tag_references(event: Any):
    """Return the S4 catalogue references recorded for one event."""
    return event.tag_references.all()


class TagAssignmentPolicyMatrixTests(TestCase):
    """R1: member/outsider/revoked/staff/leader/administrator request matrix."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.cirger = make_specialty("POLCIR")
        cls.cardio = make_specialty("POLCAR")
        cls.owner = make_user("policy-owner")

        cls.principal_tag = make_tag(
            cls.owner,
            "Reavaliar",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.PUBLIC,
        )
        MedicalSpecialty.objects.filter(pk=cls.cirger.pk).update(
            principal_tag_id=cls.principal_tag.pk
        )
        cls.restricted_tag = make_tag(
            cls.owner,
            "Restrita",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.other_team_tag = make_tag(
            cls.owner,
            "Cardio Restrita",
            specialty=cls.cardio,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.public_tag = make_tag(cls.owner, "Prioridade Global")
        cls.inactive_tag = make_tag(
            cls.owner,
            "Inativa",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
        )
        cls.archived_tag = make_tag(
            cls.owner,
            "Arquivada",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
            is_active=False,
            is_deleted=True,
        )

        cls.member = make_user("policy-member")
        join_team(cls.member, cls.cirger)
        cls.outsider = make_user("policy-outsider")
        join_team(cls.outsider, cls.cardio)
        cls.revoked = make_user("policy-revoked")
        join_team(cls.revoked, cls.cirger, active=False)
        cls.leader = make_user("policy-leader")
        join_team(cls.leader, cls.cirger, is_leader=True)
        cls.staff_operator = make_user("policy-staff", is_staff=True)
        cls.catalogue_admin = make_user(
            "policy-admin", permissions=None, is_staff=True, is_superuser=True
        )
        cls.no_clinical_permission = make_user("policy-no-clinical", permissions=None)

        cls.patient = Patient.objects.create(
            name="Paciente Política",
            birthday="1980-01-01",
            status=Patient.Status.OUTPATIENT,
            created_by=cls.owner,
            updated_by=cls.owner,
        )

    def _add_url(self) -> str:
        return reverse(
            "patients:patient_tag_add", kwargs={"patient_id": self.patient.pk}
        )

    def _remove_url(self, tag: Tag) -> str:
        return reverse(
            "patients:patient_tag_remove",
            kwargs={"patient_id": self.patient.pk, "tag_id": tag.pk},
        )

    def _remove_all_url(self) -> str:
        return reverse(
            "patients:patient_tag_remove_all", kwargs={"patient_id": self.patient.pk}
        )

    def _assign(self, actor: Any, tag: AllowedTag) -> Any:
        self.client.force_login(actor)
        return self.client.post(self._add_url(), {"tag_id": tag.pk, "notes": "n"})

    def _assert_no_assignment(self, tag: AllowedTag) -> None:
        self.assertFalse(
            Tag.objects.filter(patient=self.patient, allowed_tag_id=tag.pk).exists()
        )
        self.assertFalse(TagAddedEvent.objects.filter(patient=self.patient).exists())

    def test_member_can_assign_principal_public_tag(self) -> None:
        response = self._assign(self.member, self.principal_tag)

        self.assertEqual(response.status_code, 200)
        association = Tag.objects.get(
            patient=self.patient, allowed_tag_id=self.principal_tag.pk
        )
        event = TagAddedEvent.objects.get(patient=self.patient)
        self.assertEqual(event.tag_name, self.principal_tag.name)
        self.assertEqual(
            [
                (reference.tag_id, reference.action)
                for reference in tag_references(event)
            ],
            [(self.principal_tag.pk, "added")],
        )
        self.assertEqual(association.notes, "n")

    def test_outsider_cannot_assign_principal_public_tag(self) -> None:
        response = self._assign(self.outsider, self.principal_tag)

        self.assertEqual(response.status_code, 400)
        self._assert_no_assignment(self.principal_tag)

    def test_revoked_member_cannot_assign_principal_public_tag(self) -> None:
        response = self._assign(self.revoked, self.principal_tag)

        self.assertEqual(response.status_code, 400)
        self._assert_no_assignment(self.principal_tag)

    def test_leader_cannot_assign_another_teams_restricted_tag(self) -> None:
        self.client.force_login(self.leader)

        response = self.client.post(self._add_url(), {"tag_id": self.other_team_tag.pk})

        self.assertEqual(response.status_code, 400)
        self._assert_no_assignment(self.other_team_tag)

    def test_leader_can_assign_own_restricted_tag(self) -> None:
        self.client.force_login(self.leader)
        response = self.client.post(self._add_url(), {"tag_id": self.restricted_tag.pk})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Tag.objects.filter(
                patient=self.patient, allowed_tag_id=self.restricted_tag.pk
            ).exists()
        )

    def test_outsider_cannot_assign_restricted_team_tag(self) -> None:
        response = self._assign(self.outsider, self.restricted_tag)

        self.assertEqual(response.status_code, 400)
        self._assert_no_assignment(self.restricted_tag)

    def test_catalogue_administrator_overrides_team_membership(self) -> None:
        response = self._assign(self.catalogue_admin, self.principal_tag)
        self.assertEqual(response.status_code, 200)

        other_patient = Patient.objects.create(
            name="Paciente Admin",
            birthday="1981-02-02",
            status=Patient.Status.OUTPATIENT,
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.client.force_login(self.catalogue_admin)
        response = self.client.post(
            reverse(
                "patients:patient_tag_add", kwargs={"patient_id": other_patient.pk}
            ),
            {"tag_id": self.restricted_tag.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Tag.objects.filter(
                patient=other_patient, allowed_tag_id=self.restricted_tag.pk
            ).exists()
        )

    def test_staff_without_catalogue_authority_gains_no_team_override(self) -> None:
        response = self._assign(self.staff_operator, self.restricted_tag)

        self.assertEqual(response.status_code, 400)
        self._assert_no_assignment(self.restricted_tag)

    def test_non_principal_public_tag_keeps_clinical_baseline(self) -> None:
        response = self._assign(self.outsider, self.public_tag)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Tag.objects.filter(
                patient=self.patient, allowed_tag_id=self.public_tag.pk
            ).exists()
        )

    def test_assignment_requires_clinical_mutation_permission(self) -> None:
        response = self._assign(self.no_clinical_permission, self.public_tag)

        self.assertEqual(response.status_code, 403)
        self._assert_no_assignment(self.public_tag)

    def test_inactive_tag_cannot_be_newly_assigned(self) -> None:
        response = self._assign(self.member, self.inactive_tag)

        self.assertEqual(response.status_code, 400)
        self._assert_no_assignment(self.inactive_tag)

    def test_archived_tag_cannot_be_newly_assigned(self) -> None:
        response = self._assign(self.member, self.archived_tag)

        self.assertEqual(response.status_code, 404)
        self._assert_no_assignment(self.archived_tag)

    def test_member_can_remove_inactive_association(self) -> None:
        association = Tag.objects.create(
            allowed_tag=self.inactive_tag,
            patient=self.patient,
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.client.force_login(self.member)

        response = self.client.post(self._remove_url(association))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Tag.objects.filter(pk=association.pk).exists())
        event = TagRemovedEvent.objects.get(patient=self.patient)
        self.assertEqual(event.tag_name, self.inactive_tag.name)

    def test_member_can_remove_archived_association(self) -> None:
        association = Tag.objects.create(
            allowed_tag=self.archived_tag,
            patient=self.patient,
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.client.force_login(self.member)

        response = self.client.post(self._remove_url(association))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Tag.objects.filter(pk=association.pk).exists())
        self.assertTrue(TagRemovedEvent.objects.filter(patient=self.patient).exists())

    def test_outsider_cannot_remove_restricted_association(self) -> None:
        association = Tag.objects.create(
            allowed_tag=self.restricted_tag,
            patient=self.patient,
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.client.force_login(self.outsider)

        response = self.client.post(self._remove_url(association))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Tag.objects.filter(pk=association.pk).exists())
        self.assertFalse(TagRemovedEvent.objects.filter(patient=self.patient).exists())

    def test_outsider_cannot_remove_principal_association(self) -> None:
        association = Tag.objects.create(
            allowed_tag=self.principal_tag,
            patient=self.patient,
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.client.force_login(self.outsider)

        response = self.client.post(self._remove_url(association))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Tag.objects.filter(pk=association.pk).exists())

    def test_member_can_remove_principal_association(self) -> None:
        association = Tag.objects.create(
            allowed_tag=self.principal_tag,
            patient=self.patient,
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.client.force_login(self.member)

        response = self.client.post(self._remove_url(association))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Tag.objects.filter(pk=association.pk).exists())


class BulkRemovalAuthorizedSetTests(TestCase):
    """R1: bulk removal touches only the caller's authorized associations."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.owner = make_user("bulk-owner")
        cls.cirger = make_specialty("BLKCIR")
        cls.cardio = make_specialty("BLKCAR")
        cls.cirger_tag = make_tag(
            cls.owner,
            "Cirurgia",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.cardio_tag = make_tag(
            cls.owner,
            "Cardio",
            specialty=cls.cardio,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.public_tag = make_tag(cls.owner, "Acompanhamento")
        cls.cirger_member = make_user("bulk-cirger")
        join_team(cls.cirger_member, cls.cirger)
        cls.patient = Patient.objects.create(
            name="Paciente Lote",
            birthday="1979-03-03",
            status=Patient.Status.OUTPATIENT,
            created_by=cls.owner,
            updated_by=cls.owner,
        )

    def _associate(self, tag: AllowedTag) -> Tag:
        return Tag.objects.create(
            allowed_tag=tag,
            patient=self.patient,
            created_by=self.owner,
            updated_by=self.owner,
        )

    def _remove_all(self) -> Any:
        return self.client.post(
            reverse(
                "patients:patient_tag_remove_all",
                kwargs={"patient_id": self.patient.pk},
            )
        )

    def test_bulk_removal_preserves_other_teams_associations(self) -> None:
        self._associate(self.cirger_tag)
        self._associate(self.cardio_tag)
        self._associate(self.public_tag)
        self.client.force_login(self.cirger_member)

        response = self._remove_all()

        self.assertEqual(response.status_code, 200)
        data = response.json()
        remaining = list(
            Tag.objects.filter(patient=self.patient).values_list(
                "allowed_tag_id", flat=True
            )
        )
        # The other team's restricted tag is preserved; the non-principal public
        # tag stays on the caller's clinical mutation baseline.
        self.assertEqual(remaining, [self.cardio_tag.pk])
        self.assertEqual(data["preserved"], 1)
        # S5: the surviving association belongs to another team's restricted
        # tag, so the response payload is requester-projected and omits it even
        # though the association itself is preserved in the database.
        self.assertEqual([item["allowed_tag_id"] for item in data["tags"]], [])
        event = TagBulkRemoveEvent.objects.get(patient=self.patient)
        self.assertEqual(event.tag_count, 2)
        self.assertEqual(
            sorted(reference.tag_id for reference in tag_references(event)),
            sorted([self.cirger_tag.pk, self.public_tag.pk]),
        )

    def test_bulk_removal_without_authorized_associations_is_denied(self) -> None:
        self._associate(self.cirger_tag)
        self._associate(self.cardio_tag)
        self.client.force_login(self.owner)

        response = self._remove_all()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Nenhuma tag para remover")
        self.assertEqual(Tag.objects.filter(patient=self.patient).count(), 2)
        self.assertFalse(
            TagBulkRemoveEvent.objects.filter(patient=self.patient).exists()
        )


class ClinicalTransitionTagPreservationTests(TestCase):
    """R4: discharge and status changes never clear team tag associations."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.owner = make_user("transition-owner")
        cls.cirger = make_specialty("TRNCIR")
        cls.cardio = make_specialty("TRNCAR")
        cls.cirger_tag = make_tag(
            cls.owner,
            "Transição Cirurgia",
            specialty=cls.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        cls.cardio_tag = make_tag(
            cls.owner,
            "Transição Cardio",
            specialty=cls.cardio,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )

    def _patient_with_two_team_tags(self) -> tuple[Patient, list[Tag]]:
        patient = Patient.objects.create(
            name="Paciente Transição",
            birthday="1978-04-04",
            status=Patient.Status.INPATIENT,
            created_by=self.owner,
            updated_by=self.owner,
        )
        associations = [
            Tag.objects.create(
                allowed_tag=tag,
                patient=patient,
                created_by=self.owner,
                updated_by=self.owner,
            )
            for tag in (self.cirger_tag, self.cardio_tag)
        ]
        return patient, associations

    def test_discharge_does_not_clear_team_classifications(self) -> None:
        patient, associations = self._patient_with_two_team_tags()
        admission_time = timezone.now() - timedelta(days=2)

        PatientAdmission.objects.create(
            patient=patient,
            admission_datetime=admission_time,
            discharge_datetime=admission_time + timedelta(days=1),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            created_by=self.owner,
            updated_by=self.owner,
        )

        self.assertEqual(
            sorted(
                Tag.objects.filter(patient=patient).values_list(
                    "allowed_tag_id", flat=True
                )
            ),
            sorted([association.allowed_tag_id for association in associations]),
        )

    def test_status_change_does_not_clear_team_classifications(self) -> None:
        patient, associations = self._patient_with_two_team_tags()

        patient.status = Patient.Status.OUTPATIENT
        patient.bed = ""
        patient.save()

        self.assertEqual(
            sorted(
                Tag.objects.filter(patient=patient).values_list(
                    "allowed_tag_id", flat=True
                )
            ),
            sorted([association.allowed_tag_id for association in associations]),
        )


class MembershipRevocationRaceTests(TransactionTestCase):
    """R1: assignment revalidates authority from the locked membership row."""

    def test_revocation_under_the_lock_denies_the_assignment(self) -> None:
        from apps.accounts.services import team_membership
        from apps.patients.services import tag_assignments

        administrator = make_user(
            "race-admin", permissions=None, is_staff=True, is_superuser=True
        )
        member = make_user("race-member")
        team = make_specialty("RACEM")
        membership = join_team(member, team)
        tag = make_tag(
            administrator,
            "Corrida Revogação",
            specialty=team,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        patient = Patient.objects.create(
            name="Paciente Corrida Revogação",
            birthday="1982-06-06",
            status=Patient.Status.OUTPATIENT,
            created_by=administrator,
            updated_by=administrator,
        )
        locked = threading.Event()
        release = threading.Event()
        outcomes: list[str] = []

        def revoker() -> None:
            try:
                with transaction.atomic():
                    UserSpecialty.objects.select_for_update().get(pk=membership.pk)
                    locked.set()
                    release.wait(timeout=30)
                    team_membership.revoke_membership(
                        actor=administrator, membership=membership
                    )
            finally:
                connection.close()

        def assigner() -> None:
            try:
                tag_assignments.assign_tag(actor=member, patient=patient, tag=tag)
                outcomes.append("assigned")
            except PermissionDenied:
                outcomes.append("denied")
            # A thread failure must surface in the assertion message below.
            except Exception as error:  # noqa: BLE001
                outcomes.append(f"error:{type(error).__name__}:{error}")
            finally:
                connection.close()

        revoke_thread = threading.Thread(target=revoker)
        revoke_thread.start()
        self.assertTrue(locked.wait(timeout=30), "revoker never took the row lock")
        assign_thread = threading.Thread(target=assigner)
        assign_thread.start()
        waited_for_lock = self._wait_until_blocked_on_lock(assign_thread)
        release.set()
        revoke_thread.join(timeout=30)
        assign_thread.join(timeout=30)

        self.assertFalse(revoke_thread.is_alive())
        self.assertFalse(assign_thread.is_alive())
        self.assertTrue(waited_for_lock, f"assignment never waited: {outcomes}")
        self.assertEqual(outcomes, ["denied"])
        self.assertFalse(Tag.objects.filter(patient=patient).exists())
        self.assertFalse(TagAddedEvent.objects.filter(patient=patient).exists())
        self.assertFalse(
            TagEventReference.objects.filter(event__patient=patient).exists()
        )

    def _wait_until_blocked_on_lock(self, assigner: threading.Thread) -> bool:
        """Return whether the assignment waits on a row lock before finishing."""
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if not assigner.is_alive():
                return False
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_locks WHERE NOT granted")
                if cursor.fetchone()[0]:
                    return True
            time.sleep(0.02)
        return False
