"""Batch exam-request capture (lote de exames / chequinho) — S1.

Dedicated page (APAC style) for the "Solicitação de Exames SUS" template:
shared motivo/data/médico filled once plus a dynamic 1–12 exam formset.
POST creates one ``PDFFormSubmission`` per exam in a single transaction,
all sharing one ``batch_id`` inside ``form_data`` (no schema change).

Supervision follows the APAC/fill parity: ``save_draft``/``save_final``
with ``is_doctor_or_resident`` gating; students stay drafts through the
model backstop as well.
"""

import logging
import uuid

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.forms import formset_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.core.permissions.utils import is_doctor_or_resident

from ..models import PDFFormSubmission, PDFFormTemplate
from ..permissions import check_pdf_form_creation
from ..security import PDFFormSecurity
from ..services.form_generator import DynamicFormGenerator

logger = logging.getLogger(__name__)

# Single resolution point for the production chequinho template id prefix
# (slice constraint: resolve by configuration/code, never scatter the id).
EXAM_REQUEST_BATCH_TEMPLATE_ID_PREFIX = "dde2a393"

EXAM_BATCH_MAX_ITEMS = 12

BATCH_APPROVAL_DENIED_MESSAGE = (
    "Apenas médicos e residentes podem salvar lotes definitivos de exames."
)


def resolve_exam_request_template():
    """Return the active "Solicitação de Exames SUS" template.

    Resolution order: explicit ``EXAM_REQUEST_BATCH_TEMPLATE_ID`` setting,
    then the production template id prefix, then a name lookup (dev/test).
    """
    configured_id = getattr(settings, "EXAM_REQUEST_BATCH_TEMPLATE_ID", "")
    if configured_id:
        return get_object_or_404(
            PDFFormTemplate, pk=configured_id, is_active=True
        )

    candidates = PDFFormTemplate.objects.filter(is_active=True)
    for template in candidates:
        if str(template.pk).startswith(EXAM_REQUEST_BATCH_TEMPLATE_ID_PREFIX):
            return template

    for needle in ("Solicitação de Exames", "Exames SUS", "chequinho"):
        template = candidates.filter(name__icontains=needle).first()
        if template is not None:
            return template

    raise Http404("Exam request template not found")


class ExamBatchSharedForm(forms.Form):
    """Shared fields filled once for the whole batch."""

    requestReason = forms.CharField(
        label="Motivo da Solicitação",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
    currentDate = forms.DateField(
        label="Data",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}
        ),
    )
    doctor = forms.CharField(
        label="Profissional Solicitante",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    doctorRegistrationNumber = forms.CharField(
        label="Registro Profissional",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ExamBatchItemForm(forms.Form):
    """One exam row: free-text exam name plus optional code (phase 1)."""

    examRequested = forms.CharField(
        label="Exame Solicitado",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Ex.: Hemograma"}
        ),
    )
    examCode = forms.CharField(
        label="Código",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Opcional"}
        ),
    )


ExamBatchItemFormSet = formset_factory(
    ExamBatchItemForm,
    extra=1,
    min_num=1,
    validate_min=True,
    max_num=EXAM_BATCH_MAX_ITEMS,
    validate_max=True,
)


def submitted_batch_action(request):
    """Return the supervision action submitted by the form buttons."""
    if "save_final" in request.POST:
        return "save_final"
    if "save_draft" in request.POST:
        return "save_draft"
    return None


def build_exam_batch_form_data(*, template, patient, user, shared, exam, batch_id):
    """Build one submission's ``form_data`` in the current single format.

    Starts from the generator auto-fills for this template/patient/user so
    the batch rows carry exactly what the single fill would store, then
    applies the shared values, the row's exam, and the shared ``batch_id``.
    """
    generator = DynamicFormGenerator()
    form_class = generator.generate_form_class(template, patient, user)
    form_data = dict(getattr(form_class, "_patient_initial_values", {}) or {})

    current_date = shared["currentDate"]
    if hasattr(current_date, "isoformat"):
        current_date = current_date.isoformat()

    form_data.update(
        {
            "patientName": patient.name,
            "patientAddress": getattr(patient, "address", "") or "",
            "patientCity": getattr(patient, "city", "") or "",
            "patientState": getattr(patient, "state", "") or "",
            "patientNationalId": getattr(patient, "id_number", "") or "",
            "requestReason": shared["requestReason"],
            "currentDate": current_date,
            "doctor": shared["doctor"],
            "doctorRegistrationNumber": shared.get("doctorRegistrationNumber", ""),
            "examRequested": exam["examRequested"],
            "examCode": exam.get("examCode", ""),
            "batch_id": batch_id,
        }
    )
    return PDFFormSecurity.sanitize_form_data(form_data)


