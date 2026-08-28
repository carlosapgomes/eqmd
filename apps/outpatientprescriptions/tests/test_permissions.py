from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.drugtemplates.models import DrugTemplate
from apps.outpatientprescriptions.models import OutpatientPrescription
from apps.patients.models import Patient

User = get_user_model()


def grant_event_permissions(user, *codenames):
    """Grant the given events app permissions to a user.

    The test database does not seed the profession groups' permissions, so
    view tests must grant the exact Django permissions enforced by
    PermissionRequiredMixin.
    """
    perms = Permission.objects.filter(
        content_type__app_label="events", codename__in=codenames
    )
    user.user_permissions.add(*perms)


class PrescriptionPermissionTestCase(TestCase):
    """Base test case for prescription permission tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for permission tests."""
        # Create users with different professions (lifecycle gates cleared so
        # the core middleware does not redirect view requests).
        cls.doctor = User.objects.create_user(
            username="doctor",
            email="doctor@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
            first_name="Dr. John",
            last_name="Smith",
        )

        cls.resident = User.objects.create_user(
            username="resident",
            email="resident@example.com",
            password="testpass123",
            profession_type=User.RESIDENT,
            password_change_required=False,
            terms_accepted=True,
            first_name="Dr. Jane",
            last_name="Doe",
        )

        cls.nurse = User.objects.create_user(
            username="nurse",
            email="nurse@example.com",
            password="testpass123",
            profession_type=User.NURSE,
            password_change_required=False,
            terms_accepted=True,
            first_name="Nurse",
            last_name="Johnson",
        )

        cls.physiotherapist = User.objects.create_user(
            username="physio",
            email="physio@example.com",
            password="testpass123",
            profession_type=User.PHYSIOTERAPIST,
            password_change_required=False,
            terms_accepted=True,
            first_name="Physio",
            last_name="Wilson",
        )

        cls.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="testpass123",
            profession_type=User.STUDENT,
            password_change_required=False,
            terms_accepted=True,
            first_name="Student",
            last_name="Brown",
        )

        # Grant the Django permissions enforced by the prescription views:
        # doctors manage events, residents/physiotherapists create them;
        # nurses and students have no event-management permissions.
        grant_event_permissions(cls.doctor, "add_event", "change_event", "delete_event")
        grant_event_permissions(cls.resident, "add_event")
        grant_event_permissions(cls.physiotherapist, "add_event")

        # Note: Hospital entities removed after single-hospital refactor

        # Create patients with different statuses
        cls.outpatient = Patient.objects.create(
            name="Outpatient",
            birthday="1990-01-01",
            status=1,  # Outpatient
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.inpatient = Patient.objects.create(
            name="Inpatient",
            birthday="1985-05-15",
            status=2,  # Inpatient
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        # Create prescriptions
        cls.recent_prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="Recent prescription",
            instructions="Recent instructions",
            status="draft",
            prescription_date=timezone.localdate(),
            patient=cls.outpatient,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.old_prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now() - timedelta(days=30),
            description="Old prescription",
            instructions="Old instructions",
            status="finalized",
            prescription_date=timezone.localdate() - timedelta(days=30),
            patient=cls.outpatient,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()

    def _setup_session(self, user):
        """Helper method to set up user session."""
        self.client.login(username=user.username, password="testpass123")


class PatientAccessPermissionTest(PrescriptionPermissionTestCase):
    """Test patient access permissions for prescriptions."""

    @patch("apps.outpatientprescriptions.views.can_access_patient")
    def test_doctor_can_access_all_patients(self, mock_can_access):
        """Test that doctors can access all patients."""
        mock_can_access.return_value = True
        self._setup_session(self.doctor)

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_detail",
                kwargs={"pk": self.recent_prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        mock_can_access.assert_called_once()

    @patch("apps.outpatientprescriptions.views.can_access_patient")
    def test_resident_limited_patient_access(self, mock_can_access):
        """Test that residents have limited patient access."""
        mock_can_access.return_value = True  # Has access
        self._setup_session(self.resident)

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_detail",
                kwargs={"pk": self.recent_prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

        # Test no access scenario: the detail view raises PermissionDenied
        # when the user cannot access the patient, which maps to 403.
        mock_can_access.return_value = False
        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_detail",
                kwargs={"pk": self.recent_prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 403)

    @patch("apps.outpatientprescriptions.views.can_access_patient")
    def test_nurse_limited_patient_access(self, mock_can_access):
        """Test that nurses have limited patient access."""
        mock_can_access.return_value = True
        self._setup_session(self.nurse)

        # Nurses can view prescriptions but have limited edit access
        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_detail",
                kwargs={"pk": self.recent_prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.outpatientprescriptions.views.can_access_patient")
    def test_student_outpatient_only_access(self, mock_can_access):
        """Test that students can only access outpatients."""
        mock_can_access.return_value = True
        self._setup_session(self.student)

        # Students should be able to access outpatient prescriptions
        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_detail",
                kwargs={"pk": self.recent_prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.outpatientprescriptions.views.can_access_patient")
    def test_no_patient_access_returns_403(self, mock_can_access):
        """Test that users without patient access get 403."""
        mock_can_access.return_value = False
        self._setup_session(self.doctor)

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_detail",
                kwargs={"pk": self.recent_prescription.pk},
            )
        )
        # The detail view deliberately raises PermissionDenied when the user
        # cannot access the patient (established view contract).
        self.assertEqual(response.status_code, 403)


class EventEditPermissionTest(PrescriptionPermissionTestCase):
    """Test event edit permissions for prescriptions."""

    @patch("apps.core.permissions.decorators.can_edit_event")
    def test_creator_can_edit_recent_prescription(self, mock_can_edit):
        """Test that creators can edit recent prescriptions."""
        mock_can_edit.return_value = True
        self._setup_session(self.doctor)

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_update",
                kwargs={"pk": self.recent_prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        mock_can_edit.assert_called_once()

    @patch("apps.core.permissions.decorators.can_edit_event")
    def test_cannot_edit_old_prescription(self, mock_can_edit):
        """Test that old prescriptions cannot be edited (24-hour rule)."""
        mock_can_edit.return_value = False  # Simulate 24-hour rule violation
        self._setup_session(self.doctor)

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_update",
                kwargs={"pk": self.old_prescription.pk},
            )
        )
        # can_edit_event_required denies with HttpResponseForbidden (403).
        self.assertEqual(response.status_code, 403)

    @patch("apps.core.permissions.decorators.can_edit_event")
    def test_non_creator_cannot_edit(self, mock_can_edit):
        """Test that non-creators cannot edit prescriptions."""
        mock_can_edit.return_value = False
        self._setup_session(self.resident)

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_update",
                kwargs={"pk": self.recent_prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 403)

    @patch("apps.core.permissions.decorators.can_edit_event")
    def test_nurse_cannot_edit_prescriptions(self, mock_can_edit):
        """Test that nurses cannot edit prescriptions."""
        mock_can_edit.return_value = False
        self._setup_session(self.nurse)

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_update",
                kwargs={"pk": self.recent_prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 403)

    @patch("apps.core.permissions.decorators.can_edit_event")
    def test_student_cannot_edit_prescriptions(self, mock_can_edit):
        """Test that students cannot edit prescriptions."""
        mock_can_edit.return_value = False
        self._setup_session(self.student)

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_update",
                kwargs={"pk": self.recent_prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 403)


class EventDeletePermissionTest(PrescriptionPermissionTestCase):
    """Test event delete permissions for prescriptions."""

    @patch("apps.outpatientprescriptions.views.can_delete_event")
    def test_creator_can_delete_recent_prescription(self, mock_can_delete):
        """Test that creators can delete recent prescriptions."""
        mock_can_delete.return_value = True
        self._setup_session(self.doctor)

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_delete",
                kwargs={"pk": self.recent_prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        mock_can_delete.assert_called_once()

    @patch("apps.outpatientprescriptions.views.can_delete_event")
    def test_cannot_delete_old_prescription(self, mock_can_delete):
        """Test that old prescriptions cannot be deleted (24-hour rule)."""
        mock_can_delete.return_value = False
        self._setup_session(self.doctor)

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_delete",
                kwargs={"pk": self.old_prescription.pk},
            )
        )
        # The delete view raises PermissionDenied in get_object() (403).
        self.assertEqual(response.status_code, 403)

    @patch("apps.outpatientprescriptions.views.can_delete_event")
    def test_non_creator_cannot_delete(self, mock_can_delete):
        """Test that non-creators cannot delete prescriptions."""
        mock_can_delete.return_value = False
        self._setup_session(self.resident)

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_delete",
                kwargs={"pk": self.recent_prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_successful_deletion_workflow(self):
        """Test successful deletion workflow (real permission logic)."""
        self._setup_session(self.doctor)

        # Create a prescription to delete
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="Prescription to delete",
            instructions="Test instructions",
            status="draft",
            prescription_date=timezone.localdate(),
            patient=self.outpatient,
            created_by=self.doctor,
            updated_by=self.doctor,
        )

        prescription_id = prescription.id

        # Delete the prescription (creator + recent => can_delete_event True)
        response = self.client.post(
            reverse(
                "outpatientprescriptions:outpatientprescription_delete",
                kwargs={"pk": prescription.pk},
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            OutpatientPrescription.objects.filter(id=prescription_id).exists()
        )


class PrescriptionCreationPermissionTest(PrescriptionPermissionTestCase):
    """Test prescription creation permissions."""

    def test_doctor_can_create_prescriptions(self):
        """Test that doctors can create prescriptions."""
        self._setup_session(self.doctor)

        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_create")
        )
        self.assertEqual(response.status_code, 200)

    def test_resident_can_create_prescriptions(self):
        """Test that residents can create prescriptions."""
        self._setup_session(self.resident)

        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_create")
        )
        self.assertEqual(response.status_code, 200)

    def test_physiotherapist_can_create_prescriptions(self):
        """Test that physiotherapists can create prescriptions."""
        self._setup_session(self.physiotherapist)

        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_create")
        )
        self.assertEqual(response.status_code, 200)

    def test_nurse_cannot_create_prescriptions(self):
        """Test that nurses cannot create prescriptions."""
        self._setup_session(self.nurse)

        # The create view requires the events.add_event permission
        # (PermissionRequiredMixin) -> 403 for users without it.
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_create")
        )
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_create_prescriptions(self):
        """Test that students cannot create prescriptions."""
        self._setup_session(self.student)

        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_create")
        )
        self.assertEqual(response.status_code, 403)


