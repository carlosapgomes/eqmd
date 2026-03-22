from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.events.models import Event
from apps.patients.models import Patient
from apps.simplenotes.models import SimpleNote

User = get_user_model()


class SimpleNoteViewTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            username="simplenote-view-creator",
            email="creator@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            terms_accepted_at=timezone.now(),
        )
        self.other_user = User.objects.create_user(
            username="simplenote-view-other",
            email="other@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            terms_accepted_at=timezone.now(),
        )
        self.patient = Patient.objects.create(
            name="View Test Patient",
            birthday="1990-01-01",
            status=1,
            fiscal_number="98765432100",
            created_by=self.creator,
            updated_by=self.creator,
        )

    def _grant_event_permissions(self, user, *codenames):
        permissions = Permission.objects.filter(
            content_type__app_label="events", codename__in=codenames
        )
        user.user_permissions.add(*permissions)

    def test_create_simplenote_for_accessible_patient(self):
        self._grant_event_permissions(self.creator, "add_event")
        self.assertTrue(self.creator.has_perm("events.add_event"))
        self.client.force_login(self.creator)

        url = reverse(
            "simplenotes:patient_simplenote_create",
            kwargs={"patient_pk": self.patient.pk},
        )
        event_datetime = (timezone.now() - timezone.timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M"
        )

        response = self.client.post(
            url,
            data={
                "event_datetime": event_datetime,
                "content": "Conteúdo de teste suficiente para criação da nota.",
            },
        )

        self.assertEqual(response.status_code, 302)
        note = SimpleNote.objects.get(patient=self.patient)
        self.assertEqual(note.created_by, self.creator)
        self.assertEqual(note.event_type, Event.SIMPLE_NOTE_EVENT)

    def test_update_simplenote_allowed_for_creator_within_window(self):
        self._grant_event_permissions(self.creator, "change_event")
        self.assertTrue(self.creator.has_perm("events.change_event"))
        note = SimpleNote.objects.create(
            patient=self.patient,
            description="Nota/Observação",
            content="Conteúdo inicial da nota para edição.",
            event_datetime=timezone.now(),
            created_by=self.creator,
            updated_by=self.creator,
        )

        self.client.force_login(self.creator)
        url = reverse("simplenotes:simplenote_update", kwargs={"pk": note.pk})
        response = self.client.post(
            url,
            data={
                "event_datetime": (
                    timezone.now() - timezone.timedelta(days=1)
                ).strftime("%Y-%m-%dT%H:%M"),
                "content": "Conteúdo atualizado da nota com tamanho válido.",
            },
        )

        self.assertEqual(response.status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.content, "Conteúdo atualizado da nota com tamanho válido.")

    def test_delete_simplenote_denied_when_permission_fails(self):
        self._grant_event_permissions(self.other_user, "delete_event")
        self.assertTrue(self.other_user.has_perm("events.delete_event"))
        note = SimpleNote.objects.create(
            patient=self.patient,
            description="Nota/Observação",
            content="Conteúdo para teste de deleção negada.",
            event_datetime=timezone.now(),
            created_by=self.creator,
            updated_by=self.creator,
        )

        self.client.force_login(self.other_user)
        url = reverse("simplenotes:simplenote_delete", kwargs={"pk": note.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)
