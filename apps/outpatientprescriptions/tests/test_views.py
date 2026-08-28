from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.events.models import Event
from apps.outpatientprescriptions.forms.prescription_forms import (
    OutpatientPrescriptionForm,
)
from apps.outpatientprescriptions.models import OutpatientPrescription, PrescriptionItem

# Note: Hospital model removed after single-hospital refactor
from apps.patients.models import Patient
from apps.sample_content.models import SampleContent

User = get_user_model()


def grant_event_permissions(user, *codenames):
    """Grant the given events app permissions to a user.

    The test database does not seed the profession groups' permissions, so
    view tests must grant the exact Django permissions enforced by
    PermissionRequiredMixin on the create/update/delete views.
    """
    perms = Permission.objects.filter(
        content_type__app_label="events", codename__in=codenames
    )
    user.user_permissions.add(*perms)


class OutpatientPrescriptionListViewTest(TestCase):
    """Test cases for OutpatientPrescriptionListView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        # Lifecycle gates cleared so the core middleware does not redirect
        # (NavigationReadyUserFactory contract).
        cls.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )

        cls.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.user1,
            updated_by=cls.user1,
        )

        # Create prescriptions
        cls.prescription1 = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="Prescription 1",
            instructions="Instructions 1",
            status="draft",
            prescription_date=timezone.localdate(),
            patient=cls.patient,
            created_by=cls.user1,
            updated_by=cls.user1,
        )

        cls.prescription2 = OutpatientPrescription.objects.create(
            event_datetime=timezone.now() - timedelta(days=1),
            description="Prescription 2",
            instructions="Instructions 2",
            status="finalized",
            prescription_date=timezone.localdate() - timedelta(days=1),
            patient=cls.patient,
            created_by=cls.user2,
            updated_by=cls.user2,
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username="user1", password="testpass123")

    def test_view_url_accessible_by_name(self):
        """Test that view is accessible by name."""
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list")
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list")
        )
        self.assertTemplateUsed(
            response, "outpatientprescriptions/outpatientprescription_list.html"
        )

    def test_view_shows_accessible_prescriptions(self):
        """Test that view shows only accessible prescriptions."""
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list")
        )
        prescriptions = response.context["prescriptions"]

        # Single-hospital configuration: all authenticated users can access
        # all patients, so both prescriptions are visible.
        self.assertIn(self.prescription1, prescriptions)
        self.assertIn(self.prescription2, prescriptions)

    def test_view_search_functionality(self):
        """Test search functionality (instructions, patient name, item drug
        name are the searched fields; description is not)."""
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list"),
            {"search": "Instructions 1"},
        )
        prescriptions = response.context["prescriptions"]

        # Should find prescription1 by instructions
        self.assertIn(self.prescription1, prescriptions)
        self.assertNotIn(self.prescription2, prescriptions)

        # Description-only search matches nothing (current search contract)
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list"),
            {"search": "Prescription 1"},
        )
        self.assertNotIn(self.prescription1, response.context["prescriptions"])

    def test_view_patient_filter(self):
        """Test patient filter functionality."""
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list"),
            {"patient": str(self.patient.id)},
        )
        prescriptions = response.context["prescriptions"]

        # Should show prescriptions for the specific patient
        for prescription in prescriptions:
            self.assertEqual(prescription.patient, self.patient)

    def test_view_status_filter(self):
        """Test status filter functionality."""
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list"),
            {"status": "draft"},
        )
        prescriptions = response.context["prescriptions"]

        # Should show only draft prescriptions
        for prescription in prescriptions:
            self.assertEqual(prescription.status, "draft")

    def test_view_date_range_filter(self):
        """Test date range filter functionality (date_from/date_to params)."""
        start_date = timezone.localdate() - timedelta(days=1)
        end_date = timezone.localdate()

        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list"),
            {
                "date_from": start_date.strftime("%Y-%m-%d"),
                "date_to": end_date.strftime("%Y-%m-%d"),
            },
        )
        prescriptions = response.context["prescriptions"]

        # Should show prescriptions within date range
        for prescription in prescriptions:
            self.assertTrue(start_date <= prescription.prescription_date <= end_date)

    def test_view_pagination(self):
        """Test pagination functionality."""
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list")
        )
        self.assertIn("is_paginated", response.context)
        self.assertIn("page_obj", response.context)

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list")
        )
        self.assertRedirects(response, "/accounts/login/?next=/prescriptions/")

    @patch("apps.core.permissions.cache.get_user_accessible_patients")
    def test_view_respects_patient_access_permissions(self, mock_accessible):
        """Test that view respects patient access permissions."""
        mock_accessible.return_value = []

        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list")
        )
        prescriptions = response.context["prescriptions"]

        # Should show empty queryset if no patient access
        self.assertEqual(len(prescriptions), 0)


class OutpatientPrescriptionDetailViewTest(TestCase):
    """Test cases for OutpatientPrescriptionDetailView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )

        cls.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.user1,
            updated_by=cls.user1,
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="Test Prescription",
            instructions="Test instructions",
            status="draft",
            prescription_date=timezone.localdate(),
            patient=cls.patient,
            created_by=cls.user1,
            updated_by=cls.user1,
        )

        # Add prescription items
        PrescriptionItem.objects.create(
            prescription=cls.prescription,
            drug_name="Drug A",
            presentation="10mg tablet",
            usage_instructions="Take 1 daily",
            quantity="30",
            order=1,
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username="user1", password="testpass123")

    @patch("apps.outpatientprescriptions.views.can_access_patient")
    def test_view_accessible_with_patient_access(self, mock_can_access):
        """Test that view is accessible when user has patient access."""
        mock_can_access.return_value = True

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_detail",
                kwargs={"pk": self.prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["prescription"], self.prescription)

    @patch("apps.outpatientprescriptions.views.can_access_patient")
    def test_view_not_accessible_without_patient_access(self, mock_can_access):
        """Test that view is not accessible without patient access."""
        mock_can_access.return_value = False

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_detail",
                kwargs={"pk": self.prescription.pk},
            )
        )
        # The detail view deliberately raises PermissionDenied in get_object()
        # when the user cannot access the patient (403).
        self.assertEqual(response.status_code, 403)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        with patch(
            "apps.outpatientprescriptions.views.can_access_patient", return_value=True
        ):
            response = self.client.get(
                reverse(
                    "outpatientprescriptions:outpatientprescription_detail",
                    kwargs={"pk": self.prescription.pk},
                )
            )
            self.assertTemplateUsed(
                response, "outpatientprescriptions/outpatientprescription_detail.html"
            )

    def test_view_shows_prescription_items(self):
        """Test that view shows prescription items."""
        with patch(
            "apps.outpatientprescriptions.views.can_access_patient", return_value=True
        ):
            response = self.client.get(
                reverse(
                    "outpatientprescriptions:outpatientprescription_detail",
                    kwargs={"pk": self.prescription.pk},
                )
            )
            prescription = response.context["prescription"]
            self.assertEqual(prescription.items.count(), 1)

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_detail",
                kwargs={"pk": self.prescription.pk},
            )
        )
        self.assertRedirects(
            response, f"/accounts/login/?next=/prescriptions/{self.prescription.pk}/"
        )


