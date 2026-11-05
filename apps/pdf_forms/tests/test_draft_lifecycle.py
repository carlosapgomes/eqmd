"""S6 R5/R6: PDF submission standard event semantics.

Covers the new in-place update views for hospital dynamic forms and APAC
capture (prefilled from the submission, same row, draft/finalize actions), the
``get_edit_url`` target, the draft-aware delete lookup, the AIH placeholder
regression, the APAC real round trip, and the removal of the unrouted
``can_edit_pdf_submission`` / ``can_delete_pdf_submission`` helpers.
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
from apps.core.models import Icd10Code, MedicalProcedure
from apps.patients.models import Patient

from .. import permissions as pdf_permissions
from ..models import PDFFormSubmission
from ..permissions import check_pdf_form_access
from .factories import PDFFormTemplateFactory

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class PDFSubmissionDraftLifecycleTests(TestCase):
    """R5/R6: hospital form update view, actions, AIH placeholder, helpers."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("pdf-lifecycle-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "pdf-lifecycle-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("pdf-lifecycle-doctor", User.MEDICAL_DOCTOR)
        cls.other_doctor = create_profession_user(
            "pdf-lifecycle-other-doctor", User.MEDICAL_DOCTOR
        )
        cls.patient = Patient.objects.create(
            name="PDF Draft Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.template = PDFFormTemplateFactory(
            name="Formulário Dinâmico de Teste",
            created_by=cls.doctor,
            form_fields={
                "notes": {
                    "type": "textarea",
                    "required": False,
                    "label": "Notas",
                },
                "priority": {
                    "type": "text",
                    "required": False,
                    "label": "Prioridade",
                },
            },
        )

    def setUp(self):
        cache.clear()

    def _create_submission(
        self,
        *,
        author=None,
        is_draft=False,
        draft_created_by_bot="",
        promoted_at=None,
        promoted_by=None,
        form_data=None,
        template=None,
        event_datetime=None,
    ):
        author = author or self.doctor
        return PDFFormSubmission.objects.create(
            form_template=template or self.template,
            patient=self.patient,
            created_by=author,
            # The finalizer is the acting user on an approved record (design D5).
            updated_by=promoted_by or author,
            event_datetime=event_datetime or (timezone.now() - timedelta(hours=1)),
            description="Formulário PDF de teste",
            form_data=form_data or {"notes": "Nota inicial", "priority": "Alta"},
            is_draft=is_draft,
            draft_created_by_bot=draft_created_by_bot,
            draft_promoted_at=promoted_at,
            draft_promoted_by=promoted_by,
        )

    def _update_url(self, submission):
        return reverse("pdf_forms:submission_update", kwargs={"pk": submission.pk})

    def _detail_url(self, submission):
        return reverse("pdf_forms:submission_detail", kwargs={"pk": submission.pk})

    def _form_data(self, **overrides):
        data = {"notes": "Nota inicial", "priority": "Alta"}
        data.update(overrides)
        return data

    def test_human_draft_resolves_in_the_update_view(self):
        draft = self._create_submission(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            self.client.force_login(user)
            response = self.client.get(self._update_url(draft))
            self.assertEqual(response.status_code, 200)

    def test_bot_draft_stays_unreachable_in_the_update_view(self):
        bot_draft = self._create_submission(
            author=self.doctor,
            is_draft=True,
            draft_created_by_bot="bot-client-1",
        )
        self.client.force_login(self.doctor)

        self.assertEqual(self.client.get(self._update_url(bot_draft)).status_code, 404)

    def test_update_view_prefills_from_the_submission(self):
        final = self._create_submission(author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.get(self._update_url(final))

        form = response.context["form"]
        self.assertEqual(form.initial["notes"], "Nota inicial")
        self.assertEqual(form.initial["priority"], "Alta")
        self.assertEqual(response.context["submission"], final)
        self.assertFalse(response.context["is_draft_submission"])

    def test_definitive_update_saves_the_same_row(self):
        """R5: a real update view for hospital dynamic forms (24h window)."""
        final = self._create_submission(author=self.doctor)
        submission_pk = final.pk
        self.client.force_login(self.doctor)

        response = self.client.post(
            self._update_url(final),
            self._form_data(notes="Nota corrigida", priority="Alta"),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            PDFFormSubmission.all_objects.filter(patient=self.patient).count(), 1
        )
        final.refresh_from_db()
        self.assertEqual(final.pk, submission_pk)
        self.assertEqual(final.form_data["notes"], "Nota corrigida")
        self.assertEqual(final.form_data["priority"], "Alta")
        self.assertEqual(final.updated_by, self.doctor)

    def test_definitive_update_window_expires_after_24_hours(self):
        final = self._create_submission(
            author=self.doctor,
            event_datetime=timezone.now() - timedelta(hours=25),
        )
        PDFFormSubmission.all_objects.filter(pk=final.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        self.client.force_login(self.doctor)

        self.assertEqual(self.client.get(self._update_url(final)).status_code, 403)

    def test_student_save_draft_keeps_the_draft(self):
        draft = self._create_submission(author=self.student, is_draft=True)
        self.client.force_login(self.student)

        response = self.client.post(
            self._update_url(draft),
            self._form_data(notes="Nota revisada pelo estudante", save_draft="1"),
        )

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)
        self.assertIsNone(draft.draft_promoted_by)
        self.assertEqual(draft.form_data["notes"], "Nota revisada pelo estudante")

    def test_physician_finalize_flips_state_and_records_approver(self):
        draft = self._create_submission(author=self.student, is_draft=True)
        self.client.force_login(self.doctor)

        response = self.client.post(
            self._update_url(draft),
            self._form_data(notes="Nota revisada pelo médico", save_final="1"),
        )

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertFalse(draft.is_draft)
        self.assertEqual(draft.draft_promoted_by, self.doctor)
        self.assertIsNotNone(draft.draft_promoted_at)
        self.assertEqual(draft.created_by, self.student)
        self.assertEqual(draft.form_data["notes"], "Nota revisada pelo médico")

    def test_student_finalize_attempt_is_denied(self):
        draft = self._create_submission(author=self.student, is_draft=True)
        self.client.force_login(self.student)

        response = self.client.post(
            self._update_url(draft), self._form_data(save_final="1")
        )

        self.assertEqual(response.status_code, 403)
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)
        self.assertIsNone(draft.draft_promoted_by)

    def test_student_author_is_locked_out_after_approval(self):
        final = self._create_submission(
            author=self.student,
            promoted_at=timezone.now(),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.student)

        self.assertEqual(self.client.get(self._update_url(final)).status_code, 403)

    def test_non_finalizer_physician_is_locked_out_after_approval(self):
        final = self._create_submission(
            author=self.student,
            promoted_at=timezone.now(),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.other_doctor)

        self.assertEqual(self.client.get(self._update_url(final)).status_code, 403)

    def test_superuser_gets_no_view_level_override(self):
        """R6: no superuser override survives the helper removal."""
        old_submission = self._create_submission(
            author=self.doctor,
            event_datetime=timezone.now() - timedelta(hours=25),
        )
        PDFFormSubmission.all_objects.filter(pk=old_submission.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        superuser = create_navigation_user(
            username="pdf-lifecycle-superuser",
            email="pdf-lifecycle-superuser@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(superuser)

        self.assertEqual(
            self.client.get(self._update_url(old_submission)).status_code, 403
        )

    def test_update_template_offers_the_draft_and_final_actions(self):
        draft = self._create_submission(author=self.student, is_draft=True)
        self.client.force_login(self.doctor)

        response = self.client.get(self._update_url(draft))

        self.assertTrue(response.context["is_draft_submission"])
        self.assertTrue(response.context["can_finalize"])
        self.assertContains(response, 'name="save_draft"')
        self.assertContains(response, 'name="save_final"')

    def test_update_template_hides_the_finalize_action_from_students(self):
        draft = self._create_submission(author=self.student, is_draft=True)
        self.client.force_login(self.student)

        response = self.client.get(self._update_url(draft))

        self.assertTrue(response.context["is_draft_submission"])
        self.assertFalse(response.context["can_finalize"])
        self.assertContains(response, 'name="save_draft"')
        self.assertNotContains(response, 'name="save_final"')

    def test_get_edit_url_points_to_the_update_view(self):
        draft = self._create_submission(author=self.student, is_draft=True)
        final = self._create_submission(author=self.doctor)

        self.assertEqual(self._update_url(draft), draft.get_edit_url())
        self.assertEqual(self._update_url(final), final.get_edit_url())
        self.assertNotEqual(self._detail_url(draft), draft.get_edit_url())

    def test_aih_placeholder_redirect_is_preserved(self):
        """R5 regression: the AIH route keeps its 'in development' redirect."""
        self.client.force_login(self.doctor)

        response = self.client.get(
            reverse("pdf_forms:aih_form", kwargs={"patient_id": self.patient.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("pdf_forms:form_select", kwargs={"patient_id": self.patient.pk}),
        )
        messages = [str(message) for message in response.wsgi_request._messages]
        self.assertTrue(any("em desenvolvimento" in message for message in messages))

    def test_dead_permission_helpers_are_removed(self):
        """R6: the unrouted helpers no longer exist on the permissions module."""
        self.assertFalse(hasattr(pdf_permissions, "can_edit_pdf_submission"))
        self.assertFalse(hasattr(pdf_permissions, "can_delete_pdf_submission"))
        # The remaining access helpers are still importable and enforced.
        self.assertTrue(callable(check_pdf_form_access))


class APACSubmissionDraftUpdateTests(TestCase):
    """R5: APAC capture gains the same in-place update flow (real round trip)."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("pdf-apac-student", User.STUDENT)
        cls.doctor = create_profession_user("pdf-apac-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="APAC Draft Patient",
            birthday="1985-05-05",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.template = PDFFormTemplateFactory(
            name="APAC - Formulário Nacional",
            form_type="APAC",
            hospital_specific=False,
            created_by=cls.doctor,
            form_fields={},
        )
        cls.main_procedure = MedicalProcedure.objects.create(
            code="PROC001", description="Procedimento Principal"
        )
        cls.main_icd = Icd10Code.objects.create(
            code="A000",
            description="Cólera devida a Vibrio cholerae",
            is_active=True,
        )

    def setUp(self):
        cache.clear()

    def _create_url(self):
        return reverse("pdf_forms:apac_form", kwargs={"patient_id": self.patient.pk})

    def _update_url(self, submission):
        return reverse(
            "pdf_forms:apac_submission_update", kwargs={"pk": submission.pk}
        )

    def _post_data(self, **overrides):
        data = {
            "patient_name": self.patient.name,
            "patient_gender": self.patient.get_gender_display(),
            "patient_birth_date": self.patient.birthday.isoformat(),
            "main_diagnosis": "Diagnóstico inicial",
            "main_procedure": str(self.main_procedure.pk),
            "main_procedure_display": (
                f"{self.main_procedure.code} - {self.main_procedure.description}"
            ),
            "main_procedure_quantity": "2",
            "main_icd_id": str(self.main_icd.pk),
            "main_icd_display": self.main_icd.code,
            "diagnosis_notes": "Observações iniciais",
            "doctor_name": "Dra. Teste",
            "doctor_doc_type_fiscal_number": "on",
            "doctor_doc_number_fiscal_number": "12345678900",
            "request_date": timezone.localdate().isoformat(),
        }
        data.update(overrides)
        return data

    def _create_submission(self):
        self.client.force_login(self.student)
        response = self.client.post(self._create_url(), self._post_data())
        self.assertEqual(response.status_code, 302)
        submission = PDFFormSubmission.all_objects.get(
            patient=self.patient, form_template=self.template
        )
        self.assertTrue(submission.is_draft)
        return submission

    def test_apac_student_creation_persists_as_draft(self):
        """Regression (S1 backstop + S3 grant): APAC creation stores a draft."""
        submission = self._create_submission()

        self.assertTrue(submission.is_draft)
        self.assertEqual(submission.created_by, self.student)

    def test_apac_update_round_trip_preserves_values_and_corrects(self):
        """R5: real round trip with prefill, identity and an effective fix."""
        submission = self._create_submission()
        submission_pk = submission.pk
        stored = dict(submission.form_data)
        self.client.force_login(self.doctor)

        # 1. The update screen prefills from the stored submission.
        response = self.client.get(self._update_url(submission))
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial["main_diagnosis"], stored["main_diagnosis"])
        self.assertEqual(
            str(form.initial["main_procedure"]), stored["main_procedure_id"]
        )
        self.assertEqual(
            form.initial["main_procedure_display"],
            f"{stored['main_procedure_code']} - {stored['main_procedure_description']}",
        )
        self.assertEqual(str(form.initial["main_icd_id"]), stored["main_icd_id"])
        self.assertEqual(form.initial["main_icd_display"], stored["main_icd_code"])
        self.assertEqual(
            form.initial["main_procedure_quantity"],
            stored["main_procedure_quantity"],
        )
        self.assertEqual(
            form.initial["doctor_doc_number_fiscal_number"],
            stored["doctor_doc_number_fiscal_number"],
        )

        # 2. Saving an effective correction updates the SAME row.
        response = self.client.post(
            self._update_url(submission),
            self._post_data(
                main_diagnosis="Diagnóstico corrigido",
                save_draft="1",
            ),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            PDFFormSubmission.all_objects.filter(patient=self.patient).count(), 1
        )
        submission.refresh_from_db()
        self.assertEqual(submission.pk, submission_pk)
        self.assertEqual(submission.created_by, self.student)
        self.assertEqual(submission.updated_by, self.doctor)
        self.assertTrue(submission.is_draft)

        updated = submission.form_data
        self.assertEqual(updated["main_diagnosis"], "Diagnóstico corrigido")
        # Untouched values survive the round trip.
        for key in (
            "patient_name",
            "patient_birth_date",
            "main_procedure_id",
            "main_procedure_code",
            "main_procedure_description",
            "main_procedure_quantity",
            "main_icd_id",
            "main_icd_code",
            "main_icd_description",
            "doctor_doc_number_fiscal_number",
            "request_date",
        ):
            self.assertEqual(updated[key], stored[key], key)

    def test_physician_finalizes_the_apac_draft(self):
        submission = self._create_submission()
        self.client.force_login(self.doctor)

        response = self.client.post(
            self._update_url(submission),
            self._post_data(
                main_diagnosis="Diagnóstico corrigido", save_final="1"
            ),
        )

        self.assertEqual(response.status_code, 302)
        submission.refresh_from_db()
        self.assertFalse(submission.is_draft)
        self.assertEqual(submission.draft_promoted_by, self.doctor)
        self.assertEqual(submission.created_by, self.student)

    def test_hospital_update_rejects_an_apac_submission(self):
        """The dynamic-form route cannot blank a national-form submission."""
        submission = self._create_submission()
        self.client.force_login(self.doctor)

        response = self.client.get(
            reverse("pdf_forms:submission_update", kwargs={"pk": submission.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_apac_update_rejects_a_hospital_submission(self):
        hospital_template = PDFFormTemplateFactory(
            name="Formulário Hospitalar",
            created_by=self.doctor,
            form_fields={},
        )
        hospital_submission = PDFFormSubmission.objects.create(
            form_template=hospital_template,
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor,
            event_datetime=timezone.now() - timedelta(hours=1),
            description="Formulário PDF hospitalar",
            form_data={"notes": "Nota"},
        )
        self.client.force_login(self.doctor)

        response = self.client.get(self._update_url(hospital_submission))

        self.assertEqual(response.status_code, 404)

    def test_apac_get_edit_url_points_to_the_apac_update_view(self):
        submission = self._create_submission()

        self.assertEqual(self._update_url(submission), submission.get_edit_url())
