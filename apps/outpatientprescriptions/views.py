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
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta

from .models import OutpatientPrescription, PrescriptionItem
from .forms.prescription_forms import OutpatientPrescriptionForm, PrescriptionItemFormSet, PrescriptionItemFormSetHelper
from apps.core.permissions import (
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
from apps.drugtemplates.models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem


@method_decorator(hospital_context_required, name="dispatch")
class OutpatientPrescriptionListView(LoginRequiredMixin, ListView):
    """
    List view for OutpatientPrescription instances with search and filtering capabilities.
    """

    model = OutpatientPrescription
    template_name = "outpatientprescriptions/outpatientprescription_list.html"
    context_object_name = "prescriptions"
    paginate_by = 20
    paginate_orphans = 5

    def get_queryset(self):
        """Filter queryset based on search parameters and user permissions."""
        queryset = (
            OutpatientPrescription.objects.select_related("patient", "created_by", "updated_by")
            .prefetch_related(
                "patient__current_hospital", "patient__hospitalrecord_set", "items"
            )
            .all()
        )

        # Filter by user's hospital context and patient access permissions
        if (
            hasattr(self.request.user, "current_hospital")
            and self.request.user.current_hospital
        ):
            # Only show prescriptions for patients in the user's current hospital or outpatients
            queryset = queryset.filter(
                Q(patient__current_hospital=self.request.user.current_hospital) |
                Q(patient__status__in=['outpatient', 'discharged'])
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
                Q(instructions__icontains=search_query)
                | Q(patient__name__icontains=search_query)
                | Q(items__drug_name__icontains=search_query)
            ).distinct()

        # Filter by patient if specified
        patient_id = self.request.GET.get("patient")
        if patient_id:
            queryset = queryset.filter(patient__id=patient_id)

        # Filter by status
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # Date range filtering (using prescription_date)
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")

        if date_from:
            try:
                date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
                queryset = queryset.filter(prescription_date__gte=date_from)
            except ValueError:
                pass

        if date_to:
            try:
                date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
                queryset = queryset.filter(prescription_date__lte=date_to)
            except ValueError:
                pass

        # Filter by creator
        creator_id = self.request.GET.get("creator")
        if creator_id:
            queryset = queryset.filter(created_by__id=creator_id)

        return queryset.order_by("-prescription_date", "-event_datetime")

    def get_context_data(self, **kwargs):
        """Add additional context data including permission checks for each prescription."""
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context["selected_patient"] = self.request.GET.get("patient", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["date_from"] = self.request.GET.get("date_from", "")
        context["date_to"] = self.request.GET.get("date_to", "")
        context["selected_creator"] = self.request.GET.get("creator", "")

        # Cache key for filter options
        cache_key = f"prescriptions_filters_{self.request.user.id}_{getattr(self.request.user, 'current_hospital_id', 'none')}"

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

            # Get available creators (users who have created prescriptions)
            from django.contrib.auth import get_user_model

            User = get_user_model()
            available_creators = (
                User.objects.filter(
                    outpatientprescription_created__patient__id__in=accessible_patient_ids
                )
                .distinct()
                .only("id", "first_name", "last_name", "email")
            )

            filter_options = {
                "available_patients": accessible_patients,
                "available_creators": available_creators,
                "status_choices": OutpatientPrescription.STATUS_CHOICES,
            }
            # Cache for 5 minutes
            cache.set(cache_key, filter_options, 300)

        context["available_patients"] = filter_options["available_patients"]
        context["available_creators"] = filter_options["available_creators"]
        context["status_choices"] = filter_options["status_choices"]

        # Add permission information for each prescription
        if "prescriptions" in context:
            for prescription in context["prescriptions"]:
                prescription.can_edit = can_edit_event(self.request.user, prescription)
                prescription.can_delete = can_delete_event(self.request.user, prescription)

        return context


@method_decorator(hospital_context_required, name="dispatch")
class OutpatientPrescriptionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Create view for OutpatientPrescription instances with drug template integration.
    Handles both prescription form and item formset with AJAX functionality.
    """
    
    model = OutpatientPrescription
    form_class = OutpatientPrescriptionForm
    template_name = "outpatientprescriptions/outpatientprescription_create.html"
    permission_required = "events.add_event"
    
    def get_patient(self):
        """Get the patient from URL parameter."""
        patient_uuid = self.kwargs.get('patient_uuid')
        if patient_uuid:
            patient = get_object_or_404(Patient, id=patient_uuid)
            # Check if user can access this patient
            if not can_access_patient(self.request.user, patient):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied(
                    "You don't have permission to access this patient"
                )
            return patient
        return None
    
    def get_form_kwargs(self):
        """Pass user to form for permission checks."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_initial(self):
        """Set initial form data including patient if specified."""
        initial = super().get_initial()
        patient = self.get_patient()
        if patient:
            initial['patient'] = patient
        return initial
    
    def get_context_data(self, **kwargs):
        """Add formset and additional context data."""
        context = super().get_context_data(**kwargs)
        
        # Get patient from URL if specified
        patient = self.get_patient()
        if patient:
            context['patient'] = patient
        
        # Initialize formset with user context
        if self.request.POST:
            formset = PrescriptionItemFormSetHelper.get_formset_with_user(
                self.request.user, self.request.POST
            )
        else:
            formset = PrescriptionItemFormSetHelper.get_formset_with_user(
                self.request.user
            )
        
        # Prepare formset data for template
        formset_data = PrescriptionItemFormSetHelper.prepare_formset_data(formset)
        context.update(formset_data)
        
        # Add prescription template items (complete templates with quantities)
        context['prescription_template_items'] = PrescriptionTemplateItem.objects.filter(
            Q(template__creator=self.request.user) | Q(template__is_public=True)
        ).select_related('template').order_by('template__name', 'order', 'drug_name')
        
        # Add drug templates for manual entry/autocomplete functionality
        context['drug_templates'] = DrugTemplate.objects.filter(
            Q(creator=self.request.user) | Q(is_public=True)
        ).order_by('name')
        
        # Add prescription templates from sample content
        context['prescription_templates'] = SampleContent.objects.filter(
            event_type=Event.OUTPT_PRESCRIPTION_EVENT
        ).order_by('title')
        
        # Add available patients for selection if no patient specified
        if not patient:
            from apps.core.permissions.cache import get_user_accessible_patients
            accessible_patient_ids = get_user_accessible_patients(self.request.user)
            if accessible_patient_ids:
                context['available_patients'] = Patient.objects.filter(
                    id__in=accessible_patient_ids
                ).only("id", "name", "fiscal_number").order_by('name')
            else:
                context['available_patients'] = Patient.objects.none()
        
        return context
    
    def form_valid(self, form):
        """Handle form validation including formset."""
        context = self.get_context_data()
        formset = PrescriptionItemFormSetHelper.get_formset_with_user(
            self.request.user, self.request.POST
        )
        
        if form.is_valid() and formset.is_valid():
            # Save the main prescription
            self.object = form.save(commit=False)
            self.object.created_by = self.request.user
            self.object.updated_by = self.request.user
            self.object.save()
            
            # Save the formset
            formset.instance = self.object
            formset.save()
            
            messages.success(
                self.request,
                f"Receita para {self.object.patient.name} criada com sucesso!"
            )
            
            return super().form_valid(form)
        else:
            # Add formset to context for error display
            formset_data = PrescriptionItemFormSetHelper.prepare_formset_data(formset)
            context.update(formset_data)
            return self.render_to_response(context)
    
    def get_success_url(self):
        """Redirect to patient timeline after successful creation."""
        from django.urls import reverse
        return reverse(
            'events:patient_events_list',
            kwargs={'patient_id': self.object.patient.id}
        )


@login_required
def get_drug_template_data(request, template_id):
    """
    AJAX view to get drug template data by ID.
    """
    try:
        template = get_object_or_404(DrugTemplate, id=template_id)
        
        # Check if user has access to this template
        if not template.is_public and template.creator != request.user:
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        
        data = {
            'id': str(template.id),
            'name': template.name,
            'presentation': template.presentation,
            'usage_instructions': template.usage_instructions,
        }
        
        return JsonResponse(data)
        
    except DrugTemplate.DoesNotExist:
        return JsonResponse({'error': 'Template não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Erro interno'}, status=500)


@login_required
def search_drug_templates(request):
    """
    AJAX view to search drug templates by name for autocomplete functionality.
    """
    query = request.GET.get('q', '').strip()
    limit = min(int(request.GET.get('limit', 10)), 50)  # Max 50 results
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    try:
        # Filter templates by user access and search query
        templates = DrugTemplate.objects.filter(
            Q(creator=request.user) | Q(is_public=True)
        ).filter(
            Q(name__icontains=query) | Q(presentation__icontains=query)
        ).select_related('creator').order_by('name')[:limit]
        
        results = []
        for template in templates:
            results.append({
                'id': str(template.id),
                'name': template.name,
                'presentation': template.presentation,
                'usage_instructions': template.usage_instructions,
                'display_text': f"{template.name} - {template.presentation}",
                'creator': template.creator.get_full_name() if template.creator else 'Sistema',
                'is_public': template.is_public,
            })
        
        return JsonResponse({
            'results': results,
            'total': len(results),
            'query': query
        })
        
    except Exception as e:
        return JsonResponse({'error': 'Erro na busca'}, status=500)


@method_decorator(hospital_context_required, name="dispatch")
class OutpatientPrescriptionDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for OutpatientPrescription instances showing complete prescription information.
    """
    
    model = OutpatientPrescription
    template_name = "outpatientprescriptions/outpatientprescription_detail.html"
    context_object_name = "prescription"
    
    def get_queryset(self):
        """Filter queryset to ensure proper permissions and optimized queries."""
        return (
            OutpatientPrescription.objects
            .select_related("patient", "created_by", "updated_by")
            .prefetch_related(
                "patient__current_hospital", 
                "patient__hospitalrecord_set",
                "items"
            )
        )
    
    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)
        
        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied(
                "You don't have permission to access this patient's prescriptions"
            )
        
        return obj
    
    def get_context_data(self, **kwargs):
        """Add permission checks and additional context data."""
        context = super().get_context_data(**kwargs)
        
        # Add permission information
        context['can_edit'] = can_edit_event(self.request.user, self.object)
        context['can_delete'] = can_delete_event(self.request.user, self.object)
        
        # Add prescription items ordered by their order field
        context['prescription_items'] = self.object.items.order_by('order')
        
        # Add timeline URL for patient
        from django.urls import reverse
        context['patient_timeline_url'] = reverse(
            'events:patient_events_list', 
            kwargs={'patient_id': self.object.patient.id}
        )
        
        return context


@method_decorator(can_edit_event_required, name="dispatch")
@method_decorator(hospital_context_required, name="dispatch")
class OutpatientPrescriptionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Update view for OutpatientPrescription instances with 24-hour edit window check.
    Handles both prescription form and item formset updates.
    """
    
    model = OutpatientPrescription
    form_class = OutpatientPrescriptionForm
    template_name = "outpatientprescriptions/outpatientprescription_update.html"
    permission_required = "events.change_event"
    
    def get_queryset(self):
        """Filter queryset to ensure proper permissions and optimized queries."""
        return (
            OutpatientPrescription.objects
            .select_related("patient", "created_by", "updated_by")
            .prefetch_related(
                "patient__current_hospital", 
                "patient__hospitalrecord_set",
                "items"
            )
        )
    
    def get_form_kwargs(self):
        """Pass user to form for permission checks."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add formset and additional context data."""
        context = super().get_context_data(**kwargs)
        
        # Add patient info
        context['patient'] = self.object.patient
        
        # Initialize formset with existing items
        if self.request.POST:
            formset = PrescriptionItemFormSetHelper.get_formset_with_user(
                self.request.user, self.request.POST, instance=self.object
            )
        else:
            formset = PrescriptionItemFormSetHelper.get_formset_with_user(
                self.request.user, instance=self.object
            )
        
        # Prepare formset data for template
        formset_data = PrescriptionItemFormSetHelper.prepare_formset_data(formset)
        context.update(formset_data)
        
        # Add drug templates for AJAX functionality
        context['drug_templates'] = DrugTemplate.objects.filter(
            Q(creator=self.request.user) | Q(is_public=True)
        ).order_by('name')
        
        # Add prescription templates from sample content
        context['prescription_templates'] = SampleContent.objects.filter(
            event_type=Event.OUTPT_PRESCRIPTION_EVENT
        ).order_by('title')
        
        # Add permission information
        context['can_edit'] = can_edit_event(self.request.user, self.object)
        context['can_delete'] = can_delete_event(self.request.user, self.object)
        
        # Add timeline URL for patient
        from django.urls import reverse
        context['patient_timeline_url'] = reverse(
            'events:patient_events_list', 
            kwargs={'patient_id': self.object.patient.id}
        )
        
        return context
    
    def form_valid(self, form):
        """Handle form validation including formset and audit trail."""
        context = self.get_context_data()
        formset = PrescriptionItemFormSetHelper.get_formset_with_user(
            self.request.user, self.request.POST, instance=self.object
        )
        
        if form.is_valid() and formset.is_valid():
            # Save the main prescription
            self.object = form.save(commit=False)
            self.object.updated_by = self.request.user
            self.object.updated_at = timezone.now()
            self.object.save()
            
            # Save the formset
            formset.instance = self.object
            formset.save()
            
            messages.success(
                self.request,
                f"Receita para {self.object.patient.name} atualizada com sucesso!"
            )
            
            return super().form_valid(form)
        else:
            # Add formset to context for error display
            formset_data = PrescriptionItemFormSetHelper.prepare_formset_data(formset)
            context.update(formset_data)
            return self.render_to_response(context)
    
    def get_success_url(self):
        """Redirect to prescription detail after successful update."""
        return self.object.get_absolute_url()


@method_decorator(hospital_context_required, name="dispatch")
class OutpatientPrescriptionPrintView(LoginRequiredMixin, DetailView):
    """
    Print view for OutpatientPrescription instances with print-optimized template.
    """
    
    model = OutpatientPrescription
    template_name = "outpatientprescriptions/outpatientprescription_print.html"
    context_object_name = "prescription"
    
    def get_queryset(self):
        """Filter queryset to ensure proper permissions and optimized queries."""
        return (
            OutpatientPrescription.objects
            .select_related("patient", "created_by", "updated_by")
            .prefetch_related(
                "patient__current_hospital", 
                "patient__hospitalrecord_set",
                "items"
            )
        )
    
    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)
        
        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied(
                "You don't have permission to access this patient's prescriptions"
            )
        
        return obj
    
    def get_context_data(self, **kwargs):
        """Add prescription items and medical information for print template."""
        context = super().get_context_data(**kwargs)
        
        # Add prescription items ordered by their order field
        context['prescription_items'] = self.object.items.order_by('order')
        
        return context


@method_decorator(hospital_context_required, name="dispatch")
class OutpatientPrescriptionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Delete view for OutpatientPrescription instances with permission checking.
    """
    
    model = OutpatientPrescription
    template_name = "outpatientprescriptions/outpatientprescription_confirm_delete.html"
    context_object_name = "prescription"
    permission_required = "events.delete_event"
    
    def get_success_url(self):
        """Redirect to patient timeline after successful deletion."""
        from django.urls import reverse
        return reverse(
            'events:patient_events_list', 
            kwargs={'patient_id': self.object.patient.id}
        )
    
    def get_object(self, queryset=None):
        """Get object and check patient access and delete permissions."""
        obj = super().get_object(queryset)
        
        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied(
                "You don't have permission to access this patient's prescriptions"
            )
        
        # Check if user can delete this event
        if not can_delete_event(self.request.user, obj):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied(
                "You don't have permission to delete this prescription"
            )
        
        return obj
    
    def get_queryset(self):
        """Filter queryset to ensure proper permissions and optimized queries."""
        return (
            OutpatientPrescription.objects
            .select_related("patient", "created_by", "updated_by")
            .prefetch_related(
                "patient__current_hospital", 
                "patient__hospitalrecord_set",
                "items"
            )
        )
    
    def delete(self, request, *args, **kwargs):
        """Handle successful deletion."""
        prescription = self.get_object()
        messages.success(
            request,
            f"Receita para {prescription.patient.name} excluída com sucesso!"
        )
        return super().delete(request, *args, **kwargs)


@login_required 
def get_prescription_template_data(request, template_id):
    """
    AJAX view to get prescription template data by ID.
    """
    try:
        template = get_object_or_404(SampleContent, id=template_id, event_type=Event.OUTPT_PRESCRIPTION_EVENT)
        
        data = {
            'id': str(template.id),
            'title': template.title,
            'content': template.content,
        }
        
        return JsonResponse(data)
        
    except SampleContent.DoesNotExist:
        return JsonResponse({'error': 'Template não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Erro interno'}, status=500)