class OutpatientPrescriptionCreateViewTest(TestCase):
    """Test cases for OutpatientPrescriptionCreateView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        # The create view requires the events.add_event permission
        grant_event_permissions(cls.user, "add_event")

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.user,
            updated_by=cls.user,
        )

        # Create sample content
        cls.sample_content = SampleContent.objects.create(
            title="Sample Prescription Content",
            content="Sample prescription instructions",
            event_type=Event.OUTPT_PRESCRIPTION_EVENT,
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_view_accessible_to_authenticated_users(self):
        """Test that view is accessible to authenticated users."""
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_create")
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_create")
        )
        self.assertTemplateUsed(
            response, "outpatientprescriptions/outpatientprescription_create.html"
        )

    def test_view_uses_correct_form(self):
        """Test that view uses correct form class."""
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_create")
        )
        self.assertIsInstance(response.context["form"], OutpatientPrescriptionForm)

    def test_view_provides_formset_context(self):
        """Test that view provides formset in context."""
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_create")
        )
        self.assertIn("formset", response.context)
        self.assertIn("management_form", response.context)
        self.assertIn("empty_form", response.context)
        self.assertIn("can_delete", response.context)

    def test_view_provides_drug_templates_context(self):
        """Test that view provides drug/prescription template context.

        The current create view exposes drug_templates and
        prescription_templates (sample content is not part of the view
        context contract).
        """
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_create")
        )
        self.assertIn("drug_templates", response.context)
        self.assertIn("prescription_templates", response.context)
        self.assertNotIn("sample_contents", response.context)

    def test_post_creates_prescription_with_items(self):
        """Test that POST request creates prescription with items."""
        form_data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now(),
            "description": "Test prescription creation",
            "instructions": "Take all medications as prescribed",
            "status": "draft",
            "prescription_date": timezone.localdate(),
            # Inline formset prefix derives from the FK related_name ('items')
            "items-TOTAL_FORMS": "2",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-drug_name": "Paracetamol",
            "items-0-presentation": "500mg comprimidos",
            "items-0-usage_instructions": "Tomar 1 comprimido de 8 em 8 horas",
            "items-0-quantity": "21 comprimidos",
            "items-0-order": "1",
            "items-1-drug_name": "Ibuprofeno",
            "items-1-presentation": "400mg comprimidos",
            "items-1-usage_instructions": "Tomar 1 comprimido se dor",
            "items-1-quantity": "10 comprimidos",
            "items-1-order": "2",
        }

        response = self.client.post(
            reverse("outpatientprescriptions:outpatientprescription_create"), form_data
        )

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Check that prescription was created. The form derives description
        # from the event type ('Receita'), so identify the object by the
        # instructions and creator instead.
        prescription = OutpatientPrescription.objects.get(
            instructions="Take all medications as prescribed", created_by=self.user
        )
        self.assertEqual(prescription.description, "Receita")
        self.assertEqual(prescription.created_by, self.user)
        self.assertEqual(prescription.items.count(), 2)

    def test_post_invalid_form_shows_errors(self):
        """Test that POST with invalid data shows form errors."""
        form_data = {
            "patient": "",  # Missing required field
            "description": "Test prescription",
            "instructions": "Test instructions",
            # Valid formset data
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-drug_name": "Paracetamol",
            "items-0-presentation": "500mg comprimidos",
            "items-0-usage_instructions": "Tomar 1 comprimido de 8 em 8 horas",
            "items-0-quantity": "21 comprimidos",
            "items-0-order": "1",
        }

        response = self.client.post(
            reverse("outpatientprescriptions:outpatientprescription_create"), form_data
        )

        # Should stay on form page
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "patient", ["Este campo é obrigatório."]
        )

    def test_post_invalid_formset_shows_errors(self):
        """Test that POST with invalid formset shows errors."""
        form_data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now(),
            "description": "Test prescription",
            "instructions": "Test instructions",
            "status": "draft",
            "prescription_date": timezone.localdate(),
            # Invalid formset data - missing required fields
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-drug_name": "",  # Missing required field
            "items-0-presentation": "",  # Missing required field
            "items-0-usage_instructions": "",  # Missing required field
            "items-0-quantity": "",  # Missing required field
            "items-0-order": "1",
        }

        response = self.client.post(
            reverse("outpatientprescriptions:outpatientprescription_create"), form_data
        )

        # Should stay on form page
        self.assertEqual(response.status_code, 200)

        # Check that formset has errors
        formset = response.context["formset"]
        self.assertFalse(formset.is_valid())

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_create")
        )
        self.assertRedirects(response, "/accounts/login/?next=/prescriptions/create/")


class OutpatientPrescriptionUpdateViewTest(TestCase):
    """Test cases for OutpatientPrescriptionUpdateView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        # The update view requires the events.change_event permission
        grant_event_permissions(cls.user1, "change_event")

        cls.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.user1,
            updated_by=cls.user1,
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="Test Prescription",
            instructions="Test instructions",
            status="draft",
            prescription_date=timezone.localdate(),
            patient=cls.patient,
            created_by=cls.user1,
            updated_by=cls.user1,
        )

        # Add prescription item
        cls.item = PrescriptionItem.objects.create(
            prescription=cls.prescription,
            drug_name="Drug A",
            presentation="10mg tablet",
            usage_instructions="Take 1 daily",
            quantity="30",
            order=1,
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username="user1", password="testpass123")

    @patch("apps.core.permissions.decorators.can_edit_event")
    def test_view_accessible_with_edit_permission(self, mock_can_edit):
        """Test that view is accessible when user has edit permission."""
        mock_can_edit.return_value = True

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_update",
                kwargs={"pk": self.prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.core.permissions.decorators.can_edit_event")
    def test_view_not_accessible_without_edit_permission(self, mock_can_edit):
        """Test that view is not accessible without edit permission."""
        mock_can_edit.return_value = False

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_update",
                kwargs={"pk": self.prescription.pk},
            )
        )
        # can_edit_event_required denies with HttpResponseForbidden (403).
        self.assertEqual(response.status_code, 403)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        with patch(
            "apps.core.permissions.decorators.can_edit_event", return_value=True
        ):
            response = self.client.get(
                reverse(
                    "outpatientprescriptions:outpatientprescription_update",
                    kwargs={"pk": self.prescription.pk},
                )
            )
            self.assertTemplateUsed(
                response, "outpatientprescriptions/outpatientprescription_update.html"
            )

    @patch("apps.core.permissions.decorators.can_edit_event")
    def test_post_updates_prescription(self, mock_can_edit):
        """Test that POST request updates prescription."""
        mock_can_edit.return_value = True

        form_data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now(),
            "description": "Updated prescription description",
            "instructions": "Updated instructions",
            "status": "finalized",
            "prescription_date": timezone.localdate(),
            # Inline formset prefix derives from the FK related_name ('items')
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "1",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-id": str(self.item.pk),
            "items-0-drug_name": "Updated Drug A",
            "items-0-presentation": "20mg tablet",
            "items-0-usage_instructions": "Take 2 daily",
            "items-0-quantity": "60",
            "items-0-order": "1",
        }

        response = self.client.post(
            reverse(
                "outpatientprescriptions:outpatientprescription_update",
                kwargs={"pk": self.prescription.pk},
            ),
            form_data,
        )

        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)

        # Check that prescription was updated. description is derived from the
        # event type by OutpatientPrescriptionForm.save() and cannot be set
        # through the form.
        self.prescription.refresh_from_db()
        self.assertEqual(self.prescription.description, "Receita")
        self.assertEqual(self.prescription.status, "finalized")

        # Check that item was updated
        self.item.refresh_from_db()
        self.assertEqual(self.item.drug_name, "Updated Drug A")

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_update",
                kwargs={"pk": self.prescription.pk},
            )
        )
        self.assertRedirects(
            response,
            f"/accounts/login/?next=/prescriptions/{self.prescription.pk}/edit/",
        )


