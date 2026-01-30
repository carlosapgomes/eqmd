import io
import logging
import zipfile
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, CreateView, FormView, DeleteView
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.utils.text import slugify

from apps.core.permissions.utils import can_access_patient, can_edit_event, can_delete_event
from apps.patients.models import Patient
from .services.pdf_generator import ConsentFormPDFGenerator

from .models import ConsentForm, ConsentTemplate, ConsentAttachment
from .forms import ConsentFormCreateForm, ConsentAttachmentUploadForm
from .utils import normalize_filename

logger = logging.getLogger(__name__)


class ConsentTemplateListAPIView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "events.add_event"

    def get(self, request, *args, **kwargs):
        templates = ConsentTemplate.objects.all().order_by("name")
        active_only = request.GET.get("active")
        if active_only and active_only.lower() in {"true", "1", "yes"}:
            templates = templates.filter(is_active=True)

        data = [
            {"id": str(template.id), "name": template.name}
            for template in templates
        ]
        return JsonResponse({"templates": data})


class ConsentFormCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = ConsentForm
    form_class = ConsentFormCreateForm
    template_name = "consentforms/consentform_create_form.html"
    permission_required = "events.add_event"

    def dispatch(self, request, *args, **kwargs):
        self.patient = get_object_or_404(Patient, pk=kwargs["patient_pk"])
        if not can_access_patient(request.user, self.patient):
            raise PermissionDenied("You don't have permission to access this patient")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["patient"] = self.patient
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["patient"] = self.patient
        context["patient_record_number"] = self.patient.get_current_record_number() or "—"
        context["active_templates"] = ConsentTemplate.objects.filter(is_active=True).order_by("name")
        return context

    def get_success_url(self):
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Termo de consentimento criado para {self.patient.name}.",
        )
        return response


class ConsentFormDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = ConsentForm
    template_name = "consentforms/consentform_detail.html"
    context_object_name = "consentform"
    permission_required = "events.view_event"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied("You don't have permission to access this patient")
        return obj

    def get_queryset(self):
        return ConsentForm.objects.select_related("patient", "created_by", "updated_by", "template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit_consentform"] = can_edit_event(self.request.user, self.object)
        context["can_delete_consentform"] = can_delete_event(self.request.user, self.object)
        context["attachments"] = self.object.attachments.all()
        return context


class ConsentFormUpdateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = ConsentAttachmentUploadForm
    template_name = "consentforms/consentform_update_form.html"
    permission_required = "events.change_event"

    def dispatch(self, request, *args, **kwargs):
        self.consent_form = get_object_or_404(ConsentForm, pk=kwargs["pk"])
        if not can_access_patient(request.user, self.consent_form.patient):
            raise PermissionDenied("You don't have permission to access this patient")
        if not can_edit_event(request.user, self.consent_form):
            raise PermissionDenied("You don't have permission to edit this consent form")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["existing_attachments"] = list(self.consent_form.attachments.all())
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["consentform"] = self.consent_form
        context["patient"] = self.consent_form.patient
        context["attachments"] = self.consent_form.attachments.all()
        return context

    def form_valid(self, form):
        files = form.cleaned_data["validated_files"]
        file_type = form.cleaned_data["attachment_kind"]
        starting_order = self.consent_form.attachments.count() + 1

        with transaction.atomic():
            for index, file_obj in enumerate(files, start=starting_order):
                ConsentAttachment.objects.create(
                    consent_form=self.consent_form,
                    file=file_obj,
                    original_filename=normalize_filename(file_obj.name),
                    file_size=file_obj.size,
                    mime_type=getattr(file_obj, "content_type", ""),
                    file_type=file_type,
                    order=index,
                )

            self.consent_form.updated_by = self.request.user
            self.consent_form.save(update_fields=["updated_by", "updated_at"])

        messages.success(self.request, "Anexos adicionados com sucesso.")
        return redirect("consentforms:consentform_update", pk=self.consent_form.pk)


class ConsentFormDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = ConsentForm
    template_name = "consentforms/consentform_confirm_delete.html"
    context_object_name = "consentform"
    permission_required = "events.delete_event"

    def get_success_url(self):
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.object.patient.pk},
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied("You don't have permission to access this patient")
        if not can_delete_event(self.request.user, obj):
            raise PermissionDenied("You don't have permission to delete this consent form")
        return obj

    def get_queryset(self):
        return ConsentForm.objects.select_related("patient", "created_by")

    def delete(self, request, *args, **kwargs):
        consent_form = self.get_object()
        patient_name = consent_form.patient.name
        messages.success(request, f"Termo de consentimento de {patient_name} excluído com sucesso.")
        return super().delete(request, *args, **kwargs)


class ConsentFormAttachmentsZipView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "events.view_event"

    def get(self, request, *args, **kwargs):
        consent_form = get_object_or_404(ConsentForm, pk=kwargs["pk"])
        if not can_access_patient(request.user, consent_form.patient):
            raise PermissionDenied("You don't have permission to access this patient")

        attachments = consent_form.attachments.order_by("order", "created_at", "original_filename")
        if not attachments.exists():
            messages.info(request, "Nenhum anexo disponível para download.")
            return redirect("consentforms:consentform_detail", pk=consent_form.pk)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for index, attachment in enumerate(attachments, start=1):
                filename = attachment.original_filename or f"anexo-{index}.jpg"
                safe_name = normalize_filename(filename)
                entry_name = f"{index:02d}-{safe_name}" if safe_name else f"{index:02d}-anexo.jpg"
                with attachment.file.open("rb") as file_obj:
                    zip_file.writestr(entry_name, file_obj.read())

        buffer.seek(0)
        safe_patient = slugify(consent_form.patient.name) or "paciente"
        date_str = consent_form.document_date.strftime("%Y%m%d")
        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = (
            f'attachment; filename="termo-assinado-{safe_patient}-{date_str}.zip"'
        )
        return response


@method_decorator(require_POST, name="dispatch")
class ConsentAttachmentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "events.change_event"

    def post(self, request, *args, **kwargs):
        attachment = get_object_or_404(ConsentAttachment, pk=kwargs["pk"])
        consent_form = attachment.consent_form

        if not can_access_patient(request.user, consent_form.patient):
            raise PermissionDenied("You don't have permission to access this patient")
        if not can_edit_event(request.user, consent_form):
            raise PermissionDenied("You don't have permission to edit this consent form")

        attachment.delete()
        consent_form.updated_by = request.user
        consent_form.save(update_fields=["updated_by", "updated_at"])
        messages.success(request, "Anexo removido com sucesso.")
        return redirect("consentforms:consentform_update", pk=consent_form.pk)


class ConsentFormPDFView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            consent_form = get_object_or_404(ConsentForm, pk=kwargs["pk"])

            if not can_access_patient(request.user, consent_form.patient):
                raise PermissionDenied("You don't have permission to access this patient")

            pdf_generator = ConsentFormPDFGenerator()
            pdf_buffer = pdf_generator.generate_from_consent(consent_form)

            response = HttpResponse(pdf_buffer.read(), content_type="application/pdf")
            safe_name = "".join(
                c for c in consent_form.patient.name if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            date_str = consent_form.document_date.strftime("%Y%m%d")
            filename = f"Termo_Consentimento_{safe_name}_{date_str}.pdf"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        except Exception as exc:
            logger.error("Consent form PDF generation error: %s", str(exc), exc_info=True)
            return HttpResponse(f"Erro ao gerar PDF: {str(exc)}", status=500)
