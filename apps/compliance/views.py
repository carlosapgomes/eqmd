from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.views.generic import CreateView, ListView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.urls import reverse_lazy
from .models import PatientDataRequest, PrivacyPolicy, DataProcessingNotice
from .forms import PatientDataRequestCreationForm, PatientDataRequestManagementForm
from .services.data_export import PatientDataExportService
import markdown


class PatientDataRequestCreateView(LoginRequiredMixin, CreateView):
    """Staff view to create patient data requests during in-person visits"""
    model = PatientDataRequest
    form_class = PatientDataRequestCreationForm
    template_name = 'admin/compliance/data_request_create.html'
    success_url = reverse_lazy('compliance:data_request_list')

    def form_valid(self, form):
        # Set the staff member who created the request
        form.instance.created_by = self.request.user
        form.instance.assigned_to = self.request.user  # Initially assign to creator
        
        # Save the request
        response = super().form_valid(form)

        # Send confirmation email to requester
        self.send_confirmation_email(self.object)

        # Notify DPO if different from creator
        self.notify_dpo_new_request(self.object)

        messages.success(
            self.request,
            f'Solicitação LGPD criada com sucesso: {self.object.request_id}'
        )

        return response

    def send_confirmation_email(self, request_obj):
        """Send confirmation email to requester"""
        subject = f'Confirmação de Solicitação LGPD - {request_obj.request_id}'
        message = f"""
        Prezado(a) {request_obj.requester_name},

        Sua solicitação de dados foi registrada em nosso sistema:

        Número da Solicitação: {request_obj.request_id}
        Tipo: {request_obj.get_request_type_display()}
        Data da Solicitação: {request_obj.requested_at.strftime('%d/%m/%Y %H:%M')}
        Prazo para Resposta: {request_obj.due_date.strftime('%d/%m/%Y')}

        Descrição: {request_obj.description}

        Sua solicitação está sendo processada conforme estabelecido pela LGPD. 
        Você receberá uma resposta no email {request_obj.requester_email} em até 15 dias.

        Para qualquer dúvida, entre em contato conosco presencialmente ou pelo 
        telefone do hospital.

        Atenciosamente,
        Equipe de Proteção de Dados
        """

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [request_obj.requester_email],
                fail_silently=True
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to send confirmation email: {e}")

    def notify_dpo_new_request(self, request_obj):
        """Notify DPO about new data request if needed"""
        from apps.compliance.models import LGPDComplianceSettings

        try:
            settings_obj = LGPDComplianceSettings.objects.first()
            if settings_obj and settings_obj.dpo_email and settings_obj.dpo_email != self.request.user.email:
                subject = f'Nova Solicitação LGPD - {request_obj.request_id}'
                message = f"""
                Nova solicitação LGPD registrada por: {self.request.user.get_full_name()}

                ID: {request_obj.request_id}
                Tipo: {request_obj.get_request_type_display()}
                Solicitante: {request_obj.requester_name}
                Email: {request_obj.requester_email}
                Paciente: {request_obj.patient_name_provided}
                Prioridade: {request_obj.get_priority_display()}
                Prazo: {request_obj.due_date.strftime('%d/%m/%Y')}

                Acesse o admin para revisar a solicitação.
                """

                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings_obj.dpo_email],
                    fail_silently=True
                )
        except Exception as e:
            print(f"Failed to notify DPO: {e}")


@login_required
def patient_data_export(request, request_id):
    """Export patient data for approved requests"""
    data_request = get_object_or_404(
        PatientDataRequest,
        request_id=request_id,
        status='approved'
    )

    if not data_request.patient:
        raise Http404("Patient not found for this request")

    # Check permissions (staff only)
    if not request.user.is_staff:
        raise Http404("Permission denied")

    # Export data
    export_service = PatientDataExportService(data_request.patient)
    response = export_service.export_data(
        format_type=data_request.data_export_format,
        request_id=request_id
    )

    # Update request status
    data_request.status = 'completed'
    data_request.response_sent_at = timezone.now()
    data_request.save()

    return response


class PatientDataRequestListView(LoginRequiredMixin, ListView):
    """Staff view to list and manage data requests"""
    model = PatientDataRequest
    template_name = 'admin/compliance/data_request_list.html'
    context_object_name = 'requests'
    paginate_by = 20

    def get_queryset(self):
        queryset = PatientDataRequest.objects.all()

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by overdue
        overdue = self.request.GET.get('overdue')
        if overdue == 'true':
            queryset = queryset.filter(due_date__lt=timezone.now())

        return queryset.order_by('-requested_at')


class PatientDataRequestDetailView(LoginRequiredMixin, DetailView):
    """Staff view to manage individual data requests"""
    model = PatientDataRequest
    template_name = 'admin/compliance/data_request_detail.html'
    context_object_name = 'data_request'

    def get_object(self):
        return get_object_or_404(PatientDataRequest, request_id=self.kwargs['request_id'])


class PatientDataRequestUpdateView(LoginRequiredMixin, UpdateView):
    """Staff view to update data requests"""
    model = PatientDataRequest
    form_class = PatientDataRequestManagementForm
    template_name = 'admin/compliance/data_request_update.html'
    context_object_name = 'data_request'

    def get_object(self):
        return get_object_or_404(PatientDataRequest, request_id=self.kwargs['request_id'])

    def get_success_url(self):
        return reverse_lazy('compliance:data_request_detail', kwargs={'request_id': self.object.request_id})

    def form_valid(self, form):
        if form.cleaned_data.get('status') in ['approved', 'rejected']:
            form.instance.reviewed_by = self.request.user
            form.instance.reviewed_at = timezone.now()

        messages.success(self.request, 'Solicitação atualizada com sucesso!')
        return super().form_valid(form)


def privacy_policy(request, policy_type='main'):
    """Display current privacy policy"""
    policy = get_object_or_404(
        PrivacyPolicy,
        policy_type=policy_type,
        is_active=True
    )
    
    # Convert markdown to HTML
    content_html = markdown.markdown(policy.content_markdown, extensions=['tables', 'toc'])
    
    context = {
        'policy': policy,
        'content_html': content_html,
    }
    
    return render(request, 'compliance/privacy_policy.html', context)


def data_processing_notice(request, context):
    """Display data processing notice for specific context"""
    notice = get_object_or_404(
        DataProcessingNotice,
        context=context,
        is_active=True
    )
    
    return render(request, 'compliance/data_processing_notice.html', {'notice': notice})


class PrivacyPolicyDetailView(DetailView):
    """Detailed privacy policy view with version history"""
    model = PrivacyPolicy
    template_name = 'compliance/privacy_policy_detail.html'
    context_object_name = 'policy'
    
    def get_object(self):
        policy_type = self.kwargs.get('policy_type', 'main')
        return get_object_or_404(
            PrivacyPolicy,
            policy_type=policy_type,
            is_active=True
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add version history
        context['version_history'] = PrivacyPolicy.objects.filter(
            policy_type=self.object.policy_type
        ).order_by('-effective_date')[:5]
        
        # Convert markdown to HTML
        context['content_html'] = markdown.markdown(
            self.object.content_markdown,
            extensions=['tables', 'toc', 'codehilite']
        )
        
        return context
