"""
Views for Matrix binding management and OIDC authorization.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, TemplateView, ListView, DetailView, View
from django.http import HttpResponseBadRequest
from django.utils import timezone
from django.utils.decorators import method_decorator
from oidc_provider.views import AuthorizeView as BaseAuthorizeView

from .models import MatrixUserBinding
from .services import MatrixBindingService
from .forms import MatrixBindingForm
from .promotion_service import DraftPromotionService


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


class MyDraftsView(LoginRequiredMixin, ListView):
    """View for physicians to see their pending drafts."""
    
    template_name = 'botauth/my_drafts.html'
    context_object_name = 'drafts'
    
    def get_queryset(self):
        from apps.events.models import Event
        return Event.all_objects.filter(
            is_draft=True,
            draft_delegated_by=self.request.user,
            draft_expires_at__gt=timezone.now()
        ).select_subclasses().order_by('-created_at')


class DraftDetailView(LoginRequiredMixin, DetailView):
    """View draft details for review."""
    
    template_name = 'botauth/draft_detail.html'
    context_object_name = 'draft'
    
    def get_queryset(self):
        from apps.events.models import Event
        return Event.all_objects.filter(
            is_draft=True,
            draft_delegated_by=self.request.user
        ).select_subclasses()


class DraftPromoteView(LoginRequiredMixin, View):
    """Promote a draft to definitive document."""
    
    def post(self, request, pk):
        from apps.events.models import Event
        
        draft = get_object_or_404(
            Event.all_objects.filter(is_draft=True).select_subclasses(),
            pk=pk
        )
        
        try:
            promoted = DraftPromotionService.promote_draft(
                draft=draft,
                approving_user=request.user
            )
            messages.success(
                request,
                'Documento promovido com sucesso. Você é agora o autor do registro.'
            )
            return redirect(promoted.get_absolute_url())
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('botauth:my_drafts')


class DraftRejectView(LoginRequiredMixin, View):
    """Reject and delete a draft."""
    
    def post(self, request, pk):
        from apps.events.models import Event
        
        draft = get_object_or_404(
            Event.all_objects.filter(is_draft=True).select_subclasses(),
            pk=pk
        )
        
        reason = request.POST.get('reason', '')
        
        try:
            DraftPromotionService.reject_draft(
                draft=draft,
                rejecting_user=request.user,
                reason=reason
            )
            messages.success(request, 'Rascunho rejeitado e removido.')
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('botauth:my_drafts')


# =============================================================================
# OIDC Custom Authorization View
# =============================================================================


@method_decorator(login_required, name='dispatch')
class AuthorizeView(BaseAuthorizeView):
    """
    Custom OIDC authorization view with access control.
    
    Ensures that only active users can complete OIDC authorization flows.
    This prevents inactive users from accessing Matrix Synapse via SSO.
    """
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests to authorization endpoint."""
        # Check if user is active before proceeding
        if not request.user.is_authenticated:
            return super().get(request, *args, **kwargs)
            
        if not request.user.is_active:
            # User account is inactive, deny authorization
            context = {
                'error': 'access_denied',
                'error_description': 'Your account is currently inactive. Please contact your administrator.',
                'user': request.user,
            }
            return render(request, 'oidc_provider/error.html', context, status=403)
        
        # User is active, proceed with normal authorization flow
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """Handle POST requests to authorization endpoint."""
        # Check if user is active before proceeding
        if not request.user.is_authenticated:
            return super().post(request, *args, **kwargs)
            
        if not request.user.is_active:
            # User account is inactive, deny authorization
            context = {
                'error': 'access_denied', 
                'error_description': 'Your account is currently inactive. Please contact your administrator.',
                'user': request.user,
            }
            return render(request, 'oidc_provider/error.html', context, status=403)
        
        # User is active, proceed with normal authorization flow
        return super().post(request, *args, **kwargs)