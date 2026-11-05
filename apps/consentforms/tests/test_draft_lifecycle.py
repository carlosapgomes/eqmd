"""S6 R3/R4: the ConsentForm student-draft lifecycle.

A student creation persists as a draft; drafts resolve in the detail/update/
delete views with the bot-draft guard; the update view handles finalize as an
action distinct from attachment upload (no files required, empty uploads stay
invalid); finalizing records the approver without touching the immutable
clinical content; and the model-level immutability check compares against a
draft-inclusive persisted row (design D5/D6/D12).
"""

from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.events.models import Event
from apps.patients.models import Patient

from ..models import ConsentAttachment, ConsentForm, ConsentTemplate

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class ConsentFormDraftLifecycleTests(TestCase):
    """R3/R4: creation, draft resolution, finalize, owner window, immutability."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("cf-lifecycle-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "cf-lifecycle-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("cf-lifecycle-doctor", User.MEDICAL_DOCTOR)
        cls.other_doctor = create_profession_user(
            "cf-lifecycle-other-doctor", User.MEDICAL_DOCTOR
        )
        cls.patient = Patient.objects.create(
            name="Consent Draft Patient",
            birthday="1990-01-01",
            current_record_number="RN987",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.template = ConsentTemplate.objects.create(
            name="Template de Teste",
            markdown_body=(
                "{{ patient_name }} {{ patient_record_number }} {{ document_date }}\n"
                "{{ procedure_description }}"
            ),
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    def _create_consent(
        self,
        *,
        author=None,
        is_draft=False,
        draft_created_by_bot="",
        promoted_at=None,
        promoted_by=None,
    ):
        author = author or self.doctor
        return ConsentForm.objects.create(
            template=self.template,
            patient=self.patient,
            document_date=date(2026, 1, 2),
            procedure_description="Procedimento de teste",
            rendered_markdown="Paciente Consent Draft Patient - Conteúdo imutável.",
            rendered_at=timezone.now(),
            event_datetime=timezone.now() - timedelta(hours=1),
            description="Termo de Consentimento - Template de Teste",
            event_type=Event.CONSENT_FORM_EVENT,
            is_draft=is_draft,
            draft_created_by_bot=draft_created_by_bot,
            draft_promoted_at=promoted_at,
            draft_promoted_by=promoted_by,
            created_by=author,
            # The finalizer is the acting user on an approved record (design D5).
            updated_by=promoted_by or author,
        )

    def _detail_url(self, consent):
        return reverse("consentforms:consentform_detail", kwargs={"pk": consent.pk})

    def _update_url(self, consent):
        return reverse("consentforms:consentform_update", kwargs={"pk": consent.pk})

    def _delete_url(self, consent):
        return reverse("consentforms:consentform_delete", kwargs={"pk": consent.pk})

    def test_student_creation_persists_as_draft(self):
        """Regression (S1 backstop): the consent creation form stores a draft."""
        self.client.force_login(self.student)

        response = self.client.post(
            reverse(
                "consentforms:consentform_create",
                kwargs={"patient_pk": self.patient.pk},
            ),
            {
                "template": str(self.template.pk),
                "document_date": timezone.localdate().strftime("%Y-%m-%d"),
                "procedure_description": "Procedimento criado pelo estudante",
            },
        )

        self.assertEqual(response.status_code, 302)
        consent = ConsentForm.all_objects.get(created_by=self.student)
        self.assertTrue(consent.is_draft)
        self.assertIn(self.patient.name, consent.rendered_markdown)

    def test_human_drafts_resolve_in_detail_update_and_delete(self):
        draft = self._create_consent(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self._detail_url(draft)).status_code, 200)
            self.assertEqual(self.client.get(self._update_url(draft)).status_code, 200)
            self.assertEqual(self.client.get(self._delete_url(draft)).status_code, 200)

    def test_bot_drafts_stay_unreachable_through_normal_views(self):
        bot_draft = self._create_consent(
            author=self.doctor,
            is_draft=True,
            draft_created_by_bot="bot-client-1",
        )
        self.client.force_login(self.doctor)

        self.assertEqual(self.client.get(self._detail_url(bot_draft)).status_code, 404)
        self.assertEqual(self.client.get(self._update_url(bot_draft)).status_code, 404)
        self.assertEqual(self.client.get(self._delete_url(bot_draft)).status_code, 404)

    def test_definitive_consent_still_resolves(self):
        final = self._create_consent(author=self.doctor)
        self.client.force_login(self.doctor)

        self.assertEqual(self.client.get(self._detail_url(final)).status_code, 200)
        self.assertEqual(self.client.get(self._update_url(final)).status_code, 200)
        self.assertEqual(self.client.get(self._delete_url(final)).status_code, 200)

    def test_physician_finalize_needs_no_files_and_keeps_content(self):
        """R3/D12: finalize is distinct from the attachment upload."""
        draft = self._create_consent(author=self.student, is_draft=True)
        attachment = ConsentAttachment.objects.create(
            consent_form=draft,
            file=SimpleUploadedFile(
                "page1.jpg", b"\xff\xd8\xff\xe0" + b"0" * 200, content_type="image/jpeg"
            ),
            original_filename="page1.jpg",
            file_size=204,
            mime_type="image/jpeg",
            file_type=ConsentAttachment.FILE_TYPE_IMAGE,
            order=1,
        )
        rendered_before = draft.rendered_markdown
        self.client.force_login(self.doctor)

        response = self.client.post(self._update_url(draft), {"save_final": "1"})

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertFalse(draft.is_draft)
        self.assertEqual(draft.draft_promoted_by, self.doctor)
        self.assertIsNotNone(draft.draft_promoted_at)
        self.assertEqual(draft.created_by, self.student)
        self.assertEqual(draft.rendered_markdown, rendered_before)
        self.assertEqual(draft.procedure_description, "Procedimento de teste")
        self.assertEqual(draft.document_date, date(2026, 1, 2))
        self.assertEqual(list(draft.attachments.all()), [attachment])

    def test_empty_attachment_upload_stays_invalid(self):
        """R3: an ordinary submission without files still fails validation."""
        draft = self._create_consent(author=self.student, is_draft=True)
        self.client.force_login(self.student)

        response = self.client.post(self._update_url(draft), {})

        self.assertEqual(response.status_code, 200)
        self.assertIn("Selecione pelo menos uma foto", response.content.decode())
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)

    def test_student_finalize_attempt_is_denied(self):
        draft = self._create_consent(author=self.student, is_draft=True)
        self.client.force_login(self.student)

        response = self.client.post(self._update_url(draft), {"save_final": "1"})

        self.assertEqual(response.status_code, 403)
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)
        self.assertIsNone(draft.draft_promoted_by)

    def test_draft_content_change_is_rejected_at_model_level(self):
        """R4: the immutability lookup now sees the persisted draft row."""
        draft = self._create_consent(author=self.student, is_draft=True)

        draft.rendered_markdown = "Conteúdo alterado depois do rascunho."

        with self.assertRaises(ValidationError):
            draft.save()

    def test_draft_metadata_update_keeps_the_content_check_satisfied(self):
        draft = self._create_consent(author=self.student, is_draft=True)

        draft.updated_by = self.doctor
        draft.save(update_fields=["updated_by", "updated_at"])

        draft.refresh_from_db()
        self.assertEqual(
            draft.rendered_markdown,
            "Paciente Consent Draft Patient - Conteúdo imutável.",
        )

    def test_student_author_is_locked_out_after_approval(self):
        final = self._create_consent(
            author=self.student,
            promoted_at=timezone.now(),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.student)

        self.assertEqual(self.client.get(self._update_url(final)).status_code, 403)
        self.assertEqual(self.client.get(self._delete_url(final)).status_code, 403)

    def test_finalizer_keeps_the_window(self):
        final = self._create_consent(
            author=self.student,
            promoted_at=timezone.now(),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.doctor)

        self.assertEqual(self.client.get(self._update_url(final)).status_code, 200)

    def test_finalizer_window_expires_after_24_hours(self):
        final = self._create_consent(
            author=self.student,
            promoted_at=timezone.now() - timedelta(hours=25),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.doctor)

        self.assertEqual(self.client.get(self._update_url(final)).status_code, 403)

    def test_non_finalizer_physician_is_locked_out_after_approval(self):
        final = self._create_consent(
            author=self.student,
            promoted_at=timezone.now(),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.other_doctor)

        self.assertEqual(self.client.get(self._update_url(final)).status_code, 403)

    def test_draft_update_template_offers_the_finalize_action_to_physicians(self):
        draft = self._create_consent(author=self.student, is_draft=True)

        self.client.force_login(self.doctor)
        response = self.client.get(self._update_url(draft))

        self.assertTrue(response.context["is_draft_consentform"])
        self.assertTrue(response.context["can_finalize"])
        self.assertContains(response, 'name="save_final"')

    def test_draft_update_template_hides_the_finalize_action_from_students(self):
        draft = self._create_consent(author=self.student, is_draft=True)

        self.client.force_login(self.student)
        response = self.client.get(self._update_url(draft))

        self.assertTrue(response.context["is_draft_consentform"])
        self.assertFalse(response.context["can_finalize"])
        self.assertNotContains(response, 'name="save_final"')
