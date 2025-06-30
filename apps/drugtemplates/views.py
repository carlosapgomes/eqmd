from django.shortcuts import render
from django.views.generic import DetailView, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from apps.core.permissions.decorators import doctor_required
from .models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem
from .forms import DrugTemplateForm, PrescriptionTemplateForm, PrescriptionTemplateItemFormSet


class DrugTemplateListView(LoginRequiredMixin, ListView):
    """
    List view for drug templates with filtering and pagination.
    Shows public templates + user's private templates.
    """
    model = DrugTemplate
    template_name = 'drugtemplates/drugtemplate_list.html'
    context_object_name = 'drug_templates'
    paginate_by = 20

    def get_queryset(self):
        """
        Filter templates to show public templates + user's private templates.
        Apply GET parameter filters: name search, creator filter, visibility filter.
        """
        # Base query: public templates + user's private templates
        queryset = DrugTemplate.objects.filter(
            Q(is_public=True) | Q(creator=self.request.user)
        ).select_related('creator')
        
        # Name search filter
        name_search = self.request.GET.get('name', '').strip()
        if name_search:
            queryset = queryset.filter(name__icontains=name_search)
        
        # Creator filter
        creator_filter = self.request.GET.get('creator')
        if creator_filter and creator_filter.isdigit():
            queryset = queryset.filter(creator_id=int(creator_filter))
        
        # Visibility filter
        visibility_filter = self.request.GET.get('visibility')
        if visibility_filter == 'public':
            queryset = queryset.filter(is_public=True)
        elif visibility_filter == 'private':
            queryset = queryset.filter(is_public=False, creator=self.request.user)
        elif visibility_filter == 'mine':
            queryset = queryset.filter(creator=self.request.user)
        
        # Sorting
        sort_by = self.request.GET.get('sort', 'name')
        if sort_by == 'created_at':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'created_at_asc':
            queryset = queryset.order_by('created_at')
        elif sort_by == 'name_desc':
            queryset = queryset.order_by('-name')
        else:  # default: name ascending
            queryset = queryset.order_by('name')
        
        return queryset

    def get_context_data(self, **kwargs):
        """Add filter context for template rendering."""
        context = super().get_context_data(**kwargs)
        
        # Get available creators (only those with accessible templates)
        available_creators = DrugTemplate.objects.filter(
            Q(is_public=True) | Q(creator=self.request.user)
        ).select_related('creator').values_list(
            'creator__id', 'creator__first_name', 'creator__last_name'
        ).distinct()
        
        context.update({
            'name_search': self.request.GET.get('name', ''),
            'selected_creator': self.request.GET.get('creator', ''),
            'selected_visibility': self.request.GET.get('visibility', ''),
            'selected_sort': self.request.GET.get('sort', 'name'),
            'available_creators': available_creators,
        })
        
        return context


class DrugTemplateDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for DrugTemplate with usage statistics and permission checks.
    Shows template details, usage count, and provides edit/delete access based on permissions.
    """
    model = DrugTemplate
    template_name = 'drugtemplates/drugtemplate_detail.html'
    context_object_name = 'drugtemplate'

    def get_object(self, queryset=None):
        """Get template object with access permission check."""
        template = super().get_object(queryset)
        
        # Check if user can access this template
        if not template.is_public and template.creator != self.request.user:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Você não tem permissão para acessar este template privado.")
        
        return template

    def get_context_data(self, **kwargs):
        """Add permission context."""
        context = super().get_context_data(**kwargs)
        template = self.object
        
        # Permission checks for edit/delete actions
        context['can_edit_template'] = self.can_edit_template(template)
        context['can_delete_template'] = self.can_delete_template(template)
        
        return context

    def can_edit_template(self, template):
        """Check if user can edit this template."""
        # Template creator can always edit
        return template.creator == self.request.user

    def can_delete_template(self, template):
        """Check if user can delete this template."""
        # Only template creator can delete
        return template.creator == self.request.user


@method_decorator(doctor_required, name='dispatch')
class DrugTemplateCreateView(LoginRequiredMixin, CreateView):
    """
    Create view for DrugTemplate with proper form handling.
    Requires doctor privileges and automatically sets creator to current user.
    """
    model = DrugTemplate
    form_class = DrugTemplateForm
    template_name = 'drugtemplates/drugtemplate_create_form.html'
    success_url = reverse_lazy('drugtemplates:list')

    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Set the creator to the current user and add success message."""
        form.instance.creator = self.request.user
        messages.success(
            self.request,
            f'Template "{form.instance.name}" criado com sucesso!'
        )
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect to the detail view of the created template."""
        return self.object.get_absolute_url()


class DrugTemplateUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update view for DrugTemplate with creator-only permission checks.
    Only the template creator can edit their own templates.
    """
    model = DrugTemplate
    form_class = DrugTemplateForm
    template_name = 'drugtemplates/drugtemplate_update_form.html'
    context_object_name = 'drugtemplate'

    def get_object(self, queryset=None):
        """Get template object with creator permission check."""
        template = super().get_object(queryset)
        
        # Check if user is the creator of this template
        if template.creator != self.request.user:
            raise PermissionDenied("Você não tem permissão para editar este template. Apenas o criador pode editá-lo.")
        
        return template

    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Add success message after successful update."""
        messages.success(
            self.request,
            f'Template "{form.instance.name}" atualizado com sucesso!'
        )
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect to the detail view of the updated template."""
        return self.object.get_absolute_url()


class DrugTemplateDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete view for DrugTemplate with creator-only permission checks.
    Only the template creator can delete their own templates.
    Checks for usage in prescriptions before deletion.
    """
    model = DrugTemplate
    template_name = 'drugtemplates/drugtemplate_confirm_delete.html'
    context_object_name = 'drugtemplate'
    success_url = reverse_lazy('drugtemplates:list')

    def get_object(self, queryset=None):
        """Get template object with creator permission check."""
        template = super().get_object(queryset)
        
        # Check if user is the creator of this template
        if template.creator != self.request.user:
            raise PermissionDenied("Você não tem permissão para excluir este template. Apenas o criador pode excluí-lo.")
        
        return template

    def get_context_data(self, **kwargs):
        """Add usage statistics for information display."""
        context = super().get_context_data(**kwargs)
        template = self.object
        
        # Get template usage statistics for informational display
        # Note: This will be updated when outpatientprescriptions app is implemented
        usage_count = 0  # TODO: Count actual prescription usage when model exists
        
        context.update({
            'usage_count': usage_count,
        })
        
        return context

    def delete(self, request, *args, **kwargs):
        """Handle template deletion with success message."""
        template = self.get_object()
        template_name = template.name
        
        # Template deletion is safe - prescription items contain copied data
        # Template ID is only used for usage statistics tracking
        messages.success(
            request,
            f'Template "{template_name}" excluído com sucesso!'
        )
        
        return super().delete(request, *args, **kwargs)


# Prescription Template Views

class PrescriptionTemplateListView(LoginRequiredMixin, ListView):
    """
    List view for prescription templates with filtering and pagination.
    Shows public templates + user's private templates.
    """
    model = PrescriptionTemplate
    template_name = 'drugtemplates/prescriptiontemplate_list.html'
    context_object_name = 'prescription_templates'
    paginate_by = 20

    def get_queryset(self):
        """
        Filter templates to show public templates + user's private templates.
        Apply GET parameter filters: name search, creator filter, visibility filter.
        """
        # Base query: public templates + user's private templates
        queryset = PrescriptionTemplate.objects.filter(
            Q(is_public=True) | Q(creator=self.request.user)
        ).select_related('creator').prefetch_related('items')
        
        # Name search filter
        name_search = self.request.GET.get('name', '').strip()
        if name_search:
            queryset = queryset.filter(name__icontains=name_search)
        
        # Creator filter
        creator_filter = self.request.GET.get('creator')
        if creator_filter and creator_filter.isdigit():
            queryset = queryset.filter(creator_id=int(creator_filter))
        
        # Visibility filter
        visibility_filter = self.request.GET.get('visibility')
        if visibility_filter == 'public':
            queryset = queryset.filter(is_public=True)
        elif visibility_filter == 'private':
            queryset = queryset.filter(is_public=False, creator=self.request.user)
        elif visibility_filter == 'mine':
            queryset = queryset.filter(creator=self.request.user)
        
        # Sorting
        sort_by = self.request.GET.get('sort', 'name')
        if sort_by == 'created_at':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'created_at_asc':
            queryset = queryset.order_by('created_at')
        elif sort_by == 'name_desc':
            queryset = queryset.order_by('-name')
        else:  # default: name ascending
            queryset = queryset.order_by('name')
        
        return queryset

    def get_context_data(self, **kwargs):
        """Add filter context for template rendering."""
        context = super().get_context_data(**kwargs)
        
        # Get available creators (only those with accessible templates)
        available_creators = PrescriptionTemplate.objects.filter(
            Q(is_public=True) | Q(creator=self.request.user)
        ).select_related('creator').values_list(
            'creator__id', 'creator__first_name', 'creator__last_name'
        ).distinct()
        
        context.update({
            'name_search': self.request.GET.get('name', ''),
            'selected_creator': self.request.GET.get('creator', ''),
            'selected_visibility': self.request.GET.get('visibility', ''),
            'selected_sort': self.request.GET.get('sort', 'name'),
            'available_creators': available_creators,
        })
        
        return context


class PrescriptionTemplateDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for PrescriptionTemplate with usage statistics and permission checks.
    Shows template details, items, and provides edit/delete access based on permissions.
    """
    model = PrescriptionTemplate
    template_name = 'drugtemplates/prescriptiontemplate_detail.html'
    context_object_name = 'prescription_template'

    def get_object(self, queryset=None):
        """Get template object with access permission check."""
        template = super().get_object(queryset)
        
        # Check if user can access this template
        if not template.is_public and template.creator != self.request.user:
            raise PermissionDenied("Você não tem permissão para acessar este template privado.")
        
        return template

    def get_context_data(self, **kwargs):
        """Add permission context and template items."""
        context = super().get_context_data(**kwargs)
        template = self.object
        
        # Get template items ordered by order field
        template_items = template.items.all().order_by('order', 'drug_name')
        
        # Permission checks for edit/delete actions
        context['can_edit_template'] = self.can_edit_template(template)
        context['can_delete_template'] = self.can_delete_template(template)
        context['template_items'] = template_items
        context['items_count'] = template_items.count()
        
        return context

    def can_edit_template(self, template):
        """Check if user can edit this template."""
        # Template creator can always edit
        return template.creator == self.request.user

    def can_delete_template(self, template):
        """Check if user can delete this template."""
        # Only template creator can delete
        return template.creator == self.request.user


