"""S3: batch actions on the timeline and detail (chequinho).

Covers R1 (batch button on every card of a batch), R2 (single button
unchanged), R3 (no batch button for singles), R4 (detail banner with
download + siblings), R5 (bulk batch_info in one grouped query).
"""

import uuid

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.events.views import get_pdf_batch_info
from apps.pdf_forms.models import PDFFormSubmission

from .factories import PatientFactory, PDFFormTemplateFactory

User = get_user_model()


def make_template(user, name="Chequinho S3"):
    return PDFFormTemplateFactory(
        name=name,
        created_by=user,
        form_fields={
            "examRequested": {"type": "text", "required": False, "label": "Exame"},
        },
    )


def exam_form_data(n, batch_id=None):
    data = {
        "requestReason": "Dor no peito",
        "examRequested": f"EXAME-{n:02d} HEMOGRAMA",
        "examCode": "",
    }
    if batch_id is not None:
        data["batch_id"] = batch_id
    return data


class ExamBatchTimelineActionsTests(TestCase):
    """R1/R2/R3/R5 through the patient timeline page."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = create_navigation_user(
            username="batch-action-doctor",
            email="batch-action-doctor@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
        )
        cls.patient = PatientFactory(created_by=cls.doctor, updated_by=cls.doctor)
        cls.template = make_template(cls.doctor)

    def setUp(self):
        cache.clear()

    def _create_submission(self, n, batch_id=None, is_draft=False):
        return PDFFormSubmission.objects.create(
            form_template=self.template,
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor,
            event_datetime=timezone.now(),
            description=f"Exame {n}",
            form_data=exam_form_data(n, batch_id),
            is_draft=is_draft,
        )

    def _create_batch(self, count, draft_indices=frozenset(), batch_id=None):
        batch_id = batch_id or str(uuid.uuid4())
        submissions = [
            self._create_submission(n, batch_id, is_draft=(n in draft_indices))
            for n in range(1, count + 1)
        ]
        return batch_id, submissions

    def _timeline_html(self):
        self.client.force_login(self.doctor)
        response = self.client.get(
            reverse(
                "apps.patients:patient_events_timeline",
                kwargs={"patient_id": self.patient.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def _batch_url(self, batch_id):
        return reverse("pdf_forms:exam_batch_download", kwargs={"batch_id": batch_id})

    def test_batch_button_on_all_cards_of_the_batch(self):
        """R1: all N timeline cards link to the same batch download."""
        batch_id, _ = self._create_batch(3)
        html = self._timeline_html()
        self.assertEqual(html.count(self._batch_url(batch_id)), 3)
        self.assertIn("Baixar lote 3-up (3 vias)", html)

    def test_single_button_unchanged_for_finals_and_hidden_for_drafts(self):
        """R2: single download stays per-exam; drafts keep hiding it."""
        _batch_id, submissions = self._create_batch(2, draft_indices={2})
        final, draft = submissions
        single_url = reverse(
            "pdf_forms:pdf_download", kwargs={"submission_id": final.pk}
        )
        draft_single_url = reverse(
            "pdf_forms:pdf_download", kwargs={"submission_id": draft.pk}
        )
        html = self._timeline_html()
        self.assertIn(single_url, html)
        self.assertNotIn(draft_single_url, html)

    def test_no_batch_button_for_single_exams(self):
        """R3: submissions without batch_id show no batch button."""
        self._create_submission(1)
        html = self._timeline_html()
        self.assertNotIn("exam-batch/download", html)

    def test_no_batch_button_without_final_siblings(self):
        """R3: a lone final among drafts shows no batch button."""
        batch_id, _ = self._create_batch(2, draft_indices={2})
        html = self._timeline_html()
        self.assertNotIn(self._batch_url(batch_id), html)

    def test_batch_info_uses_a_single_grouped_query(self):
        """R5: bulk batch_info costs one query no matter the card count."""
        batch_id, submissions = self._create_batch(3)
        single = self._create_submission(4)
        events = list(
            PDFFormSubmission.objects.filter(
                pk__in=[s.pk for s in (*submissions, single)]
            )
        )
        with self.assertNumQueries(1):
            info = get_pdf_batch_info(events)
        self.assertEqual(
            {pk: (v["batch_id"], v["count"]) for pk, v in info.items()},
            {s.pk: (batch_id, 3) for s in submissions},
        )


class ExamBatchDetailBannerTests(TestCase):
    """R4 through the submission detail page."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = create_navigation_user(
            username="batch-banner-doctor",
            email="batch-banner-doctor@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
        )
        cls.patient = PatientFactory(created_by=cls.doctor, updated_by=cls.doctor)
        cls.template = make_template(cls.doctor, name="Chequinho S3 detalhe")

    def _create_submission(self, n, batch_id=None):
        return PDFFormSubmission.objects.create(
            form_template=self.template,
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor,
            event_datetime=timezone.now(),
            description=f"Exame {n}",
            form_data=exam_form_data(n, batch_id),
        )

    def _detail_html(self, submission):
        self.client.force_login(self.doctor)
        response = self.client.get(
            reverse("pdf_forms:submission_detail", kwargs={"pk": submission.pk})
        )
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_detail_banner_with_download_and_sibling_links(self):
        """R4: batch detail shows banner, batch download and siblings."""
        batch_id = str(uuid.uuid4())
        submissions = [self._create_submission(n, batch_id) for n in (1, 2, 3)]
        html = self._detail_html(submissions[0])
        self.assertIn("Parte do lote de 3 exames", html)
        self.assertIn(
            reverse("pdf_forms:exam_batch_download", kwargs={"batch_id": batch_id}),
            html,
        )
        for sibling in submissions[1:]:
            self.assertIn(
                reverse("pdf_forms:submission_detail", kwargs={"pk": sibling.pk}),
                html,
            )

    def test_detail_without_banner_for_single_exams(self):
        """R4: single-exam detail shows no batch banner."""
        submission = self._create_submission(1)
        html = self._detail_html(submission)
        self.assertNotIn("Parte do lote", html)
        self.assertNotIn("exam-batch/download", html)