class ExamRequestBatchView(LoginRequiredMixin, View):
    """Capture a batch of exam requests for one patient (S1)."""

    template_name = "pdf_forms/exam_batch_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        from apps.patients.models import Patient

        self.patient = get_object_or_404(Patient, id=kwargs["patient_id"])
        check_pdf_form_creation(request.user, self.patient)
        self.form_template = resolve_exam_request_template()

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        shared_form = ExamBatchSharedForm(initial=self._shared_initial(request))
        formset = ExamBatchItemFormSet(prefix="exams")
        return render(
            request,
            self.template_name,
            self._context(shared_form, formset),
        )

    def post(self, request, *args, **kwargs):
        action = submitted_batch_action(request)
        if action == "save_final" and not is_doctor_or_resident(request.user):
            raise PermissionDenied(BATCH_APPROVAL_DENIED_MESSAGE)

        shared_form = ExamBatchSharedForm(request.POST)
        formset = ExamBatchItemFormSet(request.POST, prefix="exams")

        try:
            total_forms = int(request.POST.get("exams-TOTAL_FORMS", "0"))
        except (TypeError, ValueError):
            total_forms = 0

        exams = []
        if (
            total_forms <= EXAM_BATCH_MAX_ITEMS
            and shared_form.is_valid()
            and formset.is_valid()
        ):
            exams = [
                form.cleaned_data
                for form in formset.forms
                if form.cleaned_data
                and (form.cleaned_data.get("examRequested") or "").strip()
            ]

        if (
            total_forms > EXAM_BATCH_MAX_ITEMS
            or not shared_form.is_valid()
            or not formset.is_valid()
            or not exams
        ):
            if total_forms > EXAM_BATCH_MAX_ITEMS:
                messages.error(
                    request,
                    f"O lote comporta no máximo {EXAM_BATCH_MAX_ITEMS} exames.",
                )
            elif not exams and shared_form.is_valid() and formset.is_valid():
                messages.error(request, "Adicione ao menos um exame ao lote.")
            else:
                messages.error(request, "Por favor, corrija os erros no formulário.")
            logger.warning(
                "Exam batch validation failed (user_id=%s, patient_id=%s)",
                getattr(request.user, "id", None),
                getattr(self.patient, "id", None),
            )
            return render(
                request,
                self.template_name,
                self._context(shared_form, formset),
            )

        if action == "save_draft":
            is_draft = True
        else:
            # Definitive intent; the student backstop still forces drafts.
            is_draft = False

        batch_id = str(uuid.uuid4())
        with transaction.atomic():
            for exam in exams:
                form_data = build_exam_batch_form_data(
                    template=self.form_template,
                    patient=self.patient,
                    user=request.user,
                    shared=shared_form.cleaned_data,
                    exam=exam,
                    batch_id=batch_id,
                )
                submission = PDFFormSubmission(
                    form_template=self.form_template,
                    patient=self.patient,
                    created_by=request.user,
                    updated_by=request.user,
                    event_datetime=timezone.now(),
                    description=(
                        "Solicitação de Exames SUS: "
                        f"{exam['examRequested'].strip()}"
                    ),
                    form_data=form_data,
                    is_draft=is_draft,
                )
                submission.save()

        messages.success(
            request,
            f"Lote de {len(exams)} exames criado com sucesso!",
        )
        return redirect(
            "apps.patients:patient_events_timeline",
            patient_id=self.patient.pk,
        )

    def _shared_initial(self, request):
        """Pre-fill shared fields with the current auto-fill values."""
        user = request.user
        return {
            "doctor": user.get_full_name() or user.username,
            "doctorRegistrationNumber": getattr(
                user, "professional_registration_number", ""
            )
            or "",
            "currentDate": timezone.localdate(),
        }

    def _context(self, shared_form, formset):
        return {
            "patient": self.patient,
            "form_template": self.form_template,
            "shared_form": shared_form,
            "formset": formset,
            "can_finalize": is_doctor_or_resident(self.request.user),
            "max_items": EXAM_BATCH_MAX_ITEMS,
        }
