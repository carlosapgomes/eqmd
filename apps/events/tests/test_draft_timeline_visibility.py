"""S2 R1: human drafts in the patient timeline (design D9).

The timeline shows human drafts to every user with patient access, marks them
with a badge carrying their age and a distinct tint, and offers a drafts-only
filter. Bot drafts keep their own promotion path and stay out of the timeline.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.patients.models import Patient
from apps.simplenotes.models import SimpleNote

User = get_user_model()


class DraftTimelineVisibilityTests(TestCase):
    """R1: badge, tint, age, drafts-only filter and bot-draft exclusion."""

    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(
            username="drafttimelinestudent",
            email="drafttimelinestudent@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.STUDENT,
        )
        cls.doctor = User.objects.create_user(
            username="drafttimelinedoctor",
            email="drafttimelinedoctor@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        cls.patient = Patient.objects.create(
            name="Draft Timeline Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def _create_note(
        self,
        *,
        description,
        author=None,
        is_draft=False,
        draft_created_by_bot="",
        created_at=None,
    ):
        author = author or self.doctor
        note = SimpleNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description=description,
            content=f"Conteúdo de {description}",
            is_draft=is_draft,
            draft_created_by_bot=draft_created_by_bot,
            created_by=author,
            updated_by=author,
        )
        if created_at is not None:
            SimpleNote.all_objects.filter(pk=note.pk).update(created_at=created_at)
            note.refresh_from_db()
        return note

    def _timeline(self, user, **params):
        self.client.force_login(user)
        return self.client.get(
            reverse(
                "apps.patients:patient_events_timeline",
                kwargs={"patient_id": self.patient.pk},
            ),
            params,
        )

    @staticmethod
    def _html(response):
        # ``timesince`` separates the number and the unit with a non-breaking
        # space under the pt-BR locale; normalise it for readable assertions.
        return response.content.decode().replace("\xa0", " ")

    def test_human_draft_appears_for_any_user_with_patient_access(self):
        draft = self._create_note(
            description="Rascunho do aluno", author=self.student, is_draft=True
        )

        response = self._timeline(self.doctor)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"event-{draft.pk}-title")

    def test_draft_card_shows_badge_with_age(self):
        self._create_note(
            description="Rascunho antigo",
            author=self.student,
            is_draft=True,
            created_at=timezone.now() - timedelta(days=5),
        )

        html = self._html(self._timeline(self.doctor))

        self.assertIn("draft-badge", html)
        self.assertIn("Rascunho", html)
        self.assertIn("há 5 dias", html)

    def test_draft_card_uses_distinct_tint(self):
        self._create_note(
            description="Rascunho tingido", author=self.student, is_draft=True
        )

        html = self._html(self._timeline(self.doctor))

        self.assertIn("card-medical mb-3 timeline-card-draft", html)

    def test_final_card_has_no_draft_badge_nor_tint(self):
        self._create_note(description="Nota definitiva")

        html = self._html(self._timeline(self.doctor))

        self.assertNotIn("card-medical mb-3 timeline-card-draft", html)
        self.assertNotIn("draft-badge", html)

    def test_bot_draft_stays_hidden(self):
        bot_draft = self._create_note(
            description="Rascunho do bot",
            author=self.student,
            is_draft=True,
            draft_created_by_bot="bot-client-1",
        )

        response = self._timeline(self.doctor)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, f"event-{bot_draft.pk}-title")

    def test_drafts_only_filter_limits_the_timeline(self):
        draft = self._create_note(
            description="Rascunho filtrado", author=self.student, is_draft=True
        )
        final = self._create_note(description="Nota filtrada")

        response = self._timeline(self.doctor, drafts_only="1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"event-{draft.pk}-title")
        self.assertNotContains(response, f"event-{final.pk}-title")

    def test_filter_form_offers_drafts_only_control(self):
        response = self._timeline(self.doctor)

        self.assertContains(response, 'name="drafts_only"')
