"""Batch 3-up download for exam-request batches (chequinho) — S2.

GET ``exam-batch/download/<batch_id>/`` composes every *final* submission
carrying ``batch_id`` into one A4 PDF with up to 3 vias per sheet at 100%
(fixed crop top 1.0 cm / base 10.0 cm, dashed cut lines only between
printed vias). Drafts never compose: a draft-only batch 404s, mirroring
the single download, and each final submission enforces its own
``check_pdf_download_access``.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.views import View

from ..models import PDFFormSubmission
from ..permissions import check_pdf_download_access
from ..security import PDFFormSecurity
from ..services.exam_batch_imposition import compose_exam_batch
from ..services.pdf_overlay import PDFFormOverlay

logger = logging.getLogger(__name__)


def get_batch_final_submissions(batch_id):
    """Return final submissions of a batch in deterministic slot order.

    The default manager hides drafts, so drafts never enter the
    composition. Ordering by ``(created_at, pk)`` keeps exam N at
    ``slot=(N-1)%3`` of ``sheet=(N-1)//3`` across downloads.
    """
    return list(
        PDFFormSubmission.objects.filter(form_data__batch_id=str(batch_id))
        .select_related("patient", "form_template")
        .order_by("created_at", "pk")
    )


class ExamBatchDownloadView(LoginRequiredMixin, View):
    """Download a whole exam batch composed 3-up on A4 (S2)."""

    def get(self, request, batch_id):
        submissions = get_batch_final_submissions(batch_id)

        if not submissions:
            raise Http404("Batch not found")

        # Per-submission gating, mirroring PDFFormDownloadView.
        for submission in submissions:
            check_pdf_download_access(request.user, submission)
            if not submission.form_template or not submission.form_template.pdf_file:
                raise Http404("PDF template not found")

        try:
            for submission in submissions:
                PDFFormSecurity.validate_file_path(
                    submission.form_template.pdf_file.path
                )
        except ValidationError as e:
            raise PermissionDenied(f"Security validation failed: {e!s}")

        try:
            overlay = PDFFormOverlay()
            vias = [
                overlay.render_filled_pdf_bytes(
                    submission.form_template.pdf_file.path,
                    submission.form_data,
                    submission.form_template.form_fields,
                )
                for submission in submissions
            ]
            pdf_bytes = compose_exam_batch(vias)
        except FileNotFoundError as e:
            raise Http404(f"Template file not found: {e!s}")
        except Exception as e:  # noqa: BLE001 - view error path
            logger.error(
                "Batch PDF generation failed for batch %s: %s", batch_id, e
            )
            raise Http404("Erro ao gerar PDF. Tente novamente ou contacte o suporte.")

        template_name = submissions[0].form_template.name
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = PDFFormSecurity.generate_secure_filename(
            f"lote_{template_name}_{timestamp}.pdf", prefix="pdf_form_"
        )

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = len(pdf_bytes)
        return response
