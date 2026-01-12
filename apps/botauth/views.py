"""
Views for Matrix binding management.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, TemplateView
from django.http import HttpResponseBadRequest

from .models import MatrixUserBinding
from .services import MatrixBindingService
from .forms import MatrixBindingForm


class MatrixBindingCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new Matrix binding."""
    
    model = MatrixUserBinding
    form_class = MatrixBindingForm
    template_name = 'botauth/binding_create.html'
    success_url = reverse_lazy('botauth:binding_status')
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user already has a binding
        if MatrixUserBinding.objects.filter(user=request.user).exists():
            messages.info(request, 'Você já possui uma vinculação Matrix.')
            return redirect('botauth:binding_status')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        try:
            binding, created = MatrixBindingService.create_binding(
                user=self.request.user,
                matrix_id=form.cleaned_data['matrix_id'],
                request=self.request
            )
            if created:
                messages.success(
                    self.request, 
                    'Vinculação criada. Verifique seu email para confirmar.'
                )
                # TODO: Send verification email
            return redirect(self.success_url)
        except ValueError as e:
            form.add_error('matrix_id', str(e))
            return self.form_invalid(form)


class MatrixBindingStatusView(LoginRequiredMixin, TemplateView):
    """View for showing Matrix binding status."""
    
    template_name = 'botauth/binding_status.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['binding'] = MatrixUserBinding.objects.filter(
            user=self.request.user
        ).first()
        return context


class MatrixBindingVerifyView(TemplateView):
    """View for verifying a Matrix binding via token."""
    
    template_name = 'botauth/binding_verify.html'
    
    def get(self, request, token):
        try:
            binding = MatrixBindingService.verify_binding(token, request)
            messages.success(request, 'Vinculação Matrix verificada com sucesso!')
            return redirect('botauth:binding_status')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('core:dashboard')


class MatrixBindingDeleteView(LoginRequiredMixin, DeleteView):
    """View for revoking a Matrix binding."""
    
    model = MatrixUserBinding
    template_name = 'botauth/binding_confirm_delete.html'
    success_url = reverse_lazy('botauth:binding_status')
    
    def get_queryset(self):
        # Users can only delete their own binding
        return MatrixUserBinding.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        MatrixBindingService.revoke_binding(
            self.get_object(),
            request=self.request,
            reason='User requested revocation'
        )
        messages.success(self.request, 'Vinculação Matrix removida.')
        return redirect(self.success_url)