"""S1 behavior tests for durable specialty team membership and leadership."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from apps.accounts.models import MedicalSpecialty, UserSpecialty
from apps.accounts.services import team_membership
from apps.accounts.tests.factories import DoctorFactory, SuperUserFactory

BASE_MIGRATION = ("accounts", "0005_populate_sample_specialties")
HEAD_MIGRATION = ("accounts", "0006_userspecialty_team_membership")
NAVIGATION_USER_KWARGS = {
    "password": "testpass123",
    "password_change_required": False,
    "terms_accepted": True,
}


def make_specialty(name: str, abbreviation: str, *, is_active: bool = True) -> MedicalSpecialty:
    return MedicalSpecialty.objects.create(
        name=name, abbreviation=abbreviation, is_active=is_active
    )


class MembershipStateTestCase(TestCase):
    """R1: membership rows carry durable active/leader state."""

    def setUp(self) -> None:
        self.user = DoctorFactory()
        self.specialty = make_specialty("Cirurgia Geral", "TCIRGER")

    def test_new_membership_is_active_and_not_leader(self) -> None:
        membership = UserSpecialty.objects.create(user=self.user, specialty=self.specialty)

        self.assertTrue(membership.is_active)
        self.assertFalse(membership.is_leader)
        self.assertIsNone(membership.deactivated_at)
        self.assertIsNone(membership.deactivated_by)

    def test_multiple_leaders_coexist_for_one_specialty(self) -> None:
        leader_a = DoctorFactory()
        leader_b = DoctorFactory()
        membership_a = UserSpecialty.objects.create(
            user=leader_a, specialty=self.specialty, is_leader=True
        )
        membership_b = UserSpecialty.objects.create(
            user=leader_b, specialty=self.specialty, is_leader=True
        )

        self.assertTrue(membership_a.is_leader)
        self.assertTrue(membership_b.is_leader)
        self.assertEqual(
            UserSpecialty.objects.filter(specialty=self.specialty, is_leader=True).count(), 2
        )

    def test_inactive_membership_is_excluded_from_user_specialties(self) -> None:
        UserSpecialty.objects.create(
            user=self.user, specialty=self.specialty, is_active=False
        )

        self.assertEqual(self.user.specialties, [])
        self.assertIsNone(self.user.primary_specialty)

    def test_primary_specialty_ignores_inactive_membership(self) -> None:
        inactive = make_specialty("Cardiologia", "TCARDIO")
        active = make_specialty("Pediatria", "TPED")
        UserSpecialty.objects.create(
            user=self.user, specialty=inactive, is_primary=True, is_active=False
        )
        UserSpecialty.objects.create(user=self.user, specialty=active)

        self.assertEqual(self.user.specialties, [active])
        self.assertEqual(self.user.primary_specialty, active)

    def test_leader_requires_active_membership_constraint(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            UserSpecialty.objects.create(
                user=self.user,
                specialty=self.specialty,
                is_active=False,
                is_leader=True,
            )


class MembershipServiceTestCase(TestCase):
    """R1/R3: administrator grants, revocations and retained identity."""

    def setUp(self) -> None:
        self.admin = SuperUserFactory()
        self.user = DoctorFactory()
        self.specialty = make_specialty("Cirurgia Geral", "SCIRGER")
        self.other = make_specialty("Cardiologia", "SCARDIO")

    def test_admin_grant_records_actor_and_time(self) -> None:
        membership = team_membership.grant_membership(
            actor=self.admin, user=self.user, specialty=self.specialty
        )

        self.assertTrue(membership.is_active)
        self.assertEqual(membership.assigned_by, self.admin)
        self.assertIsNotNone(membership.assigned_at)

    def test_admin_can_grant_two_leaders(self) -> None:
        membership_a = team_membership.grant_membership(
            actor=self.admin, user=DoctorFactory(), specialty=self.specialty
        )
        membership_b = team_membership.grant_membership(
            actor=self.admin, user=DoctorFactory(), specialty=self.specialty
        )

        team_membership.grant_leadership(actor=self.admin, membership=membership_a)
        team_membership.grant_leadership(actor=self.admin, membership=membership_b)

        membership_a.refresh_from_db()
        membership_b.refresh_from_db()
        self.assertTrue(membership_a.is_leader and membership_b.is_leader)
        self.assertEqual(membership_a.leadership_granted_by, self.admin)

    def test_revoke_deactivates_retains_row_and_clears_current_context(self) -> None:
        membership = team_membership.grant_membership(
            actor=self.admin, user=self.user, specialty=self.specialty
        )
        team_membership.grant_leadership(actor=self.admin, membership=membership)
        self.user.profile.current_specialty = self.specialty
        self.user.profile.save()

        revoked = team_membership.revoke_membership(actor=self.admin, membership=membership)

        self.assertEqual(revoked.pk, membership.pk)
        self.assertFalse(revoked.is_active)
        self.assertFalse(revoked.is_leader)
        self.assertEqual(revoked.deactivated_by, self.admin)
        self.assertIsNotNone(revoked.leadership_revoked_at)
        self.assertEqual(revoked.leadership_revoked_by, self.admin)
        self.user.profile.refresh_from_db()
        self.assertIsNone(self.user.profile.current_specialty)
        self.assertTrue(UserSpecialty.objects.filter(pk=membership.pk).exists())

    def test_rejoin_reuses_row_preserves_assignment_and_leadership(self) -> None:
        membership = team_membership.grant_membership(
            actor=self.admin, user=self.user, specialty=self.specialty
        )
        team_membership.grant_leadership(actor=self.admin, membership=membership)
        original_pk = membership.pk
        original_assigned_at = membership.assigned_at
        original_assigned_by = membership.assigned_by
        team_membership.revoke_membership(actor=self.admin, membership=membership)

        rejoined = team_membership.grant_membership(
            actor=self.admin, user=self.user, specialty=self.specialty
        )

        self.assertEqual(rejoined.pk, original_pk)
        self.assertTrue(rejoined.is_active)
        self.assertFalse(rejoined.is_leader)
        self.assertEqual(rejoined.assigned_at, original_assigned_at)
        self.assertEqual(rejoined.assigned_by, original_assigned_by)
        self.assertEqual(rejoined.reactivated_by, self.admin)
        self.assertEqual(UserSpecialty.objects.filter(user=self.user, specialty=self.specialty).count(), 1)

    def test_grant_leadership_requires_active_membership(self) -> None:
        membership = UserSpecialty.objects.create(
            user=self.user, specialty=self.specialty, is_active=False
        )

        with self.assertRaises(ValidationError):
            team_membership.grant_leadership(actor=self.admin, membership=membership)

    def test_grant_leadership_requires_active_specialty(self) -> None:
        inactive = make_specialty("Dermatologia", "SDM", is_active=False)
        membership = UserSpecialty.objects.create(
            user=self.user, specialty=inactive, is_active=True
        )

        with self.assertRaises(ValidationError):
            team_membership.grant_leadership(actor=self.admin, membership=membership)

    def test_revoke_leadership_keeps_membership_active(self) -> None:
        membership = team_membership.grant_membership(
            actor=self.admin, user=self.user, specialty=self.specialty
        )
        team_membership.grant_leadership(actor=self.admin, membership=membership)

        updated = team_membership.revoke_leadership(actor=self.admin, membership=membership)

        self.assertFalse(updated.is_leader)
        self.assertTrue(updated.is_active)
        self.assertEqual(updated.leadership_revoked_by, self.admin)

    def test_leader_property_only_reports_active_leadership(self) -> None:
        membership = team_membership.grant_membership(
            actor=self.admin, user=self.user, specialty=self.specialty
        )
        team_membership.grant_leadership(actor=self.admin, membership=membership)
        team_membership.grant_membership(
            actor=self.admin, user=self.user, specialty=self.other
        )

        self.assertEqual(team_membership.leader_specialties(self.user), [self.specialty])
        self.assertTrue(team_membership.is_team_leader(self.user, self.specialty))
        self.assertFalse(team_membership.is_team_leader(self.user, self.other))


class MembershipAdministrationAuthorizationTestCase(TestCase):
    """R4: leadership never grants staff or membership administration."""

    def setUp(self) -> None:
        self.admin = SuperUserFactory()
        self.leader = DoctorFactory(**NAVIGATION_USER_KWARGS)
        self.specialty = make_specialty("Cirurgia Geral", "ACIRGER")
        self.membership = team_membership.grant_membership(
            actor=self.admin, user=self.leader, specialty=self.specialty
        )
        team_membership.grant_leadership(actor=self.admin, membership=self.membership)

    def test_leadership_does_not_grant_staff_or_permissions(self) -> None:
        self.leader.refresh_from_db()

        self.assertFalse(self.leader.is_staff)
        self.assertFalse(self.leader.is_superuser)
        self.assertFalse(self.leader.has_perm("accounts.change_userspecialty"))
        self.assertFalse(self.leader.has_perm("auth.change_user"))

    def test_leader_cannot_mutate_membership_through_service(self) -> None:
        with self.assertRaises(PermissionDenied):
            team_membership.grant_membership(
                actor=self.leader, user=DoctorFactory(), specialty=self.specialty
            )
        with self.assertRaises(PermissionDenied):
            team_membership.revoke_membership(
                actor=self.leader, membership=self.membership
            )
        with self.assertRaises(PermissionDenied):
            team_membership.grant_leadership(
                actor=self.leader, membership=self.membership
            )

    def test_leader_cannot_open_django_admin(self) -> None:
        client = Client()
        client.login(username=self.leader.username, password="testpass123")

        response = client.get("/admin/")

        self.assertIn(response.status_code, (301, 302))
        self.assertNotEqual(response.status_code, 200)

    def test_leader_cannot_delete_membership_through_admin(self) -> None:
        client = Client()
        client.login(username=self.leader.username, password="testpass123")
        url = f"/admin/accounts/userspecialty/{self.membership.pk}/delete/"

        client.post(url, {"post": "yes"})

        self.membership.refresh_from_db()
        self.assertTrue(self.membership.is_active)
        self.assertTrue(self.membership.is_leader)

    def test_staff_without_membership_permission_is_denied(self) -> None:
        staff = DoctorFactory(is_staff=True)

        with self.assertRaises(PermissionDenied):
            team_membership.grant_membership(
                actor=staff, user=DoctorFactory(), specialty=self.specialty
            )


class RequestTimeEligibilityTestCase(TestCase):
    """R2/R3: every specialty selection surface validates current membership."""

    def setUp(self) -> None:
        self.user = DoctorFactory(**NAVIGATION_USER_KWARGS)
        self.client = Client()
        self.client.login(username=self.user.username, password="testpass123")
        self.admin = SuperUserFactory()
        self.general = make_specialty("Cirurgia Geral", "RCIRGER")
        self.cardio = make_specialty("Cardiologia", "RCARDIO")
        self.general_membership = team_membership.grant_membership(
            actor=self.admin, user=self.user, specialty=self.general
        )
        self.cardio_membership = team_membership.grant_membership(
            actor=self.admin, user=self.user, specialty=self.cardio
        )
        self.user.profile.current_specialty = self.general
        self.user.profile.save()

    def profile_url(self) -> str:
        return reverse(
            "apps.accounts:profile",
            kwargs={"public_id": self.user.profile.public_id},
        )

    def test_profile_form_only_offers_active_memberships(self) -> None:
        team_membership.revoke_membership(
            actor=self.admin, membership=self.general_membership
        )

        response = self.client.get(
            reverse(
                "apps.accounts:profile_update",
                kwargs={"public_id": self.user.profile.public_id},
            )
        )
        form = response.context["form"]

        self.assertIn(self.cardio, list(form.fields["current_specialty"].queryset))
        self.assertNotIn(self.general, list(form.fields["current_specialty"].queryset))

    def test_switching_api_denies_revoked_membership_without_implicit_switch(self) -> None:
        team_membership.revoke_membership(
            actor=self.admin, membership=self.general_membership
        )

        response = self.client.post(
            reverse("apps.accounts:change_specialty_api"),
            data=f'{{"specialty_id": "{self.general.pk}"}}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.user.profile.refresh_from_db()
        self.assertIsNone(self.user.profile.current_specialty)

    def test_switching_api_denies_inactive_specialty(self) -> None:
        MedicalSpecialty.objects.filter(pk=self.cardio.pk).update(is_active=False)

        response = self.client.post(
            reverse("apps.accounts:change_specialty_api"),
            data=f'{{"specialty_id": "{self.cardio.pk}"}}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_specialty, self.general)

    def test_switching_api_accepts_active_membership(self) -> None:
        response = self.client.post(
            reverse("apps.accounts:change_specialty_api"),
            data=f'{{"specialty_id": "{self.cardio.pk}"}}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_specialty, self.cardio)

    def test_same_session_revocation_clears_context_on_next_profile_request(self) -> None:
        team_membership.revoke_membership(
            actor=self.admin, membership=self.general_membership
        )

        response = self.client.get(self.profile_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Cirurgia Geral")
        self.assertContains(response, "Cardiologia")
        self.user.profile.refresh_from_db()
        self.assertIsNone(self.user.profile.current_specialty)
        self.assertIsNone(self.user.profile.effective_current_specialty)
        self.assertEqual(self.user.specialties, [self.cardio])

    def test_existing_specialty_deactivation_invalidates_current_context(self) -> None:
        MedicalSpecialty.objects.filter(pk=self.general.pk).update(is_active=False)

        response = self.client.get(self.profile_url())

        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertIsNone(self.user.profile.current_specialty)
        self.assertIsNone(self.user.profile.effective_current_specialty)



class MembershipBackfillMigrationTestCase(TransactionTestCase):
    """R1: additive migration retains rows and backfills active membership."""

    def test_existing_membership_rows_backfill_as_active_non_leader(self) -> None:
        executor = MigrationExecutor(connection)
        try:
            executor.migrate([BASE_MIGRATION])
            executor.loader.build_graph()
            old_apps = executor.loader.project_state([BASE_MIGRATION]).apps
            old_user = old_apps.get_model("accounts", "EqmdCustomUser")
            old_specialty = old_apps.get_model("accounts", "MedicalSpecialty")
            old_membership = old_apps.get_model("accounts", "UserSpecialty")
            admin = old_user.objects.create(
                username="migration-admin", email="migration-admin@example.com"
            )
            member = old_user.objects.create(
                username="migration-member", email="migration-member@example.com"
            )
            specialty = old_specialty.objects.create(
                name="Migracao Especialidade", abbreviation="MIGESP"
            )
            membership = old_membership.objects.create(
                user=member, specialty=specialty, assigned_by=admin, is_primary=True
            )
            membership_pk = membership.pk
            assigned_at = membership.assigned_at

            executor = MigrationExecutor(connection)
            executor.migrate([HEAD_MIGRATION])
            executor.loader.build_graph()

            migrated = UserSpecialty.objects.get(pk=membership_pk)
            self.assertTrue(migrated.is_active)
            self.assertFalse(migrated.is_leader)
            self.assertEqual(migrated.assigned_at, assigned_at)
            self.assertEqual(migrated.assigned_by.username, "migration-admin")
            self.assertTrue(migrated.is_primary)
        finally:
            executor = MigrationExecutor(connection)
            executor.loader.build_graph()
            executor.migrate(executor.loader.graph.leaf_nodes())
