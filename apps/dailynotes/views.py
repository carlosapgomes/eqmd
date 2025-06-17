from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from datetime import datetime, timedelta

from .models import DailyNote
from .forms import DailyNoteForm
from apps.core.permissions import (
    patient_access_required,
    can_edit_event_required,
    can_delete_event_required,
    hospital_context_required,
    can_access_patient,
    can_edit_event,
    can_delete_event,
)
from apps.patients.models import Patient
from apps.sample_content.models import SampleContent
from apps.events.models import Event


@method_decorator(hospital_context_required, name="dispatch")
class DailyNoteListView(LoginRequiredMixin, ListView):
    """
    List view for DailyNote instances with search and filtering capabilities.
    """

    model = DailyNote
    template_name = "dailynotes/dailynote_list.html"
    context_object_name = "dailynotes"
    paginate_by = 20
    paginate_orphans = 5

    def get_queryset(self):
        """Filter queryset based on search parameters and user permissions."""
        queryset = (
            DailyNote.objects.select_related("patient", "created_by", "updated_by")
            .prefetch_related(
                "patient__current_hospital", "patient__hospitalrecord_set"
            )
            .all()
        )

        # Filter by user's hospital context and patient access permissions
        if (
            hasattr(self.request.user, "current_hospital")
            and self.request.user.current_hospital
        ):
            # Only show daily notes for patients in the user's current hospital
            queryset = queryset.filter(
                patient__current_hospital=self.request.user.current_hospital
            )

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
                | Q(patient__name__icontains=search_query)
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
        """Add additional context data including permission checks for each daily note."""
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context["selected_patient"] = self.request.GET.get("patient", "")
        context["date_from"] = self.request.GET.get("date_from", "")
        context["date_to"] = self.request.GET.get("date_to", "")
        context["selected_creator"] = self.request.GET.get("creator", "")

        # Cache key for filter options
        cache_key = f"dailynotes_filters_{self.request.user.id}_{getattr(self.request.user, 'current_hospital_id', 'none')}"

        # Try to get filter options from cache
        filter_options = cache.get(cache_key)
        if filter_options is None:
            # Get available patients for filter dropdown (only accessible ones)
            from apps.core.permissions.cache import get_user_accessible_patients

            if (
                hasattr(self.request.user, "current_hospital")
                and self.request.user.current_hospital
            ):
                accessible_patient_ids = get_user_accessible_patients(self.request.user)
                accessible_patients = Patient.objects.filter(
                    id__in=accessible_patient_ids,
                    current_hospital=self.request.user.current_hospital,
                ).only("id", "name", "fiscal_number")
            else:
                accessible_patients = Patient.objects.none()

            # Get available creators (users who have created daily notes in this hospital)
            from django.contrib.auth import get_user_model

            User = get_user_model()
            if (
                hasattr(self.request.user, "current_hospital")
                and self.request.user.current_hospital
            ):
                available_creators = (
                    User.objects.filter(
                        dailynote_created__patient__current_hospital=self.request.user.current_hospital
                    )
                    .distinct()
                    .only("id", "first_name", "last_name", "email")
                )
            else:
                available_creators = User.objects.none()

            filter_options = {
                "available_patients": accessible_patients,
                "available_creators": available_creators,
            }
            # Cache for 5 minutes
            cache.set(cache_key, filter_options, 300)

        context["available_patients"] = filter_options["available_patients"]
        context["available_creators"] = filter_options["available_creators"]

        # Add permission information for each daily note
        if "dailynote_list" in context:
            for dailynote in context["dailynote_list"]:
                dailynote.can_edit = can_edit_event(self.request.user, dailynote)
                dailynote.can_delete = can_delete_event(self.request.user, dailynote)

        return context