# NOTE: HospitalContextPermissionTest removed - hospital context functionality
# no longer exists after single-hospital refactor


class DrugTemplateAccessPermissionTest(PrescriptionPermissionTestCase):
    """Test drug template access permissions in prescription context."""

    @classmethod
    def setUpTestData(cls):
        """Set up drug template test data."""
        super().setUpTestData()

        # Create drug templates with different visibility (presentation is a
        # computed property since migration 0004).
        cls.public_template = DrugTemplate.objects.create(
            name="Public Drug",
            concentration="10mg",
            pharmaceutical_form="tablet",
            usage_instructions="Take 1 daily",
            creator=cls.doctor,
            is_public=True,
        )

        cls.private_template_doctor = DrugTemplate.objects.create(
            name="Private Drug Doctor",
            concentration="20mg",
            pharmaceutical_form="tablet",
            usage_instructions="Take 2 daily",
            creator=cls.doctor,
            is_public=False,
        )

        cls.private_template_resident = DrugTemplate.objects.create(
            name="Private Drug Resident",
            concentration="30mg",
            pharmaceutical_form="tablet",
            usage_instructions="Take 3 daily",
            creator=cls.resident,
            is_public=False,
        )

    def _search_as(self, user, query):
        """Search drug templates as the given user."""
        self._setup_session(user)
        return self.client.get(
            reverse("outpatientprescriptions:search_drug_templates"), {"q": query}
        )

    def _result_names(self, response):
        """Extract template names from an autocomplete search response."""
        payload = response.json()
        return [result["name"] for result in payload.get("results", [])]

    def test_public_template_searchable_by_all_users(self):
        """Test that all users can search public drug templates."""
        for user in [
            self.doctor,
            self.resident,
            self.nurse,
            self.physiotherapist,
            self.student,
        ]:
            response = self._search_as(user, "Public")
            self.assertEqual(response.status_code, 200, user.username)
            self.assertIn("Public Drug", self._result_names(response))

    def test_private_template_searchable_by_creator_only(self):
        """Test that private templates are only accessible to their creators."""
        # Doctor sees their own private template
        response = self._search_as(self.doctor, "Private Drug")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Private Drug Doctor", self._result_names(response))
        self.assertNotIn("Private Drug Resident", self._result_names(response))

        # Resident sees their own private template but not the doctor's
        response = self._search_as(self.resident, "Private Drug")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Private Drug Resident", self._result_names(response))
        self.assertNotIn("Private Drug Doctor", self._result_names(response))


