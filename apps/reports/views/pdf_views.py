"""Views for report PDF download."""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View

from apps.core.permissions.utils import can_access_patient
from apps.reports.models import Report
from apps.reports.services.pdf_generator import ReportPDFGenerator


logger = logging.getLogger(__name__)


class ReportPDFView(LoginRequiredMixin, View):
    """View to download report as PDF."""

    def get(self, request, *args, **kwargs):
        """Generate and return PDF for the report."""
        try:
            report = get_object_or_404(Report, pk=kwargs["pk"])

            if not can_access_patient(request.user, report.patient):
                raise PermissionDenied("You don't have permission to access this patient")

            pdf_generator = ReportPDFGenerator()
            pdf_buffer = pdf_generator.generate_from_report(report)

            response = HttpResponse(pdf_buffer.read(), content_type="application/pdf")

            # Generate safe filename
            safe_name = "".join(
                c for c in report.patient.name if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            date_str = report.document_date.strftime("%Y%m%d")
            filename = f"Relatorio_{safe_name}_{date_str}.pdf"

            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        except PermissionDenied:
            raise
        except Exception as exc:
            logger.error("Report PDF generation error: %s", str(exc), exc_info=True)
            return HttpResponse(f"Erro ao gerar PDF: {str(exc)}", status=500)