@method_decorator(hospital_context_required, name="dispatch")
class DailyNoteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for DailyNote instances.
    """

    model = DailyNote
    template_name = "dailynotes/dailynote_detail.html"
    context_object_name = "dailynote"
    permission_required = "events.view_event"

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's daily notes"
            )

        return obj

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return DailyNote.objects.select_related("patient", "created_by", "updated_by")

    def get_context_data(self, **kwargs):
        """Add additional context data including permission checks."""
        context = super().get_context_data(**kwargs)

        # Add permission context for template use
        context["can_edit_dailynote"] = can_edit_event(self.request.user, self.object)
        context["can_delete_dailynote"] = can_delete_event(
            self.request.user, self.object
        )

        return context


@method_decorator(hospital_context_required, name="dispatch")
class DailyNoteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Update view for DailyNote instances with permission checking.
    """

    model = DailyNote
    form_class = DailyNoteForm
    template_name = "dailynotes/dailynote_update_form.html"
    permission_required = "events.change_event"

    def get_object(self, queryset=None):
        """Get object and check patient access and edit permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's daily notes"
            )

        # Check if user can edit this event
        if not can_edit_event(self.request.user, obj):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied("You don't have permission to edit this daily note")

        return obj

    def get_form_kwargs(self):
        """Pass current user to form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        """Redirect to detail view after successful update."""
        return reverse_lazy(
            "dailynotes:dailynote_detail", kwargs={"pk": self.object.pk}
        )

    def get_context_data(self, **kwargs):
        """Add sample content context."""
        context = super().get_context_data(**kwargs)
        context["sample_contents"] = SampleContent.objects.filter(
            event_type=Event.DAILY_NOTE_EVENT
        ).order_by("title")
        return context

    def form_valid(self, form):
        """Handle successful form submission with patient access validation."""
        # Check if user can access the selected patient (in case patient was changed)
        if not can_access_patient(self.request.user, form.instance.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to create daily notes for this patient"
            )

        messages.success(
            self.request,
            f"Evolução para {form.instance.patient.name} atualizada com sucesso.",
        )
        return super().form_valid(form)


@method_decorator(hospital_context_required, name="dispatch")
class DailyNoteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Delete view for DailyNote instances with permission checking.
    """

    model = DailyNote
    template_name = "dailynotes/dailynote_confirm_delete.html"
    context_object_name = "dailynote"
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
                "You don't have permission to access this patient's daily notes"
            )

        # Check if user can delete this event
        if not can_delete_event(self.request.user, obj):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to delete this daily note"
            )

        return obj

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return DailyNote.objects.select_related("patient", "created_by")

    def delete(self, request, *args, **kwargs):
        """Handle successful deletion."""
        dailynote = self.get_object()
        patient_name = dailynote.patient.name
        messages.success(request, f"Evolução para {patient_name} excluída com sucesso.")
        return super().delete(request, *args, **kwargs)


# @method_decorator(hospital_context_required, name="dispatch")
# class PatientDailyNoteListView(LoginRequiredMixin, ListView):
#     """
#     List view for DailyNote instances for a specific patient with date filtering.
#     """
#
#     model = DailyNote
#     template_name = "dailynotes/patient_dailynote_list.html"
#     context_object_name = "dailynotes"
#     paginate_by = 20
#     paginate_orphans = 5
#
#     def dispatch(self, request, *args, **kwargs):
#         """Get patient and check permissions before processing request."""
#         self.patient = get_object_or_404(Patient, pk=kwargs["patient_pk"])
#
#         # Check if user can access this patient
#         if not can_access_patient(request.user, self.patient):
#             from django.core.exceptions import PermissionDenied
#
#             raise PermissionDenied(
#                 "You don't have permission to access this patient's daily notes"
#             )
#
#         return super().dispatch(request, *args, **kwargs)
#
#     def get_queryset(self):
#         """Filter queryset for specific patient with date range filtering."""
#         queryset = DailyNote.objects.filter(patient=self.patient).select_related(
#             "created_by", "updated_by"
#         )
#
#         # Date range filtering
#         date_from = self.request.GET.get("date_from")
#         date_to = self.request.GET.get("date_to")
#
#         if date_from:
#             try:
#                 date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
#                 queryset = queryset.filter(event_datetime__date__gte=date_from)
#             except ValueError:
#                 pass
#
#         if date_to:
#             try:
#                 date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
#                 queryset = queryset.filter(event_datetime__date__lte=date_to)
#             except ValueError:
#                 pass
#
#         # Search in content
#         search_query = self.request.GET.get("search", "")
#         if search_query:
#             queryset = queryset.filter(
#                 Q(description__icontains=search_query)
#                 | Q(content__icontains=search_query)
#             )
#
#         return queryset.order_by("-event_datetime")
#
#     def get_context_data(self, **kwargs):
#         """Add patient and filter context."""
#         context = super().get_context_data(**kwargs)
#         context["patient"] = self.patient
#         context["search_query"] = self.request.GET.get("search", "")
#         context["date_from"] = self.request.GET.get("date_from", "")
#         context["date_to"] = self.request.GET.get("date_to", "")
#
#         # Add permission information for each daily note
#         if "dailynote_list" in context:
#             for dailynote in context["dailynote_list"]:
#                 dailynote.can_edit = can_edit_event(self.request.user, dailynote)
#                 dailynote.can_delete = can_delete_event(self.request.user, dailynote)
#
#         return context
#