class PrescriptionStatusPermissionTest(PrescriptionPermissionTestCase):
    """Test permissions related to prescription status changes."""

    def test_finalized_prescription_immutable(self):
        """Test that prescriptions denied by the edit rule cannot be modified.

        The update view enforces the edit window via can_edit_event_required;
        a denial (24-hour rule / status immutability) maps to 403.
        """
        finalized_prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="Finalized prescription",
            instructions="Final instructions",
            status="finalized",
            prescription_date=timezone.localdate(),
            patient=self.outpatient,
            created_by=self.doctor,
            updated_by=self.doctor,
        )

        self._setup_session(self.doctor)

        with patch(
            "apps.core.permissions.decorators.can_edit_event", return_value=False
        ):
            response = self.client.get(
                reverse(
                    "outpatientprescriptions:outpatientprescription_update",
                    kwargs={"pk": finalized_prescription.pk},
                )
            )
            self.assertEqual(response.status_code, 403)

    def test_draft_prescription_editable(self):
        """Test that recent draft prescriptions can be modified (real logic)."""
        draft_prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="Draft prescription",
            instructions="Draft instructions",
            status="draft",
            prescription_date=timezone.localdate(),
            patient=self.outpatient,
            created_by=self.doctor,
            updated_by=self.doctor,
        )

        self._setup_session(self.doctor)

        # Doctor is the creator and the event is recent, so the edit decorator
        # and the events.change_event permission both pass.
        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_update",
                kwargs={"pk": draft_prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 200)


