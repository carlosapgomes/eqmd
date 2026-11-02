"""
Tests for medical specialty admin configuration (Phase 3: TDD).

This file contains tests for Django admin interface for managing
medical specialties and user specialty assignments.
"""
from typing import Any, cast

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.admin import (
    MedicalSpecialtyAdmin,
    UserSpecialtyAdmin,
    UserSpecialtyInline,
    UserSpecialtyInlineFormSet,
)
from apps.accounts.models import EqmdCustomUser, MedicalSpecialty, UserSpecialty
from apps.accounts.tests.factories import (
    DoctorFactory,
    StaffUserFactory,
    SuperUserFactory,
)

User = get_user_model()


# ============================================================================
# TASK 3.1: Tests for MedicalSpecialty CRUD Operations
# ============================================================================

class MedicalSpecialtyAdminTestCase(TestCase):
    """Test cases for MedicalSpecialtyAdmin (Task 3.1)."""

    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = MedicalSpecialtyAdmin(MedicalSpecialty, self.site)
        self.staff_user = StaffUserFactory()

    def test_list_displays_correct_fields(self):
        """Test that list_display shows correct fields."""
        MedicalSpecialty.objects.create(
            name='Test Cirurgia Vascular',
            abbreviation='TCIRVASC'
        )

        result = self.admin.get_list_display(None)

        expected = ['name', 'abbreviation', 'is_active', 'created_at']
        self.assertEqual(list(result), expected)

    def test_list_filters_include_is_active(self):
        """Test that list_filters includes is_active field."""
        result = self.admin.get_list_filter(None)

        self.assertIn('is_active', result)

    def test_search_fields_include_name_and_abbreviation(self):
        """Test that search_fields include name and abbreviation."""
        result = self.admin.get_search_fields(None)

        self.assertIn('name', result)
        self.assertIn('abbreviation', result)

    def test_ordering_by_name(self):
        """Test that ordering is by name."""
        result = self.admin.get_ordering(None)

        self.assertEqual(result, ('name',))

    def test_fieldsets_structure(self):
        """Test that fieldsets are properly configured."""
        fieldsets = self.admin.get_fieldsets(None)

        # Should have three fieldsets (identification, details, team tag)
        self.assertEqual(len(fieldsets), 3)

        # First fieldset should have name and abbreviation
        self.assertIn('name', fieldsets[0][1]['fields'])
        self.assertIn('abbreviation', fieldsets[0][1]['fields'])

        # Second fieldset should have description and is_active
        self.assertIn('description', fieldsets[1][1]['fields'])
        self.assertIn('is_active', fieldsets[1][1]['fields'])

        # Third fieldset exposes the public principal tag mapping
        self.assertIn('principal_tag', fieldsets[2][1]['fields'])


# ============================================================================
# TASK 3.2: Tests for UserSpecialtyInline in User Admin
# ============================================================================

class UserSpecialtyInlineTestCase(TestCase):
    """Test cases for UserSpecialtyInline (Task 3.2)."""

    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.inline = UserSpecialtyInline(UserSpecialty, self.site)

    def test_inline_model_is_user_specialty(self):
        """Test that inline uses UserSpecialty model."""
        self.assertEqual(self.inline.model, UserSpecialty)

    def test_extra_is_zero(self):
        """Test that extra forms is set to 0."""
        self.assertEqual(self.inline.extra, 0)

    def test_readonly_fields_include_assigned_at(self):
        """Test that assigned_at is in readonly_fields."""
        readonly_fields = self.inline.get_readonly_fields(None)

        self.assertIn('assigned_at', readonly_fields)
        self.assertIn('is_active', readonly_fields)
        self.assertIn('is_leader', readonly_fields)

    def test_inline_fields_include_correct_fields(self):
        """Test that inline includes correct fields."""
        fields = self.inline.get_fields(None)

        expected_fields = [
            'specialty',
            'is_primary',
            'is_active',
            'is_leader',
            'assigned_at',
            'assigned_by',
            'deactivated_at',
        ]
        self.assertEqual(sorted(fields), sorted(expected_fields))


# ============================================================================
# TASK 3.3: Tests for Specialty Assignment via User Admin
# ============================================================================