@method_decorator(hospital_context_required, name="dispatch")
class PatientDailyNoteCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    """
    Create view for DailyNote instances for a specific patient.
    """

    model = DailyNote
    form_class = DailyNoteForm
    template_name = "dailynotes/patient_dailynote_form.html"
    permission_required = "events.add_event"

    def dispatch(self, request, *args, **kwargs):
        """Get patient and check permissions before processing request."""
        self.patient = get_object_or_404(Patient, pk=kwargs["patient_pk"])

        # Check if user can access this patient
        if not can_access_patient(request.user, self.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to create daily notes for this patient"
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
            event_type=Event.DAILY_NOTE_EVENT
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
            self.request, f"Evolução para {self.patient.name} criada com sucesso."
        )
        return super().form_valid(form)


@method_decorator(hospital_context_required, name="dispatch")
class DailyNoteDuplicateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Duplicate view for DailyNote instances - creates a new dailynote based on an existing one.
    """

    model = DailyNote
    form_class = DailyNoteForm
    template_name = "dailynotes/dailynote_duplicate_form.html"
    permission_required = "events.add_event"

    def dispatch(self, request, *args, **kwargs):
        """Get source dailynote and check permissions before processing request."""
        self.source_dailynote = get_object_or_404(DailyNote, pk=kwargs["pk"])

        # Check if user can access the source patient
        if not can_access_patient(request.user, self.source_dailynote.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's daily notes"
            )

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass current user and pre-populate form with source dailynote data."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user

        # Pre-populate with source dailynote data, but with current datetime
        kwargs["initial"] = {
            "content": self.source_dailynote.content,
            "event_datetime": timezone.now(),
        }
        return kwargs

    def get_context_data(self, **kwargs):
        """Add source dailynote, patient and sample content context."""
        context = super().get_context_data(**kwargs)
        context["source_dailynote"] = self.source_dailynote
        context["patient"] = self.source_dailynote.patient
        context["sample_contents"] = SampleContent.objects.filter(
            event_type=Event.DAILY_NOTE_EVENT
        ).order_by("title")
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful creation."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.source_dailynote.patient.pk},
        )

    def form_valid(self, form):
        """Handle successful form submission."""
        form.instance.patient = self.source_dailynote.patient
        messages.success(
            self.request,
            f"Nova evolução para {self.source_dailynote.patient.name} criada com base na evolução anterior.",
        )
        return super().form_valid(form)


@method_decorator(hospital_context_required, name="dispatch")
class DailyNotePrintView(LoginRequiredMixin, DetailView):
    """
    Print view for DailyNote instances - clean print layout.
    """

    model = DailyNote
    template_name = "dailynotes/dailynote_print.html"
    context_object_name = "dailynote"

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's daily notes"
            )

        return obj

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return DailyNote.objects.select_related("patient", "created_by", "updated_by")


@method_decorator(hospital_context_required, name="dispatch")
class PatientDailyNoteExportView(LoginRequiredMixin, ListView):
    """
    Export view for all daily notes of a specific patient - print-friendly format.
    """

    model = DailyNote
    template_name = "dailynotes/patient_dailynote_export.html"
    context_object_name = "dailynotes"

    def dispatch(self, request, *args, **kwargs):
        """Get patient and check permissions before processing request."""
        self.patient = get_object_or_404(Patient, pk=kwargs["patient_pk"])

        # Check if user can access this patient
        if not can_access_patient(request.user, self.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's daily notes"
            )

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Get all daily notes for the patient, ordered by date."""
        return (
            DailyNote.objects.filter(patient=self.patient)
            .select_related("created_by", "updated_by")
            .order_by("event_datetime")
        )

    def get_context_data(self, **kwargs):
        """Add patient context."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.patient
        context["export_date"] = timezone.now()
        return context