class PermissionIntegrationTest(PrescriptionPermissionTestCase):
    """Integration tests for permission scenarios."""

    def test_complete_permission_workflow(self):
        """Test complete workflow with permission checks at each step."""
        self._setup_session(self.doctor)

        # Step 1: Create prescription (should succeed for doctor)
        create_data = {
            "patient": self.outpatient.pk,
            "event_datetime": timezone.now(),
            "description": "Permission test prescription",
            "instructions": "Permission test instructions",
            "status": "draft",
            "prescription_date": timezone.localdate(),
            # Inline formset prefix derives from the FK related_name ('items')
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-drug_name": "Permission Test Drug",
            "items-0-presentation": "10mg tablet",
            "items-0-usage_instructions": "Take as needed",
            "items-0-quantity": "30",
            "items-0-order": "1",
        }

        response = self.client.post(
            reverse("outpatientprescriptions:outpatientprescription_create"),
            create_data,
        )
        self.assertEqual(response.status_code, 302)

        # The form derives description from the event type ('Receita'), so
        # identify the created object by instructions and creator.
        prescription = OutpatientPrescription.objects.get(
            instructions="Permission test instructions", created_by=self.doctor
        )

        # Step 2: View prescription (should succeed with patient access)
        with patch(
            "apps.outpatientprescriptions.views.can_access_patient", return_value=True
        ):
            response = self.client.get(
                reverse(
                    "outpatientprescriptions:outpatientprescription_detail",
                    kwargs={"pk": prescription.pk},
                )
            )
            self.assertEqual(response.status_code, 200)

        # Step 3: Edit prescription (should succeed with edit permission)
        with patch(
            "apps.core.permissions.decorators.can_edit_event", return_value=True
        ):
            response = self.client.get(
                reverse(
                    "outpatientprescriptions:outpatientprescription_update",
                    kwargs={"pk": prescription.pk},
                )
            )
            self.assertEqual(response.status_code, 200)

        # Step 4: Switch to different user (resident)
        self._setup_session(self.resident)

        # Step 5: Try to edit (should fail without permission)
        with patch(
            "apps.core.permissions.decorators.can_edit_event", return_value=False
        ):
            response = self.client.get(
                reverse(
                    "outpatientprescriptions:outpatientprescription_update",
                    kwargs={"pk": prescription.pk},
                )
            )
            self.assertEqual(response.status_code, 403)

        # Step 6: Switch to student
        self._setup_session(self.student)

        # Step 7: Try to view (should depend on patient access)
        with patch(
            "apps.outpatientprescriptions.views.can_access_patient", return_value=True
        ):
            response = self.client.get(
                reverse(
                    "outpatientprescriptions:outpatientprescription_detail",
                    kwargs={"pk": prescription.pk},
                )
            )
            self.assertEqual(response.status_code, 200)

        # Step 8: Try to create prescription as student (should fail)
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_create")
        )
        self.assertEqual(response.status_code, 403)

    def test_permission_edge_cases(self):
        """Test edge cases in permission logic."""
        self._setup_session(self.doctor)

        # Detail view for a non-existent prescription -> 404
        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_detail",
                kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
            )
        )
        self.assertEqual(response.status_code, 404)

        # Logged-out user is redirected to login
        self.client.logout()
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list")
        )
        self.assertRedirects(response, "/accounts/login/?next=/prescriptions/")
