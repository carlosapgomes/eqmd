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
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from datetime import datetime, timedelta

from .models import SimpleNote
from .forms import SimpleNoteForm
from apps.core.permissions import (
    patient_access_required,
    can_edit_event_required,
    can_delete_event_required,
    can_access_patient,
    can_edit_event,
    can_delete_event,
)
from apps.patients.models import Patient
from apps.sample_content.models import SampleContent
from apps.events.models import Event
from apps.events.services.event_deletion import delete_event_record
from apps.core.permissions.utils import is_doctor_or_resident

DRAFT_APPROVAL_DENIED_MESSAGE = (
    "Apenas médicos e residentes podem aprovar rascunhos de notas."
)


def visible_simple_notes():
    """Active simple notes with human drafts, bot drafts excluded (design D3).

    The default manager hides every draft, and bot drafts must stay on their
    own botauth promotion path, so the queryset re-admits human drafts only.
    """
    return (
        SimpleNote.objects.with_drafts()
        .filter(Q(is_draft=False) | Q(draft_created_by_bot=""))
        .select_related("patient", "created_by", "updated_by")
    )


class SimpleNoteListView(LoginRequiredMixin, ListView):
    """
    List view for SimpleNote instances with search and filtering capabilities.
    """

    model = SimpleNote
    template_name = "simplenotes/simplenote_list.html"
    context_object_name = "simplenotes"
    paginate_by = 20
    paginate_orphans = 5

    def get_queryset(self):
        """Filter queryset based on search parameters and user permissions."""
        queryset = (
            SimpleNote.objects.select_related("patient", "created_by", "updated_by")
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
        """Add additional context data including permission checks for each simple note."""
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context["selected_patient"] = self.request.GET.get("patient", "")
        context["date_from"] = self.request.GET.get("date_from", "")
        context["date_to"] = self.request.GET.get("date_to", "")
        context["selected_creator"] = self.request.GET.get("creator", "")

        # Cache key for filter options
        cache_key = f"simplenotes_filters_{self.request.user.id}"

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

            # Get available creators (users who have created simple notes in this hospital)
            from django.contrib.auth import get_user_model

            User = get_user_model()
            available_creators = (
                User.objects.filter(
                    simplenote_created__patient__id__in=accessible_patient_ids
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

        # Add permission information for each simple note
        if "simplenote_list" in context:
            for simplenote in context["simplenote_list"]:
                simplenote.can_edit = can_edit_event(self.request.user, simplenote)
                simplenote.can_delete = can_delete_event(self.request.user, simplenote)

        return context


class SimpleNoteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for SimpleNote instances.
    """

    model = SimpleNote
    template_name = "simplenotes/simplenote_detail.html"
    context_object_name = "simplenote"
    permission_required = "events.view_event"

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's simple notes"
            )

        return obj

    def get_queryset(self):
        """Resolve definitive notes and human drafts (bot drafts stay 404)."""
        return visible_simple_notes()

    def get_context_data(self, **kwargs):
        """Add additional context data including permission checks."""
        context = super().get_context_data(**kwargs)

        # Add permission context for template use
        context["can_edit_simplenote"] = can_edit_event(self.request.user, self.object)
        context["can_delete_simplenote"] = can_delete_event(
            self.request.user, self.object
        )

        return context


class SimpleNoteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Update view for SimpleNote instances with permission checking.
    """

    model = SimpleNote
    form_class = SimpleNoteForm
    template_name = "simplenotes/simplenote_update_form.html"
    permission_required = "events.change_event"

    def get_queryset(self):
        """Resolve definitive notes and human drafts (bot drafts stay 404)."""
        return visible_simple_notes()

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
                "You don't have permission to access this patient's simple notes"
            )

        # Check if user can edit this event
        if not can_edit_event(self.request.user, obj):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied("You don't have permission to edit this simple note")

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
            event_type=Event.SIMPLE_NOTE_EVENT
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
        """Persist the note, keeping or promoting the supervised draft state."""
        # Check if user can access the selected patient (in case patient was changed)
        if not can_access_patient(self.request.user, form.instance.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to create simple notes for this patient"
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
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(DRAFT_APPROVAL_DENIED_MESSAGE)

        self.object = form.save(commit=False)
        self.object.updated_by = self.request.user

        if was_draft and action == "save_final":
            self.object.is_draft = False
            self.object.draft_promoted_at = timezone.now()
            self.object.draft_promoted_by = self.request.user
            messages.success(
                self.request,
                f"Nota para {self.object.patient.name} aprovada e registrada no prontuário.",
            )
        elif was_draft:
            self.object.is_draft = True
            messages.success(
                self.request,
                f"Rascunho da nota para {self.object.patient.name} atualizado.",
            )
        else:
            messages.success(
                self.request,
                f"Nota para {self.object.patient.name} atualizada com sucesso.",
            )

        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


class SimpleNoteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Delete view for SimpleNote instances with permission checking.
    """

    model = SimpleNote
    template_name = "simplenotes/simplenote_confirm_delete.html"
    context_object_name = "simplenote"
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
                "You don't have permission to access this patient's simple notes"
            )

        # Check if user can delete this event
        if not can_delete_event(self.request.user, obj):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to delete this simple note"
            )

        return obj

    def get_queryset(self):
        """Resolve definitive notes and human drafts (bot drafts stay 404)."""
        return visible_simple_notes()

    def form_valid(self, form):
        """Delete the note, hard-deleting never-finalized drafts (design D7).

        ``BaseDeleteView.form_valid`` would call ``self.object.delete()``
        directly, so the method decision lives here instead.
        """
        note = self.object
        delete_event_record(note, deleted_by=self.request.user)
        messages.success(
            self.request, f"Nota para {note.patient.name} excluída com sucesso."
        )
        return HttpResponseRedirect(self.get_success_url())


class PatientSimpleNoteCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    """
    Create view for SimpleNote instances for a specific patient.
    """

    model = SimpleNote
    form_class = SimpleNoteForm
    template_name = "simplenotes/simplenote_create_form.html"
    permission_required = "events.add_event"

    def dispatch(self, request, *args, **kwargs):
        """Get patient and check permissions before processing request."""
        self.patient = get_object_or_404(Patient, pk=kwargs["patient_pk"])

        # Check if user can access this patient
        if not can_access_patient(request.user, self.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to create simple notes for this patient"
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
            event_type=Event.SIMPLE_NOTE_EVENT
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
            self.request, f"Nota para {self.patient.name} criada com sucesso."
        )
        return super().form_valid(form)


class SimpleNoteDuplicateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Duplicate view for SimpleNote instances - creates a new simplenote based on an existing one.
    """

    model = SimpleNote
    form_class = SimpleNoteForm
    template_name = "simplenotes/simplenote_duplicate_form.html"
    permission_required = "events.add_event"

    def dispatch(self, request, *args, **kwargs):
        """Get source simplenote and check permissions before processing request."""
        self.source_simplenote = get_object_or_404(SimpleNote, pk=kwargs["pk"])

        # Check if user can access the source patient
        if not can_access_patient(request.user, self.source_simplenote.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's simple notes"
            )

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass current user and pre-populate form with source simplenote data."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user

        # Pre-populate with source simplenote data, but with current datetime
        kwargs["initial"] = {
            "content": self.source_simplenote.content,
            "event_datetime": timezone.now(),
        }
        return kwargs

    def get_context_data(self, **kwargs):
        """Add source simplenote, patient and sample content context."""
        context = super().get_context_data(**kwargs)
        context["source_simplenote"] = self.source_simplenote
        context["patient"] = self.source_simplenote.patient
        context["sample_contents"] = SampleContent.objects.filter(
            event_type=Event.SIMPLE_NOTE_EVENT
        ).order_by("title")
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful creation."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.source_simplenote.patient.pk},
        )

    def form_valid(self, form):
        """Handle successful form submission."""
        form.instance.patient = self.source_simplenote.patient
        messages.success(
            self.request,
            f"Nova nota para {self.source_simplenote.patient.name} criada com base na nota anterior.",
        )
        return super().form_valid(form)


class SimpleNotePrintView(LoginRequiredMixin, DetailView):
    """
    Print view for SimpleNote instances - clean print layout.
    """

    model = SimpleNote
    template_name = "simplenotes/simplenote_print.html"
    context_object_name = "simplenote"

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to access this patient's simple notes"
            )

        return obj

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return SimpleNote.objects.select_related("patient", "created_by", "updated_by")