@method_decorator(doctor_required, name='dispatch')
class PrescriptionTemplateCreateView(LoginRequiredMixin, CreateView):
    """
    Create view for PrescriptionTemplate with formset handling.
    Requires doctor privileges and automatically sets creator to current user.
    """
    model = PrescriptionTemplate
    form_class = PrescriptionTemplateForm
    template_name = 'drugtemplates/prescriptiontemplate_create_form.html'

    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Add formset to context."""
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = PrescriptionTemplateItemFormSet(self.request.POST)
        else:
            context['formset'] = PrescriptionTemplateItemFormSet()
        return context

    def form_valid(self, form):
        """Handle form and formset validation."""
        context = self.get_context_data()
        formset = context['formset']
        
        # Set the creator to the current user
        form.instance.creator = self.request.user
        
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            
            messages.success(
                self.request,
                f'Template de prescrição "{form.instance.name}" criado com sucesso!'
            )
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        """Redirect to the detail view of the created template."""
        return self.object.get_absolute_url()


class PrescriptionTemplateUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update view for PrescriptionTemplate with formset handling and creator-only permission checks.
    Only the template creator can edit their own templates.
    """
    model = PrescriptionTemplate
    form_class = PrescriptionTemplateForm
    template_name = 'drugtemplates/prescriptiontemplate_update_form.html'
    context_object_name = 'prescription_template'

    def get_object(self, queryset=None):
        """Get template object with creator permission check."""
        template = super().get_object(queryset)
        
        # Check if user is the creator of this template
        if template.creator != self.request.user:
            raise PermissionDenied("Você não tem permissão para editar este template. Apenas o criador pode editá-lo.")
        
        return template

    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Add formset to context."""
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = PrescriptionTemplateItemFormSet(
                self.request.POST, 
                instance=self.object
            )
        else:
            context['formset'] = PrescriptionTemplateItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        """Handle form and formset validation."""
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            
            messages.success(
                self.request,
                f'Template de prescrição "{form.instance.name}" atualizado com sucesso!'
            )
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        """Redirect to the detail view of the updated template."""
        return self.object.get_absolute_url()


class PrescriptionTemplateDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete view for PrescriptionTemplate with creator-only permission checks.
    Only the template creator can delete their own templates.
    """
    model = PrescriptionTemplate
    template_name = 'drugtemplates/prescriptiontemplate_confirm_delete.html'
    context_object_name = 'prescription_template'
    success_url = reverse_lazy('drugtemplates:prescription_list')

    def get_object(self, queryset=None):
        """Get template object with creator permission check."""
        template = super().get_object(queryset)
        
        # Check if user is the creator of this template
        if template.creator != self.request.user:
            raise PermissionDenied("Você não tem permissão para excluir este template. Apenas o criador pode excluí-lo.")
        
        return template

    def get_context_data(self, **kwargs):
        """Add template items and usage statistics for information display."""
        context = super().get_context_data(**kwargs)
        template = self.object
        
        # Get template items for display
        template_items = template.items.all().order_by('order', 'drug_name')
        
        # Get template usage statistics for informational display
        # Note: This will be updated when outpatientprescriptions app is implemented
        usage_count = 0  # TODO: Count actual prescription usage when model exists
        
        context.update({
            'template_items': template_items,
            'items_count': template_items.count(),
            'usage_count': usage_count,
        })
        
        return context

    def delete(self, request, *args, **kwargs):
        """Handle template deletion with success message."""
        template = self.get_object()
        template_name = template.name
        
        messages.success(
            request,
            f'Template de prescrição "{template_name}" excluído com sucesso!'
        )
        
        return super().delete(request, *args, **kwargs)
