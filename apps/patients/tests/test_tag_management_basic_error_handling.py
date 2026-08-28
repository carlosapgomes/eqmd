from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user

from ..models import AllowedTag, Patient

User = get_user_model()


class TagManagementBasicErrorHandlingTests(TestCase):
    """Basic tag endpoints: success flows and primary error contracts."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = create_navigation_user(
            username="doctor",
            email="doctor@example.com",
            password="testpass123",
        )
        change_perm = Permission.objects.get(codename="change_patient")
        cls.doctor.user_permissions.add(change_perm)

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday=timezone.now().date() - timedelta(days=365 * 30),
            status=Patient.Status.OUTPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.tag = AllowedTag.objects.create(
            name="Test Tag",
            color="#007bff",
            is_active=True,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        self.client.force_login(self.doctor)

    def _add_url(self):
        return reverse(
            "patients:patient_tag_add",
            kwargs={"patient_id": self.patient.id},
        )

    def test_add_tag_to_nonexistent_patient(self):
        """Adding a tag to an unknown patient UUID is a 404."""
        url = reverse(
            "patients:patient_tag_add",
            kwargs={"patient_id": "00000000-0000-0000-0000-000000000000"},
        )
        response = self.client.post(url, {"tag_id": str(self.tag.pk)})

        self.assertEqual(response.status_code, 404)

    def test_add_nonexistent_tag(self):
        """An AllowedTag id that no longer exists is a domain 404."""
        dummy = AllowedTag.objects.create(
            name="Dummy Tag",
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        missing_id = dummy.pk
        dummy.delete()

        response = self.client.post(
            self._add_url(),
            {"tag_id": str(missing_id)},
        )

        self.assertEqual(response.status_code, 404)

    def test_add_inactive_tag(self):
        """An inactive AllowedTag is rejected with a domain 400."""
        self.tag.is_active = False
        self.tag.save()

        response = self.client.post(
            self._add_url(),
            {"tag_id": str(self.tag.pk)},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "Não é possível adicionar esta tag ao paciente",
        )

    def test_add_duplicate_tag(self):
        """A second add of the same AllowedTag is a domain 400."""
        from ..models import Tag

        Tag.objects.create(
            patient=self.patient,
            allowed_tag=self.tag,
            created_by=self.doctor,
            updated_by=self.doctor,
        )

        response = self.client.post(
            self._add_url(),
            {"tag_id": str(self.tag.pk)},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "Não é possível adicionar esta tag ao paciente",
        )

    def test_add_tag_without_ajax_succeeds(self):
        """The add endpoint has no AJAX gate: plain POSTs succeed."""
        response = self.client.post(
            self._add_url(),
            {"tag_id": str(self.tag.pk)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_missing_tag_id_parameter(self):
        """A POST without tag_id is a domain 400 with exact payload."""
        response = self.client.post(self._add_url(), {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "ID da tag é obrigatório",
        )

    def test_successful_tag_add(self):
        """A valid add returns 200, the tag list, and persists the row."""
        response = self.client.post(
            self._add_url(),
            {"tag_id": str(self.tag.pk)},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tags", data)
        self.assertEqual(len(data["tags"]), 1)
        self.assertTrue(self.patient.patient_tags.filter(allowed_tag=self.tag).exists())

    def test_remove_existing_tag(self):
        """A valid remove returns 200 and deletes the row."""
        from ..models import Tag

        Tag.objects.create(
            patient=self.patient,
            allowed_tag=self.tag,
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        tag_instance = self.patient.patient_tags.get(allowed_tag=self.tag)
        url = reverse(
            "patients:patient_tag_remove",
            kwargs={
                "patient_id": self.patient.id,
                "tag_id": tag_instance.id,
            },
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("tags", response.json())
        self.assertFalse(
            self.patient.patient_tags.filter(allowed_tag=self.tag).exists()
        )

    def test_api_endpoint_returns_tags(self):
        """The tags API lists current tags with the documented shape."""
        from ..models import Tag

        Tag.objects.create(
            patient=self.patient,
            allowed_tag=self.tag,
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        url = reverse(
            "patients:patient_tags_api",
            kwargs={"patient_id": self.patient.id},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["current_tags"]), 1)
        self.assertEqual(data["current_tags"][0]["name"], self.tag.name)
