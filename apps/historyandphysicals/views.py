from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from datetime import datetime, timedelta

from .models import HistoryAndPhysical
from .forms import HistoryAndPhysicalForm
from apps.core.permissions import (
    patient_access_required,
    can_edit_event_required,
    can_delete_event_required,
    can_access_patient,
    can_edit_event,
    can_delete_event,
)
from apps.core.permissions.utils import is_doctor_or_resident
from apps.patients.models import Patient
from apps.sample_content.models import SampleContent
from apps.events.models import Event
from apps.events.services.event_deletion import delete_event_record

DRAFT_APPROVAL_DENIED_MESSAGE = (
    "Apenas médicos e residentes podem aprovar rascunhos de anamnese e exame físico."
)


def visible_history_and_physicals():
    """Active H&Ps with human drafts, bot drafts excluded (design D3).

    The default manager hides every draft, and bot drafts must stay on their
    own botauth promotion path, so the queryset re-admits human drafts only.
    """
    return (
        HistoryAndPhysical.objects.with_drafts()
        .filter(Q(is_draft=False) | Q(draft_created_by_bot=""))
        .select_related("patient", "created_by", "updated_by")
    )


class HistoryAndPhysicalListView(LoginRequiredMixin, ListView):
    """
    List view for HistoryAndPhysical instances with search and filtering capabilities.
    """

    model = HistoryAndPhysical
    template_name = "historyandphysicals/historyandphysical_list.html"
    context_object_name = "historyandphysicals"
    paginate_by = 20
    paginate_orphans = 5

    def get_queryset(self):
        """Filter queryset based on search parameters and user permissions."""
        queryset = (
            HistoryAndPhysical.objects.select_related("patient", "created_by", "updated_by")
            .all()
        )

        # Filter by patient access permissions (single hospital configuration)
        # All users can access all patients in the single hospital setup

        # Optimize patient access check with bulk operations
        from apps.core.permissions.cache import get_user_accessible_patients

        accessible_patient_ids = get_user_accessible_patients(self.request.user)
        if accessible_patient_ids:
            queryset = queryset.filter(patient__id__in=accessible_patient_ids)
        else:
            queryset = queryset.none()

        # Search functionality
        search_query = self.request.GET.get("search", "")
        if search_query:
            queryset = queryset.filter(
                Q(description__icontains=search_query)
                | Q(content__icontains=search_query)
                | Q(patient__name__unaccent__icontains=search_query)
            )

        # Filter by patient if specified
        patient_id = self.request.GET.get("patient")
        if patient_id:
            queryset = queryset.filter(patient__id=patient_id)

        # Date range filtering
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")

        if date_from:
            try:
                date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
                queryset = queryset.filter(event_datetime__date__gte=date_from)
            except ValueError:
                pass

        if date_to:
            try:
                date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
                queryset = queryset.filter(event_datetime__date__lte=date_to)
            except ValueError:
                pass

        # Filter by creator
        creator_id = self.request.GET.get("creator")
        if creator_id:
            queryset = queryset.filter(created_by__id=creator_id)

        return queryset.order_by("-event_datetime")

    def get_context_data(self, **kwargs):
        """Add additional context data including permission checks for each history and physical."""
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context["selected_patient"] = self.request.GET.get("patient", "")
        context["date_from"] = self.request.GET.get("date_from", "")
        context["date_to"] = self.request.GET.get("date_to", "")
        context["selected_creator"] = self.request.GET.get("creator", "")

        # Cache key for filter options
        cache_key = f"historyandphysicals_filters_{self.request.user.id}"

        # Try to get filter options from cache
        filter_options = cache.get(cache_key)
        if filter_options is None:
            # Get available patients for filter dropdown (only accessible ones)
            from apps.core.permissions.cache import get_user_accessible_patients

            accessible_patient_ids = get_user_accessible_patients(self.request.user)
            if accessible_patient_ids:
                accessible_patients = Patient.objects.filter(
                    id__in=accessible_patient_ids
                ).only("id", "name", "fiscal_number")
            else:
                accessible_patients = Patient.objects.none()

            # Get available creators (users who have created history and physicals in this hospital)
            from django.contrib.auth import get_user_model

            User = get_user_model()
            available_creators = (
                User.objects.filter(
                    historyandphysical_created__patient__id__in=accessible_patient_ids
                )
                .distinct()
                .only("id", "first_name", "last_name", "email")
            )

            filter_options = {
                "available_patients": accessible_patients,
                "available_creators": available_creators,
            }
            # Cache for 5 minutes
            cache.set(cache_key, filter_options, 300)

        context["available_patients"] = filter_options["available_patients"]
        context["available_creators"] = filter_options["available_creators"]

        # Add permission information for each history and physical
        if "historyandphysical_list" in context:
            for historyandphysical in context["historyandphysical_list"]:
                historyandphysical.can_edit = can_edit_event(self.request.user, historyandphysical)
                historyandphysical.can_delete = can_delete_event(self.request.user, historyandphysical)

        return context


class HistoryAndPhysicalDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for HistoryAndPhysical instances.
    """

    model = HistoryAndPhysical
    template_name = "historyandphysicals/historyandphysical_detail.html"
    context_object_name = "historyandphysical"
    permission_required = "events.view_event"

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's history and physicals"
            )

        return obj

    def get_queryset(self):
        """Resolve definitive records and human drafts (bot drafts stay 404)."""
        return visible_history_and_physicals()

    def get_context_data(self, **kwargs):
        """Add additional context data including permission checks."""
        context = super().get_context_data(**kwargs)

        # Add permission context for template use
        context["can_edit_historyandphysical"] = can_edit_event(self.request.user, self.object)
        context["can_delete_historyandphysical"] = can_delete_event(
            self.request.user, self.object
        )

        return context


class HistoryAndPhysicalUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Update view for HistoryAndPhysical instances with permission checking.
    """

    model = HistoryAndPhysical
    form_class = HistoryAndPhysicalForm
    template_name = "historyandphysicals/historyandphysical_update_form.html"
    permission_required = "events.change_event"

    def get_queryset(self):
        """Resolve definitive records and human drafts (bot drafts stay 404)."""
        return visible_history_and_physicals()

    def get_object(self, queryset=None):
        """Get object and check patient access and edit permissions."""
        obj = super().get_object(queryset)
        # Capture the persisted status so the action dispatch and the
        # re-rendered form agree with the stored record.
        self.was_draft = obj.is_draft

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's history and physicals"
            )

        # Check if user can edit this event
        if not can_edit_event(self.request.user, obj):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied("You don't have permission to edit this history and physical")

        return obj

    def get_form_kwargs(self):
        """Pass current user to form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        """Redirect to patient timeline after successful update."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline", 
            kwargs={"patient_id": self.object.patient.pk}
        )

    def get_context_data(self, **kwargs):
        """Add sample content and draft action context."""
        context = super().get_context_data(**kwargs)
        context["sample_contents"] = SampleContent.objects.filter(
            event_type=Event.HISTORY_AND_PHYSICAL_EVENT
        ).order_by("title")
        context["is_draft_note"] = self.object.is_draft
        context["can_finalize"] = self.object.is_draft and is_doctor_or_resident(
            self.request.user
        )
        return context

    def _submitted_action(self):
        """Return the update action submitted by the form buttons."""
        if "save_final" in self.request.POST:
            return "save_final"
        if "save_draft" in self.request.POST:
            return "save_draft"
        return None

    def form_valid(self, form):
        """Persist the record, keeping or promoting the supervised draft state."""
        # Check if user can access the selected patient (in case patient was changed)
        if not can_access_patient(self.request.user, form.instance.patient):
            raise PermissionDenied(
                "You don't have permission to create history and physicals for this patient"
            )

        action = self._submitted_action()
        was_draft = self.was_draft

        # Approving a draft is a physician act; the update template hides the
        # button, this gate enforces it (design D5).
        if (
            was_draft
            and action == "save_final"
            and not is_doctor_or_resident(self.request.user)
        ):
            raise PermissionDenied(DRAFT_APPROVAL_DENIED_MESSAGE)

        self.object = form.save(commit=False)
        self.object.updated_by = self.request.user

        if was_draft and action == "save_final":
            self.object.is_draft = False
            self.object.draft_promoted_at = timezone.now()
            self.object.draft_promoted_by = self.request.user
            messages.success(
                self.request,
                f"Anamnese e Exame Físico para {self.object.patient.name} aprovada e registrada no prontuário.",
            )
        elif was_draft:
            self.object.is_draft = True
            messages.success(
                self.request,
                f"Rascunho da anamnese e exame físico para {self.object.patient.name} atualizado.",
            )
        else:
            messages.success(
                self.request,
                f"Anamnese e Exame Físico para {self.object.patient.name} atualizada com sucesso.",
            )

        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


class HistoryAndPhysicalDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Delete view for HistoryAndPhysical instances with permission checking.
    """

    model = HistoryAndPhysical
    template_name = "historyandphysicals/historyandphysical_confirm_delete.html"
    context_object_name = "historyandphysical"
    permission_required = "events.delete_event"
    def get_success_url(self):
        """Redirect to patient timeline after successful deletion."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.object.patient.pk},
        )

    def get_object(self, queryset=None):
        """Get object and check patient access and delete permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's history and physicals"
            )

        # Check if user can delete this event
        if not can_delete_event(self.request.user, obj):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to delete this history and physical"
            )

        return obj

    def get_queryset(self):
        """Resolve definitive records and human drafts (bot drafts stay 404)."""
        return visible_history_and_physicals()

    def form_valid(self, form):
        """Delete the record, hard-deleting never-finalized drafts (design D7).

        ``BaseDeleteView.form_valid`` would call ``self.object.delete()``
        directly, so the method decision lives here instead.
        """
        historyandphysical = self.object
        delete_event_record(historyandphysical, deleted_by=self.request.user)
        messages.success(
            self.request,
            f"Anamnese e Exame Físico para {historyandphysical.patient.name} excluída com sucesso.",
        )
        return HttpResponseRedirect(self.get_success_url())


class PatientHistoryAndPhysicalCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    """
    Create view for HistoryAndPhysical instances for a specific patient.
    """

    model = HistoryAndPhysical
    form_class = HistoryAndPhysicalForm
    template_name = "historyandphysicals/historyandphysical_create_form.html"
    permission_required = "events.add_event"

    def dispatch(self, request, *args, **kwargs):
        """Get patient and check permissions before processing request."""
        self.patient = get_object_or_404(Patient, pk=kwargs["patient_pk"])

        # Check if user can access this patient
        if not can_access_patient(request.user, self.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to create history and physicals for this patient"
            )

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass current user and initial patient to form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["initial"] = {"patient": self.patient}
        return kwargs

    def get_context_data(self, **kwargs):
        """Add patient and sample content context."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.patient
        context["sample_contents"] = SampleContent.objects.filter(
            event_type=Event.HISTORY_AND_PHYSICAL_EVENT
        ).order_by("title")
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful creation."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )

    def form_valid(self, form):
        """Handle successful form submission."""
        form.instance.patient = self.patient
        messages.success(
            self.request, f"Anamnese e Exame Físico para {self.patient.name} criada com sucesso."
        )
        return super().form_valid(form)


class HistoryAndPhysicalDuplicateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Duplicate view for HistoryAndPhysical instances - creates a new history and physical based on an existing one.
    """

    model = HistoryAndPhysical
    form_class = HistoryAndPhysicalForm
    template_name = "historyandphysicals/historyandphysical_duplicate_form.html"
    permission_required = "events.add_event"

    def dispatch(self, request, *args, **kwargs):
        """Get source history and physical and check permissions before processing request."""
        self.source_historyandphysical = get_object_or_404(HistoryAndPhysical, pk=kwargs["pk"])

        # Check if user can access the source patient
        if not can_access_patient(request.user, self.source_historyandphysical.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's history and physicals"
            )

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass current user and pre-populate form with source history and physical data."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user

        # Pre-populate with source history and physical data, but with current datetime
        kwargs["initial"] = {
            "content": self.source_historyandphysical.content,
            "event_datetime": timezone.now(),
        }
        return kwargs

    def get_context_data(self, **kwargs):
        """Add source history and physical, patient and sample content context."""
        context = super().get_context_data(**kwargs)
        context["source_historyandphysical"] = self.source_historyandphysical
        context["patient"] = self.source_historyandphysical.patient
        context["sample_contents"] = SampleContent.objects.filter(
            event_type=Event.HISTORY_AND_PHYSICAL_EVENT
        ).order_by("title")
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful creation."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.source_historyandphysical.patient.pk},
        )

    def form_valid(self, form):
        """Handle successful form submission."""
        form.instance.patient = self.source_historyandphysical.patient
        messages.success(
            self.request,
            f"Nova Anamnese e Exame Físico para {self.source_historyandphysical.patient.name} criada com base na anterior.",
        )
        return super().form_valid(form)


class HistoryAndPhysicalPrintView(LoginRequiredMixin, DetailView):
    """
    Print view for HistoryAndPhysical instances - clean print layout.
    """

    model = HistoryAndPhysical
    template_name = "historyandphysicals/historyandphysical_print.html"
    context_object_name = "historyandphysical"

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's history and physicals"
            )

        return obj

    def get_queryset(self):
        """Serve final records only (design D10).

        The default manager excludes every draft, so printing a human or bot
        draft is a 404 for every user while finals render as before.
        """
        return HistoryAndPhysical.objects.select_related("patient", "created_by", "updated_by")