class OutpatientPrescriptionDeleteViewTest(TestCase):
    """Test cases for OutpatientPrescriptionDeleteView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        # The delete view requires the events.delete_event permission
        grant_event_permissions(cls.user, "delete_event")

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

        # Create fresh prescription for each test
        self.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="Test Prescription",
            instructions="Test instructions",
            status="draft",
            prescription_date=timezone.localdate(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
        )

    @patch("apps.outpatientprescriptions.views.can_delete_event")
    def test_view_accessible_with_delete_permission(self, mock_can_delete):
        """Test that view is accessible when user has delete permission."""
        mock_can_delete.return_value = True

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_delete",
                kwargs={"pk": self.prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.outpatientprescriptions.views.can_delete_event")
    def test_view_not_accessible_without_delete_permission(self, mock_can_delete):
        """Test that view is not accessible without delete permission."""
        mock_can_delete.return_value = False

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_delete",
                kwargs={"pk": self.prescription.pk},
            )
        )
        # The delete view raises PermissionDenied in get_object() (403).
        self.assertEqual(response.status_code, 403)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        with patch(
            "apps.outpatientprescriptions.views.can_delete_event", return_value=True
        ):
            response = self.client.get(
                reverse(
                    "outpatientprescriptions:outpatientprescription_delete",
                    kwargs={"pk": self.prescription.pk},
                )
            )
            self.assertTemplateUsed(
                response,
                "outpatientprescriptions/outpatientprescription_confirm_delete.html",
            )

    def test_post_deletes_prescription(self):
        """Test that POST request deletes prescription (real permission logic)."""
        prescription_id = self.prescription.id

        response = self.client.post(
            reverse(
                "outpatientprescriptions:outpatientprescription_delete",
                kwargs={"pk": self.prescription.pk},
            )
        )

        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)

        # Check that prescription was deleted
        self.assertFalse(
            OutpatientPrescription.objects.filter(id=prescription_id).exists()
        )

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_delete",
                kwargs={"pk": self.prescription.pk},
            )
        )
        self.assertRedirects(
            response,
            f"/accounts/login/?next=/prescriptions/{self.prescription.pk}/delete/",
        )


class OutpatientPrescriptionPrintViewTest(TestCase):
    """Test cases for OutpatientPrescriptionPrintView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="Test Prescription for Print",
            instructions="Print test instructions",
            status="finalized",
            prescription_date=timezone.localdate(),
            patient=cls.patient,
            created_by=cls.user,
            updated_by=cls.user,
        )

        # Add prescription items
        PrescriptionItem.objects.create(
            prescription=cls.prescription,
            drug_name="Print Drug A",
            presentation="10mg tablet",
            usage_instructions="Take 1 daily for print test",
            quantity="30",
            order=1,
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    @patch("apps.outpatientprescriptions.views.can_access_patient")
    def test_view_accessible_with_patient_access(self, mock_can_access):
        """Test that view is accessible when user has patient access."""
        mock_can_access.return_value = True

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_print",
                kwargs={"pk": self.prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.outpatientprescriptions.views.can_access_patient")
    def test_view_not_accessible_without_patient_access(self, mock_can_access):
        """Test that view is not accessible without patient access."""
        mock_can_access.return_value = False

        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_print",
                kwargs={"pk": self.prescription.pk},
            )
        )
        # The print view raises PermissionDenied in get_object() (403).
        self.assertEqual(response.status_code, 403)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        with patch(
            "apps.outpatientprescriptions.views.can_access_patient", return_value=True
        ):
            response = self.client.get(
                reverse(
                    "outpatientprescriptions:outpatientprescription_print",
                    kwargs={"pk": self.prescription.pk},
                )
            )
            self.assertTemplateUsed(
                response, "outpatientprescriptions/outpatientprescription_print.html"
            )

    def test_view_shows_prescription_data(self):
        """Test that view shows prescription data for printing."""
        with patch(
            "apps.outpatientprescriptions.views.can_access_patient", return_value=True
        ):
            response = self.client.get(
                reverse(
                    "outpatientprescriptions:outpatientprescription_print",
                    kwargs={"pk": self.prescription.pk},
                )
            )

            prescription = response.context["prescription"]
            self.assertEqual(prescription, self.prescription)
            self.assertEqual(prescription.items.count(), 1)

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_print",
                kwargs={"pk": self.prescription.pk},
            )
        )
        self.assertRedirects(
            response,
            f"/accounts/login/?next=/prescriptions/{self.prescription.pk}/print/",
        )


