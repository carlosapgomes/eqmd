from datetime import timedelta
from typing import ClassVar

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.permissions.constants import EVENT_EDIT_TIME_LIMIT
from apps.events.models import Event


class DischargeReport(Event):
    """Discharge report extending the base Event model"""

    # Date fields
    admission_date: ClassVar[models.DateField] = models.DateField(
        verbose_name="Data de Admissão", help_text="Data da admissão hospitalar"
    )
    discharge_date: ClassVar[models.DateField] = models.DateField(
        verbose_name="Data de Alta", help_text="Data da alta hospitalar"
    )

    # Text content fields
    admission_history: ClassVar[models.TextField] = models.TextField(
        verbose_name="História da Admissão", help_text="História clínica da admissão"
    )
    problems_and_diagnosis: ClassVar[models.TextField] = models.TextField(
        verbose_name="Problemas e Diagnósticos",
        help_text="Problemas principais e diagnósticos",
    )
    exams_list: ClassVar[models.TextField] = models.TextField(
        verbose_name="Lista de Exames",
        help_text="Exames realizados durante a internação",
    )
    procedures_list: ClassVar[models.TextField] = models.TextField(
        verbose_name="Lista de Procedimentos", help_text="Procedimentos realizados"
    )
    inpatient_medical_history: ClassVar[models.TextField] = models.TextField(
        verbose_name="História Médica da Internação",
        help_text="Evolução médica durante a internação",
    )
    discharge_status: ClassVar[models.TextField] = models.TextField(
        verbose_name="Status da Alta", help_text="Condições do paciente na alta"
    )
    discharge_recommendations: ClassVar[models.TextField] = models.TextField(
        verbose_name="Recomendações de Alta",
        help_text="Orientações e recomendações para pós-alta",
    )

    # Classification field
    medical_specialty: ClassVar[models.CharField] = models.CharField(
        max_length=100,
        verbose_name="Especialidade Médica",
        help_text="Especialidade responsável pela alta",
    )

    # Finalization anchor for the 24h correction window (design D6)
    finalized_at: ClassVar[models.DateTimeField] = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Finalizado em",
        help_text="Data/hora da finalização que ancora a janela de correção",
    )
    finalized_by: ClassVar[models.ForeignKey] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finalized_discharge_reports",
        verbose_name="Finalizado por",
        help_text="Usuário que finalizou o relatório",
    )

    # (model field, clipboard section label) in PDF/detail display order.
    COPY_SECTION_FIELDS: ClassVar[tuple[tuple[str, str], ...]] = (
        ("problems_and_diagnosis", "Problemas e Diagnósticos"),
        ("admission_history", "História da Admissão"),
        ("exams_list", "Lista de Exames"),
        ("procedures_list", "Lista de Procedimentos"),
        ("inpatient_medical_history", "História Médica da Internação"),
        ("discharge_status", "Status da Alta"),
        ("discharge_recommendations", "Recomendações de Alta"),
    )

    class Meta:
        verbose_name = "Relatório de Alta"
        verbose_name_plural = "Relatórios de Alta"
        ordering = ["-event_datetime"]  # noqa: RUF012 — declarative Model Meta option.
        indexes = [  # noqa: RUF012 — declarative Model Meta option.
            models.Index(fields=["admission_date"]),
            models.Index(fields=["discharge_date"]),
            models.Index(fields=["medical_specialty"]),
        ]

    def __init__(self, *args, **kwargs):
        is_draft_provided = "is_draft" in kwargs
        if not is_draft_provided:
            try:
                field_names = [field.attname for field in self._meta.concrete_fields]
                is_draft_index = field_names.index("is_draft")
                is_draft_provided = len(args) > is_draft_index
            except ValueError:
                is_draft_provided = False

        super().__init__(*args, **kwargs)

        if not is_draft_provided and self._state.adding:
            self.is_draft = True

    def save(self, *args, **kwargs):
        """Override save to set the correct event type and clean text fields."""
        from .utils import clean_discharge_report_text_fields

        self.event_type = Event.DISCHARGE_REPORT_EVENT

        # Clean text fields before saving
        clean_discharge_report_text_fields(self)

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the absolute URL for this discharge report."""
        from django.urls import reverse

        return reverse(
            "apps.dischargereports:dischargereport_detail", kwargs={"pk": self.pk}
        )

    def get_edit_url(self):
        """Return the edit URL for this discharge report."""
        from django.urls import reverse

        return reverse(
            "apps.dischargereports:dischargereport_update", kwargs={"pk": self.pk}
        )

    @property
    def is_within_finalization_window(self):
        """Whether the final's 24h correction window is still open.

        The window is anchored at ``finalized_at``. Legacy finals without an
        anchor fall back to ``created_at`` so their verdicts match the
        creation-anchored rule that shipped before design D6.
        """
        anchor = self.finalized_at or self.created_at
        if anchor is None:
            return False
        return timezone.now() <= anchor + timedelta(hours=EVENT_EDIT_TIME_LIMIT)

    def can_be_edited_by_user(self, user):
        """Check if report can be edited by specific user"""
        from .services.permissions import can_edit_discharge_report

        return can_edit_discharge_report(user, self)

    def can_be_deleted_by_user(self, user):
        """Check if report can be deleted by specific user"""
        from .services.permissions import can_delete_discharge_report

        return can_delete_discharge_report(user, self)

    def get_copy_text(self) -> str:
        """Plaintext export for the clipboard copy button.

        Mirrors the PDF/detail section order with uppercase labels so the
        pasted text stays readable in the hospital's internal system.
        Blank sections are skipped; raw field text is preserved as-is
        (same contract as DailyNote's copy button).
        """
        lines: list[str] = [self._copy_header(), self._copy_date_line(), ""]
        for field_name, label in self.COPY_SECTION_FIELDS:
            value = (getattr(self, field_name, "") or "").strip()
            if not value:
                continue
            lines.append(f"{label.upper()}:")
            lines.append(value)
            lines.append("")
        return "\n".join(lines).strip()

    def _copy_header(self) -> str:
        """First clipboard line with the medical specialty."""
        header = "RELATÓRIO DE ALTA"
        specialty = (self.medical_specialty or "").strip()
        if specialty:
            header += f" — {specialty}"
        return header

    def _copy_date_line(self) -> str:
        """Second clipboard line with admission/discharge dates."""
        admission = self._format_copy_date(self.admission_date)
        discharge = self._format_copy_date(self.discharge_date)
        date_line = f"Admissão: {admission} | Alta: {discharge}"
        if self.admission_date and self.discharge_date:
            days = (self.discharge_date - self.admission_date).days
            duration = "1 dia" if days == 1 else f"{days} dias"
            date_line += f" ({duration})"
        return date_line

    @staticmethod
    def _format_copy_date(value) -> str:
        """Format a date for clipboard output, tolerating missing values."""
        if not value:
            return "—"
        return value.strftime("%d/%m/%Y")

    @property
    def status_display(self):
        """Get display text for report status"""
        if self.is_draft:
            return "Rascunho"
        else:
            return "Finalizado"

    @property
    def status_badge_class(self):
        """Get CSS class for status badge"""
        return "badge bg-warning text-dark" if self.is_draft else "badge bg-success"

    def __str__(self):
        """String representation of the discharge report."""
        draft_text = " (Rascunho)" if self.is_draft else ""
        return f"Relatório de Alta - {self.patient.name} - {self.discharge_date.strftime('%d/%m/%Y')}{draft_text}"