class SpecialtyAssignmentTestCase(TestCase):
    """Test cases for specialty assignment functionality (Task 3.3)."""

    def test_assign_specialty_to_user_via_inline(self):
        """
        Test assigning a specialty to a user through admin inline.

        **WHEN** an administrator assigns a specialty to a user via the
        user admin inline
        **THEN** a UserSpecialty record is created with the user and specialty
        """
        user = DoctorFactory()
        specialty = MedicalSpecialty.objects.create(
            name='Test Cirurgia Geral',
            abbreviation='TCIRGER'
        )

        # Simulate admin inline assignment
        UserSpecialty.objects.create(
            user=user,
            specialty=specialty,
            is_primary=True
        )

        # Verify assignment exists
        assignment = UserSpecialty.objects.get(user=user, specialty=specialty)
        self.assertIsNotNone(assignment)
        self.assertTrue(assignment.is_primary)

    def test_assign_multiple_specialties_to_user(self):
        """Test that multiple specialties can be assigned to a user."""
        user = DoctorFactory()
        specialty1 = MedicalSpecialty.objects.create(
            name='Test Cirurgia Geral',
            abbreviation='TCIRGER'
        )
        specialty2 = MedicalSpecialty.objects.create(
            name='Test Cirurgia Vascular',
            abbreviation='TCIRVASC'
        )

        # Assign multiple specialties
        UserSpecialty.objects.create(user=user, specialty=specialty1)
        UserSpecialty.objects.create(user=user, specialty=specialty2)

        # Verify both assignments exist
        self.assertEqual(user.user_specialties.count(), 2)
        self.assertTrue(
            user.user_specialties.filter(specialty=specialty1).exists()
        )
        self.assertTrue(
            user.user_specialties.filter(specialty=specialty2).exists()
        )

    def test_remove_specialty_from_user(self):
        """Test that a specialty can be removed from a user."""
        user = DoctorFactory()
        specialty = MedicalSpecialty.objects.create(
            name='Test Cirurgia Geral',
            abbreviation='TCIRGER'
        )

        # Create assignment
        assignment = UserSpecialty.objects.create(user=user, specialty=specialty)

        # Remove assignment
        assignment.delete()

        # Verify it's gone
        self.assertFalse(
            UserSpecialty.objects.filter(user=user, specialty=specialty).exists()
        )

    def test_mark_primary_specialty(self):
        """
        Test marking a specialty as primary.

        **WHEN** an administrator marks is_primary=True on a user's specialty
        assignment
        **THEN** the specialty is marked as the user's primary specialty
        """
        user = DoctorFactory()
        specialty1 = MedicalSpecialty.objects.create(
            name='Test Cirurgia Geral',
            abbreviation='TCIRGER'
        )
        specialty2 = MedicalSpecialty.objects.create(
            name='Test Cirurgia Vascular',
            abbreviation='TCIRVASC'
        )

        # Create assignments
        UserSpecialty.objects.create(
            user=user,
            specialty=specialty1,
            is_primary=False
        )
        UserSpecialty.objects.create(
            user=user,
            specialty=specialty2,
            is_primary=True
        )

        # Verify primary is correctly set
        primary = user.user_specialties.get(is_primary=True)
        self.assertEqual(primary.specialty, specialty2)

    def test_admin_can_create_specialty(self):
        """
        Test that admin can create medical specialty.

        **WHEN** an administrator creates a medical specialty with name,
        abbreviation, and optional description
        **THEN** the specialty is saved in the database with is_active=True
        and generated timestamps
        """
        MedicalSpecialty.objects.create(
            name='Test Cardiologia',
            abbreviation='TCARDIO',
            description='Especialidade médica focada no coração'
        )

        # Verify specialty was created
        retrieved = MedicalSpecialty.objects.get(abbreviation='TCARDIO')
        self.assertEqual(retrieved.name, 'Test Cardiologia')
        self.assertEqual(retrieved.description, 'Especialidade médica focada no coração')
        self.assertTrue(retrieved.is_active)
        self.assertIsNotNone(retrieved.created_at)
        self.assertIsNotNone(retrieved.updated_at)

    def test_admin_can_soft_delete_specialty(self):
        """
        Test soft delete functionality.

        **WHEN** an administrator sets is_active=False on a specialty
        **THEN** the specialty is no longer available for assignment but
        existing assignments are preserved
        """
        specialty = MedicalSpecialty.objects.create(
            name='Test Cardiologia',
            abbreviation='TCARDIO',
            is_active=True
        )

        # Soft delete
        specialty.is_active = False
        specialty.save()

        # Refresh from database
        specialty.refresh_from_db()

        # Verify it's inactive
        self.assertFalse(specialty.is_active)

        # Verify it still exists
        self.assertTrue(
            MedicalSpecialty.objects.filter(id=specialty.id).exists()
        )


