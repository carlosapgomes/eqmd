"""S6 R1/R2: the OutpatientPrescription student-draft lifecycle.

Covers student creation persisting as a draft through the model backstop,
draft resolution in the detail/update/delete views with the bot-draft guard,
the draft versus finalize update actions with the server-side physician gate,
the clinical ``status`` staying orthogonal to supervision, and the post-final
owner window (design D5/D6/D11).
"""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import Patient

from ..models import OutpatientPrescription, PrescriptionItem

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class PrescriptionDraftLifecycleTests(TestCase):
    """R1: creation, draft resolution, finalize gate, owner window."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("rx-lifecycle-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "rx-lifecycle-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("rx-lifecycle-doctor", User.MEDICAL_DOCTOR)
        cls.other_doctor = create_profession_user(
            "rx-lifecycle-other-doctor", User.MEDICAL_DOCTOR
        )
        cls.patient = Patient.objects.create(
            name="Prescription Draft Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    def _create_prescription(
        self,
        *,
        author=None,
        is_draft=False,
        draft_created_by_bot="",
        status="draft",
        promoted_at=None,
        promoted_by=None,
    ):
        author = author or self.doctor
        prescription = OutpatientPrescription.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            prescription_date=timezone.localdate(),
            instructions="Uso oral.",
            status=status,
            is_draft=is_draft,
            draft_created_by_bot=draft_created_by_bot,
            draft_promoted_at=promoted_at,
            draft_promoted_by=promoted_by,
            description="Receita",
            created_by=author,
            # The finalizer is the acting user on an approved record (design D5).
            updated_by=promoted_by or author,
        )
        PrescriptionItem.objects.create(
            prescription=prescription,
            drug_name="Paracetamol",
            presentation="500mg comprimidos",
            usage_instructions="Tomar 1 comprimido de 8 em 8 horas.",
            quantity="21 comprimidos",
            order=1,
        )
        return prescription

    def _detail_url(self, prescription):
        return reverse(
            "outpatientprescriptions:outpatientprescription_detail",
            kwargs={"pk": prescription.pk},
        )

    def _update_url(self, prescription):
        return reverse(
            "outpatientprescriptions:outpatientprescription_update",
            kwargs={"pk": prescription.pk},
        )

    def _delete_url(self, prescription):
        return reverse(
            "outpatientprescriptions:outpatientprescription_delete",
            kwargs={"pk": prescription.pk},
        )

    def _update_post_data(self, prescription, **overrides):
        """Return the prescription form plus its inline item formset."""
        data = {
            "patient": prescription.patient.pk,
            "event_datetime": prescription.event_datetime.strftime("%Y-%m-%dT%H:%M"),
            "prescription_date": prescription.prescription_date.strftime("%Y-%m-%d"),
            "instructions": prescription.instructions,
            "status": prescription.status,
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "1",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-id": prescription.items.get().pk,
            "items-0-drug_name": "Paracetamol",
            "items-0-presentation": "500mg comprimidos",
            "items-0-usage_instructions": "Tomar 1 comprimido de 8 em 8 horas.",
            "items-0-quantity": "21 comprimidos",
            "items-0-order": "1",
        }
        data.update(overrides)
        return data

    def test_student_creation_persists_as_draft(self):
        """Regression (S1 backstop): a student creation form stores a draft."""
        self.client.force_login(self.student)

        response = self.client.post(
            reverse(
                "outpatientprescriptions:outpatientprescription_create_for_patient",
                kwargs={"patient_uuid": self.patient.pk},
            ),
            {
                "patient": self.patient.pk,
                "event_datetime": timezone.now().strftime("%Y-%m-%dT%H:%M"),
                "prescription_date": timezone.localdate().strftime("%Y-%m-%d"),
                "instructions": "Uso oral.",
                "status": "finalized",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "1",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-drug_name": "Paracetamol",
                "items-0-presentation": "500mg comprimidos",
                "items-0-usage_instructions": "Tomar 1 comprimido de 8 em 8 horas.",
                "items-0-quantity": "21 comprimidos",
                "items-0-order": "1",
            },
        )

        self.assertEqual(response.status_code, 302)
        prescription = OutpatientPrescription.all_objects.get(
            created_by=self.student, patient=self.patient
        )
        self.assertTrue(prescription.is_draft)

    def test_human_drafts_resolve_in_detail_update_and_delete(self):
        draft = self._create_prescription(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self._detail_url(draft)).status_code, 200)
            self.assertEqual(self.client.get(self._update_url(draft)).status_code, 200)
            self.assertEqual(self.client.get(self._delete_url(draft)).status_code, 200)

    def test_bot_drafts_stay_unreachable_through_normal_views(self):
        bot_draft = self._create_prescription(
            author=self.doctor,
            is_draft=True,
            draft_created_by_bot="bot-client-1",
        )
        self.client.force_login(self.doctor)

        self.assertEqual(self.client.get(self._detail_url(bot_draft)).status_code, 404)
        self.assertEqual(self.client.get(self._update_url(bot_draft)).status_code, 404)
        self.assertEqual(self.client.get(self._delete_url(bot_draft)).status_code, 404)

    def test_definitive_prescription_still_resolves(self):
        final = self._create_prescription(author=self.doctor)
        self.client.force_login(self.doctor)

        self.assertEqual(self.client.get(self._detail_url(final)).status_code, 200)
        self.assertEqual(self.client.get(self._update_url(final)).status_code, 200)
        self.assertEqual(self.client.get(self._delete_url(final)).status_code, 200)

    def test_physician_finalize_flips_state_and_keeps_clinical_status(self):
        """R1: finalize records the approver and leaves clinical status alone."""
        draft = self._create_prescription(
            author=self.student, is_draft=True, status="draft"
        )
        self.client.force_login(self.doctor)

        response = self.client.post(
            self._update_url(draft),
            # A crafted/hand-edited submission cannot smuggle a clinical status
            # change into the approval: the persisted status wins (R1/D11).
            self._update_post_data(draft, save_final="1", status="finalized"),
        )

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertFalse(draft.is_draft)
        self.assertEqual(draft.draft_promoted_by, self.doctor)
        self.assertIsNotNone(draft.draft_promoted_at)
        self.assertEqual(draft.created_by, self.student)
        self.assertEqual(draft.status, "draft")

    def test_clinical_status_change_does_not_approve_a_draft(self):
        """R1/D11: the clinical status action is not a supervision finalize."""
        draft = self._create_prescription(
            author=self.student, is_draft=True, status="draft"
        )
        self.client.force_login(self.doctor)

        response = self.client.post(
            self._update_url(draft),
            self._update_post_data(draft, status="finalized"),
        )

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)
        self.assertEqual(draft.status, "finalized")

    def test_student_finalize_attempt_is_denied(self):
        draft = self._create_prescription(author=self.student, is_draft=True)
        self.client.force_login(self.student)

        response = self.client.post(
            self._update_url(draft),
            self._update_post_data(draft, save_final="1"),
        )

        self.assertEqual(response.status_code, 403)
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)
        self.assertIsNone(draft.draft_promoted_by)

    def test_saving_a_draft_keeps_it_a_draft(self):
        draft = self._create_prescription(author=self.student, is_draft=True)
        self.client.force_login(self.student)

        response = self.client.post(
            self._update_url(draft),
            self._update_post_data(
                draft, save_draft="1", instructions="Uso oral, após refeições."
            ),
        )

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)
        self.assertIsNone(draft.draft_promoted_by)
        self.assertEqual(draft.instructions, "Uso oral, após refeições.")

    def test_student_author_is_locked_out_after_approval(self):
        final = self._create_prescription(
            author=self.student,
            promoted_at=timezone.now(),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.student)

        self.assertEqual(self.client.get(self._update_url(final)).status_code, 403)
        self.assertEqual(self.client.get(self._delete_url(final)).status_code, 403)

    def test_finalizer_keeps_the_window(self):
        final = self._create_prescription(
            author=self.student,
            promoted_at=timezone.now(),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.doctor)

        self.assertEqual(self.client.get(self._update_url(final)).status_code, 200)

    def test_finalizer_window_expires_after_24_hours(self):
        final = self._create_prescription(
            author=self.student,
            promoted_at=timezone.now() - timedelta(hours=25),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.doctor)

        self.assertEqual(self.client.get(self._update_url(final)).status_code, 403)

    def test_non_finalizer_physician_is_locked_out_after_approval(self):
        final = self._create_prescription(
            author=self.student,
            promoted_at=timezone.now(),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.other_doctor)

        self.assertEqual(self.client.get(self._update_url(final)).status_code, 403)

    def test_update_template_offers_finalize_action_to_physicians(self):
        draft = self._create_prescription(author=self.student, is_draft=True)

        self.client.force_login(self.doctor)
        response = self.client.get(self._update_url(draft))

        self.assertTrue(response.context["is_draft_prescription"])
        self.assertTrue(response.context["can_finalize"])
        self.assertContains(response, 'name="save_final"')
        self.assertContains(response, 'name="save_draft"')

    def test_update_template_offers_only_the_draft_action_to_students(self):
        draft = self._create_prescription(author=self.student, is_draft=True)

        self.client.force_login(self.student)
        response = self.client.get(self._update_url(draft))

        self.assertTrue(response.context["is_draft_prescription"])
        self.assertFalse(response.context["can_finalize"])
        self.assertNotContains(response, 'name="save_final"')
        self.assertContains(response, 'name="save_draft"')

    def test_definitive_update_template_has_no_draft_actions(self):
        final = self._create_prescription(author=self.doctor)

        self.client.force_login(self.doctor)
        response = self.client.get(self._update_url(final))

        self.assertFalse(response.context["is_draft_prescription"])
        self.assertNotContains(response, 'name="save_final"')
        self.assertNotContains(response, 'name="save_draft"')