class ViewIntegrationTest(TestCase):
    """Integration tests for view workflows."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        # The CRUD workflow exercises all three event permissions
        grant_event_permissions(cls.user, "add_event", "change_event", "delete_event")

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_complete_prescription_crud_workflow(self):
        """Test complete CRUD workflow for prescriptions."""
        # Create
        create_data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now(),
            "description": "Workflow Test Prescription",
            "instructions": "Complete workflow test instructions",
            "status": "draft",
            "prescription_date": timezone.localdate(),
            # Inline formset prefix derives from the FK related_name ('items')
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-drug_name": "Workflow Drug",
            "items-0-presentation": "10mg tablet",
            "items-0-usage_instructions": "Take 1 daily for workflow test",
            "items-0-quantity": "30",
            "items-0-order": "1",
        }

        response = self.client.post(
            reverse("outpatientprescriptions:outpatientprescription_create"),
            create_data,
        )
        self.assertEqual(response.status_code, 302)

        # Get the created prescription (description is derived by the form)
        prescription = OutpatientPrescription.objects.get(
            instructions="Complete workflow test instructions", created_by=self.user
        )

        # Read (Detail view)
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
            self.assertEqual(response.context["prescription"], prescription)

        # Update
        update_data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now(),
            "description": "Updated Workflow Test Prescription",
            "instructions": "Updated workflow test instructions",
            "status": "finalized",
            "prescription_date": timezone.localdate(),
            # Formset data for existing item
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "1",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-id": str(prescription.items.first().pk),
            "items-0-drug_name": "Updated Workflow Drug",
            "items-0-presentation": "20mg tablet",
            "items-0-usage_instructions": "Take 2 daily for updated workflow test",
            "items-0-quantity": "60",
            "items-0-order": "1",
        }

        with patch(
            "apps.core.permissions.decorators.can_edit_event", return_value=True
        ):
            response = self.client.post(
                reverse(
                    "outpatientprescriptions:outpatientprescription_update",
                    kwargs={"pk": prescription.pk},
                ),
                update_data,
            )
            self.assertEqual(response.status_code, 302)

        # Verify update (description stays derived; status changed)
        prescription.refresh_from_db()
        self.assertEqual(prescription.description, "Receita")
        self.assertEqual(prescription.status, "finalized")

        # Print view
        with patch(
            "apps.outpatientprescriptions.views.can_access_patient", return_value=True
        ):
            response = self.client.get(
                reverse(
                    "outpatientprescriptions:outpatientprescription_print",
                    kwargs={"pk": prescription.pk},
                )
            )
            self.assertEqual(response.status_code, 200)

        # Delete
        with patch(
            "apps.outpatientprescriptions.views.can_delete_event", return_value=True
        ):
            response = self.client.post(
                reverse(
                    "outpatientprescriptions:outpatientprescription_delete",
                    kwargs={"pk": prescription.pk},
                )
            )
            self.assertEqual(response.status_code, 302)

        # Verify deletion
        self.assertFalse(
            OutpatientPrescription.objects.filter(id=prescription.id).exists()
        )

    @patch("apps.outpatientprescriptions.views.can_access_patient")
    def test_prescription_list_to_detail_workflow(self, mock_can_access):
        """Test workflow from list view to detail view."""
        mock_can_access.return_value = True

        # Create prescription
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="List to Detail Test",
            instructions="Test instructions",
            status="draft",
            prescription_date=timezone.localdate(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
        )

        # Test list view
        response = self.client.get(
            reverse("outpatientprescriptions:outpatientprescription_list")
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(prescription, response.context["prescriptions"])

        # Test detail view
        response = self.client.get(
            reverse(
                "outpatientprescriptions:outpatientprescription_detail",
                kwargs={"pk": prescription.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["prescription"], prescription)
