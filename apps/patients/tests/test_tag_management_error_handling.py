from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.events.models import TagAddedEvent

from ..models import AllowedTag, Patient, Tag

User = get_user_model()


class TagManagementErrorHandlingTests(TestCase):
    """Error paths for tag add/remove/bulk operations and their payloads."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = create_navigation_user(
            username='doctor',
            email='doctor@example.com',
            password='testpass123',
        )
        change_perm = Permission.objects.get(codename='change_patient')
        cls.doctor.user_permissions.add(change_perm)

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365 * 30),
            status=Patient.Status.OUTPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.other_patient = Patient.objects.create(
            name='Other Patient',
            birthday=timezone.now().date() - timedelta(days=365 * 30),
            status=Patient.Status.OUTPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.tag = AllowedTag.objects.create(
            name='Test Tag',
            color='#007bff',
            is_active=True,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        self.client.force_login(self.doctor)

    def _add_url(self):
        return reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': self.patient.id},
        )

    def test_add_tag_to_nonexistent_patient(self):
        """Adding a tag to an unknown patient UUID is a 404."""
        url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': '00000000-0000-0000-0000-000000000000'},
        )
        response = self.client.post(url, {'tag_id': str(self.tag.id)})

        self.assertEqual(response.status_code, 404)

    def test_remove_tag_from_nonexistent_patient(self):
        """Removing a tag from an unknown patient UUID is a 404."""
        url = reverse(
            'patients:patient_tag_remove',
            kwargs={
                'patient_id': '00000000-0000-0000-0000-000000000000',
                'tag_id': '00000000-0000-0000-0000-000000000001',
            },
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_add_nonexistent_tag(self):
        """An AllowedTag id that no longer exists is a domain 404."""
        dummy = AllowedTag.objects.create(
            name='Dummy Tag',
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        missing_id = dummy.pk
        dummy.delete()

        response = self.client.post(
            self._add_url(),
            {'tag_id': str(missing_id)},
        )

        self.assertEqual(response.status_code, 404)

    def test_remove_nonexistent_tag(self):
        """Removing a tag UUID that matches nothing is a 404."""
        url = reverse(
            'patients:patient_tag_remove',
            kwargs={
                'patient_id': self.patient.id,
                'tag_id': '00000000-0000-0000-0000-000000000001',
            },
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_remove_tag_not_assigned_to_patient(self):
        """A tag assigned to another patient cannot be removed: 404."""
        Tag.objects.create(
            patient=self.other_patient,
            allowed_tag=self.tag,
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        tag_instance = self.other_patient.patient_tags.get(allowed_tag=self.tag)
        url = reverse(
            'patients:patient_tag_remove',
            kwargs={
                'patient_id': self.patient.id,
                'tag_id': tag_instance.id,
            },
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_add_inactive_tag(self):
        """An inactive AllowedTag is rejected with a domain 400."""
        self.tag.is_active = False
        self.tag.save()

        response = self.client.post(
            self._add_url(),
            {'tag_id': str(self.tag.id)},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'Não é possível adicionar esta tag ao paciente',
        )

    def test_add_duplicate_tag(self):
        """A second add of the same AllowedTag is a domain 400."""
        Tag.objects.create(
            patient=self.patient,
            allowed_tag=self.tag,
            created_by=self.doctor,
            updated_by=self.doctor,
        )

        response = self.client.post(
            self._add_url(),
            {'tag_id': str(self.tag.id)},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'Não é possível adicionar esta tag ao paciente',
        )

    def test_bulk_remove_no_tags(self):
        """Bulk remove with zero tags is a domain 400 with exact payload."""
        url = reverse(
            'patients:patient_tag_remove_all',
            kwargs={'patient_id': self.patient.id},
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'Nenhuma tag para remover',
        )

    def test_bulk_remove_with_tags_success(self):
        """Bulk remove clears every tag and returns an empty list."""
        Tag.objects.create(
            patient=self.patient,
            allowed_tag=self.tag,
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        url = reverse(
            'patients:patient_tag_remove_all',
            kwargs={'patient_id': self.patient.id},
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['tags'], [])
        self.assertFalse(self.patient.patient_tags.exists())

    def test_add_tag_without_ajax_succeeds(self):
        """The add endpoint has no AJAX gate: plain POSTs succeed."""
        response = self.client.post(
            self._add_url(),
            {'tag_id': str(self.tag.id)},
        )

        self.assertEqual(response.status_code, 200)

    def test_remove_tag_without_ajax_succeeds(self):
        """The remove endpoint has no AJAX gate: plain POSTs succeed."""
        Tag.objects.create(
            patient=self.patient,
            allowed_tag=self.tag,
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        tag_instance = self.patient.patient_tags.get(allowed_tag=self.tag)
        url = reverse(
            'patients:patient_tag_remove',
            kwargs={
                'patient_id': self.patient.id,
                'tag_id': tag_instance.id,
            },
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)

    def test_permission_denied_error_format(self):
        """Without change_patient the request fails with 403 before the view."""
        no_permission_user = create_navigation_user(
            username='noperm',
            email='noperm@example.com',
            password='testpass123',
        )
        self.client.force_login(no_permission_user)

        response = self.client.post(
            self._add_url(),
            {'tag_id': str(self.tag.id)},
        )

        self.assertEqual(response.status_code, 403)
        # PermissionRequiredMixin raises before JSON handling: HTML body.
        self.assertIn('text/html', response['Content-Type'])

    def test_api_invalid_patient_id(self):
        """The tags API for an unknown patient UUID is a 404."""
        url = reverse(
            'patients:patient_tags_api',
            kwargs={'patient_id': '00000000-0000-0000-0000-000000000000'},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_database_error_handling(self):
        """Unexpected failures return a JSON 500 with the exact payload."""
        original_create = Tag.objects.create

        def mock_create(*args, **kwargs):
            raise RuntimeError('Database connection error')

        Tag.objects.create = mock_create
        try:
            response = self.client.post(
                self._add_url(),
                {'tag_id': str(self.tag.id)},
            )
        finally:
            Tag.objects.create = original_create

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()['error'],
            'Erro interno do servidor',
        )

    def test_event_creation_failure(self):
        """Failure while writing the timeline event yields a JSON 500."""
        original_create = TagAddedEvent.objects.create

        def mock_create(*args, **kwargs):
            raise RuntimeError('Event creation failed')

        TagAddedEvent.objects.create = mock_create
        try:
            response = self.client.post(
                self._add_url(),
                {'tag_id': str(self.tag.id)},
            )
        finally:
            TagAddedEvent.objects.create = original_create

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()['error'],
            'Erro interno do servidor',
        )

    def test_missing_tag_id_parameter(self):
        """A POST without tag_id is a domain 400 with exact payload."""
        response = self.client.post(self._add_url(), {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'ID da tag é obrigatório',
        )