class AdminMembershipFlowTestCase(TestCase):
    """Runtime admin flows for durable team membership (R1/R4)."""

    def setUp(self) -> None:
        self.admin = SuperUserFactory(
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
        )
        self.client = Client()
        self.client.login(username=self.admin.username, password="testpass123")
        self.specialty = MedicalSpecialty.objects.create(
            name="Cirurgia Geral", abbreviation="ADCIRGER"
        )

    def create_membership(self, user: EqmdCustomUser) -> UserSpecialty:
        return UserSpecialty.objects.create(
            user=user, specialty=self.specialty, assigned_by=self.admin
        )

    def test_admin_action_grants_two_leaders(self) -> None:
        first = self.create_membership(DoctorFactory())
        second = self.create_membership(DoctorFactory())

        response = self.client.post(
            reverse("admin:accounts_userspecialty_changelist"),
            {
                "action": "grant_leadership",
                "_selected_action": [str(first.pk), str(second.pk)],
                "index": "0",
                "select_across": "0",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertTrue(first.is_leader)
        self.assertTrue(second.is_leader)
        self.assertEqual(first.leadership_granted_by, self.admin)

    def test_ordinary_admin_delete_deactivates_instead_of_deleting(self) -> None:
        membership = self.create_membership(DoctorFactory())
        membership.user.profile.current_specialty = self.specialty
        membership.user.profile.save()

        response = self.client.post(
            reverse("admin:accounts_userspecialty_delete", args=[membership.pk]),
            {"post": "yes"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        retained = UserSpecialty.objects.get(pk=membership.pk)
        self.assertFalse(retained.is_active)
        self.assertEqual(retained.deactivated_by, self.admin)
        membership.user.profile.refresh_from_db()
        self.assertIsNone(membership.user.profile.current_specialty)

    def test_admin_delete_queryset_deactivates_all_rows(self) -> None:
        memberships = [self.create_membership(DoctorFactory()) for _ in range(2)]
        model_admin = UserSpecialtyAdmin(UserSpecialty, AdminSite())
        request = RequestFactory().post("/admin/accounts/userspecialty/")
        request.user = self.admin

        model_admin.delete_queryset(
            request,
            UserSpecialty.objects.filter(
                pk__in=[membership.pk for membership in memberships]
            ),
        )

        for membership in memberships:
            membership.refresh_from_db()
            self.assertFalse(membership.is_active)

    def test_inline_deletion_deactivates_membership(self) -> None:
        membership = self.create_membership(DoctorFactory())
        request = RequestFactory().post("/admin/accounts/eqmdcustomuser/")
        request.user = self.admin
        inline = UserSpecialtyInline(User, AdminSite())
        formset_class = cast(
            type[UserSpecialtyInlineFormSet],
            inline.get_formset(request, membership.user),
        )
        prefix = "user_specialties"
        data: dict[str, Any] = {
            f"{prefix}-TOTAL_FORMS": "1",
            f"{prefix}-INITIAL_FORMS": "1",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-id": str(membership.pk),
            f"{prefix}-0-specialty": str(self.specialty.pk),
            f"{prefix}-0-is_primary": "",
            f"{prefix}-0-DELETE": "on",
        }

        formset = formset_class(instance=membership.user, data=data, prefix=prefix)
        formset.request = request
        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()

        retained = UserSpecialty.objects.get(pk=membership.pk)
        self.assertFalse(retained.is_active)


class PrincipalTagAdminTestCase(TestCase):
    """S2 R3: administrators configure one public same-namespace principal."""

    def setUp(self) -> None:
        self.admin = SuperUserFactory(
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
        )
        self.client = Client()
        self.client.login(username=self.admin.username, password="testpass123")
        self.specialty = MedicalSpecialty.objects.create(
            name="Cirurgia Geral", abbreviation="PCIRGER"
        )
        self.other_specialty = MedicalSpecialty.objects.create(
            name="Cardiologia", abbreviation="PCARDIO"
        )
        from apps.patients.models import AllowedTag

        self.public_tag = AllowedTag.objects.create(
            name="Reavaliar",
            specialty=self.specialty,
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.restricted_tag = AllowedTag.objects.create(
            name="Restrita",
            specialty=self.specialty,
            visibility=AllowedTag.Visibility.RESTRICTED,
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.foreign_tag = AllowedTag.objects.create(
            name="Reavaliar",
            specialty=self.other_specialty,
            created_by=self.admin,
            updated_by=self.admin,
        )

    def _payload(self, principal_tag) -> dict[str, Any]:
        return {
            "name": self.specialty.name,
            "abbreviation": self.specialty.abbreviation,
            "description": "",
            "is_active": "on",
            "principal_tag": "" if principal_tag is None else str(principal_tag.pk),
            "_save": "Salvar",
        }

    def _change_url(self) -> str:
        return reverse(
            "admin:accounts_medicalspecialty_change", args=[self.specialty.pk]
        )

    def test_admin_configures_public_same_namespace_principal(self) -> None:
        response = self.client.post(
            self._change_url(), self._payload(self.public_tag)
        )
        self.assertEqual(response.status_code, 302)
        self.specialty.refresh_from_db()
        self.assertEqual(self.specialty.principal_tag_id, self.public_tag.pk)

    def test_admin_rejects_restricted_principal(self) -> None:
        response = self.client.post(
            self._change_url(), self._payload(self.restricted_tag)
        )
        self.assertEqual(response.status_code, 200)
        self.specialty.refresh_from_db()
        self.assertIsNone(self.specialty.principal_tag_id)

    def test_admin_rejects_foreign_namespace_principal(self) -> None:
        response = self.client.post(
            self._change_url(), self._payload(self.foreign_tag)
        )
        self.assertEqual(response.status_code, 200)
        self.specialty.refresh_from_db()
        self.assertIsNone(self.specialty.principal_tag_id)

    def test_admin_can_clear_principal(self) -> None:
        self.client.post(self._change_url(), self._payload(self.public_tag))
        response = self.client.post(self._change_url(), self._payload(None))
        self.assertEqual(response.status_code, 302)
        self.specialty.refresh_from_db()
        self.assertIsNone(self.specialty.principal_tag_id)
