from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.events.models import TagAddedEvent

from ..models import AllowedTag, Patient, Tag

User = get_user_model()


class PatientTagErrorHandlingTests(TestCase):
    """Strict HTTP/error contracts for patient tag management endpoints."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_navigation_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        change_perm = Permission.objects.get(codename='change_patient')
        view_perm = Permission.objects.get(codename='view_patient')
        cls.user.user_permissions.add(change_perm, view_perm)

        cls.allowed_tag = AllowedTag.objects.create(
            name='Test Tag',
            color='#007bff',
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _create_patient(self, name='Error Test Patient'):
        return Patient.objects.create(
            name=name,
            birthday=timezone.now().date() - timedelta(days=365 * 30),
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_add_tag_with_missing_tag_id(self):
        """Missing tag_id is a domain 400 with the exact payload."""
        patient = self._create_patient()
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.post(add_url, data={'notes': 'Missing tag_id'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'ID da tag é obrigatório',
        )

    def test_add_tag_with_nonexistent_tag_id(self):
        """An integer tag_id that matches no AllowedTag is a 404.

        The view resolves the tag with get_object_or_404, so a missing
        AllowedTag id yields the domain 404.
        """
        patient = self._create_patient()
        dummy = AllowedTag.objects.create(
            name='Dummy Tag',
            created_by=self.user,
            updated_by=self.user,
        )
        missing_id = dummy.pk
        dummy.delete()
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.post(
            add_url,
            data={'tag_id': missing_id},
        )

        self.assertEqual(response.status_code, 404)

    def test_add_tag_with_malformed_tag_id(self):
        """A non-integer tag_id body is a malformed request: domain 400.

        AllowedTag.pk is an integer AutoField, so a non-integer body
        value is a bad request, not a missing resource.
        """
        patient = self._create_patient()
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.post(
            add_url,
            data={'tag_id': 'not-an-integer'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'ID da tag inválido',
        )

    def test_add_tag_with_inactive_tag_id(self):
        """Inactive AllowedTag is rejected with a domain 400 payload."""
        inactive_tag = AllowedTag.objects.create(
            name='Inactive Tag',
            color='#6c757d',
            is_active=False,
            created_by=self.user,
            updated_by=self.user,
        )
        patient = self._create_patient()
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.post(
            add_url,
            data={'tag_id': inactive_tag.pk, 'notes': 'Should fail'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'Não é possível adicionar esta tag ao paciente',
        )

    def test_add_tag_duplicate(self):
        """Assigning the same AllowedTag twice is a domain 400."""
        patient = self._create_patient()
        Tag.objects.create(
            patient=patient,
            allowed_tag=self.allowed_tag,
            created_by=self.user,
            updated_by=self.user,
        )
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.post(
            add_url,
            data={'tag_id': self.allowed_tag.pk},
        )

        self.assertEqual(response.status_code, 400)
        # can_add_patient_tag rejects duplicates before the view's own
        # existing_tag branch, so this is the authoritative payload.
        self.assertEqual(
            response.json()['error'],
            'Não é possível adicionar esta tag ao paciente',
        )

    def test_add_tag_success(self):
        """Valid add returns 200 with the refreshed tag list."""
        patient = self._create_patient()
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.post(
            add_url,
            data={'tag_id': self.allowed_tag.pk, 'notes': 'ok'},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['tags']), 1)
        self.assertEqual(data['tags'][0]['name'], 'Test Tag')
        self.assertTrue(
            patient.patient_tags.filter(allowed_tag=self.allowed_tag).exists()
        )

    def test_remove_tag_not_assigned_to_patient(self):
        """Removing a tag that belongs to another patient is a 404."""
        other_patient = self._create_patient(name='Other Patient')
        tag = Tag.objects.create(
            patient=other_patient,
            allowed_tag=self.allowed_tag,
            created_by=self.user,
            updated_by=self.user,
        )
        patient = self._create_patient(name='Remove Target Patient')
        remove_url = reverse(
            'patients:patient_tag_remove',
            kwargs={'patient_id': patient.pk, 'tag_id': tag.pk},
        )
        response = self.client.post(remove_url)

        self.assertEqual(response.status_code, 404)

    def test_remove_tag_success_then_second_remove_404(self):
        """Removing twice: first succeeds, second is a 404."""
        patient = self._create_patient()
        tag = Tag.objects.create(
            patient=patient,
            allowed_tag=self.allowed_tag,
            created_by=self.user,
            updated_by=self.user,
        )
        remove_url = reverse(
            'patients:patient_tag_remove',
            kwargs={'patient_id': patient.pk, 'tag_id': tag.pk},
        )

        first = self.client.post(remove_url)
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()['success'])
        self.assertFalse(patient.patient_tags.exists())

        second = self.client.post(remove_url)
        self.assertEqual(second.status_code, 404)

    def test_remove_all_tags_when_no_tags_exist(self):
        """Bulk remove with zero tags is a domain 400 with exact payload."""
        patient = self._create_patient()
        remove_all_url = reverse(
            'patients:patient_tag_remove_all',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.post(remove_all_url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'Nenhuma tag para remover',
        )

    def test_remove_all_tags_success(self):
        """Bulk remove clears every tag and returns an empty list."""
        patient = self._create_patient()
        Tag.objects.create(
            patient=patient,
            allowed_tag=self.allowed_tag,
            created_by=self.user,
            updated_by=self.user,
        )
        remove_all_url = reverse(
            'patients:patient_tag_remove_all',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.post(remove_all_url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['tags'], [])
        self.assertFalse(patient.patient_tags.exists())

    def test_api_nonexistent_patient(self):
        """Tags API for an unknown patient UUID is a 404."""
        api_url = reverse(
            'patients:patient_tags_api',
            kwargs={'patient_id': '00000000-0000-0000-0000-000000000000'},
        )
        response = self.client.get(api_url)

        self.assertEqual(response.status_code, 404)

    def test_api_success_json(self):
        """Tags API returns the documented JSON shape."""
        patient = self._create_patient()
        Tag.objects.create(
            patient=patient,
            allowed_tag=self.allowed_tag,
            created_by=self.user,
            updated_by=self.user,
        )
        api_url = reverse(
            'patients:patient_tags_api',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.get(api_url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['patient_id'], str(patient.pk))
        self.assertEqual(data['patient_name'], patient.name)
        self.assertEqual(len(data['current_tags']), 1)
        self.assertTrue(data['permissions']['can_manage_tags'])
        self.assertTrue(data['permissions']['can_view_tags'])

    def test_anonymous_user_redirects_to_login(self):
        """Anonymous access is redirected to login (auth contract)."""
        patient = self._create_patient()
        self.client.logout()
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.post(
            add_url,
            data={'tag_id': self.allowed_tag.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_permission_denied_without_change_permission(self):
        """A user without change_patient gets a 403 before the view runs."""
        limited_user = create_navigation_user(
            username='limiteduser',
            email='limited@example.com',
            password='testpass123',
        )
        patient = self._create_patient()
        self.client.force_login(limited_user)
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.post(
            add_url,
            data={'tag_id': self.allowed_tag.pk},
        )

        self.assertEqual(response.status_code, 403)
        # PermissionRequiredMixin raises before any JSON handling: HTML.
        self.assertIn('text/html', response['Content-Type'])

    def test_csrf_rejected_without_token(self):
        """POST without a CSRF token is rejected with 403."""
        patient = self._create_patient()
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(
            add_url,
            data={'tag_id': self.allowed_tag.pk},
        )

        self.assertEqual(response.status_code, 403)

    def test_malformed_patient_id_path_404(self):
        """A non-UUID patient_id never reaches the view: router 404."""
        response = self.client.post('/patients/not-a-uuid/tags/add/')

        self.assertEqual(response.status_code, 404)

    def test_malformed_tag_id_path_404(self):
        """A non-UUID tag_id in the remove path is a router 404."""
        patient = self._create_patient()
        response = self.client.post(
            f'/patients/{patient.pk}/tags/not-a-uuid/remove/'
        )

        self.assertEqual(response.status_code, 404)

    def test_long_notes_accepted(self):
        """Notes is unbounded text: very long values are accepted."""
        patient = self._create_patient()
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.post(
            add_url,
            data={'tag_id': self.allowed_tag.pk, 'notes': 'x' * 10000},
        )

        self.assertEqual(response.status_code, 200)

    def test_error_message_consistency(self):
        """Missing-tag_id error is a non-empty string with exact text."""
        patient = self._create_patient()
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        response = self.client.post(add_url, data={'notes': 'Missing tag_id'})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIsInstance(data['error'], str)
        self.assertEqual(data['error'], 'ID da tag é obrigatório')

    def test_database_error_returns_json_500(self):
        """Unexpected failures return a JSON 500 with the exact payload."""
        patient = self._create_patient()
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        original_create = Tag.objects.create

        def mock_create(*args, **kwargs):
            raise RuntimeError('Database connection error')

        Tag.objects.create = mock_create
        try:
            response = self.client.post(
                add_url,
                data={'tag_id': self.allowed_tag.pk},
            )
        finally:
            Tag.objects.create = original_create

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()['error'],
            'Erro interno do servidor',
        )

    def test_event_creation_failure_returns_json_500(self):
        """Failure while writing the timeline event still yields JSON 500."""
        patient = self._create_patient()
        add_url = reverse(
            'patients:patient_tag_add',
            kwargs={'patient_id': patient.pk},
        )
        original_create = TagAddedEvent.objects.create

        def mock_create(*args, **kwargs):
            raise RuntimeError('Event creation failed')

        TagAddedEvent.objects.create = mock_create
        try:
            response = self.client.post(
                add_url,
                data={'tag_id': self.allowed_tag.pk},
            )
        finally:
            TagAddedEvent.objects.create = original_create

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()['error'],
            'Erro interno do servidor',
        )

    def test_graceful_degradation_on_errors(self):
        """Detail page still renders the tag management UI and its JS hooks."""
        patient = self._create_patient()
        detail_url = reverse(
            'patients:patient_detail',
            kwargs={'pk': patient.pk},
        )
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gerenciamento de Tags')
        self.assertContains(response, 'showError')
        self.assertContains(response, 'showSuccess')
