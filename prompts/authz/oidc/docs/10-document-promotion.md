# Phase 10 – Document Promotion

## Goal

Implement the flow for promoting drafts to definitive documents, ensuring proper authorship transfer and audit trail.

## Prerequisites

- Phase 09 completed (Draft Lifecycle)
- All existing tests passing

## Tasks

### Task 10.1: Create Promotion Service

Create `apps/botauth/promotion_service.py`:

```python
"""
Service for promoting drafts to definitive documents.
"""

import logging
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger('security.promotion')


class DraftPromotionService:
    """Service for promoting bot-created drafts to definitive documents."""
    
    @classmethod
    @transaction.atomic
    def promote_draft(cls, draft, approving_user, modifications=None):
        """
        Promote a draft to a definitive document.
        
        Args:
            draft: The draft Event to promote
            approving_user: The physician approving the draft
            modifications: Optional dict of field updates
        
        Returns:
            The promoted event
        
        Raises:
            ValueError: If draft cannot be promoted
        """
        # Validate draft
        if not draft.is_draft:
            raise ValueError("Event is not a draft")
        
        if draft.draft_expires_at and draft.draft_expires_at < timezone.now():
            raise ValueError("Draft has expired")
        
        # Validate approving user
        cls._validate_approving_user(draft, approving_user)
        
        # Apply modifications if provided
        if modifications:
            for field, value in modifications.items():
                if hasattr(draft, field) and field not in ('id', 'is_draft', 'created_by'):
                    setattr(draft, field, value)
        
        # Transfer authorship
        original_created_by = draft.created_by
        draft.created_by = approving_user
        draft.updated_by = approving_user
        
        # Clear draft status
        draft.is_draft = False
        draft.draft_promoted_at = timezone.now()
        draft.draft_promoted_by = approving_user
        
        # Update description to remove bot reference
        if 'via bot' in draft.description.lower() or 'rascunho' in draft.description.lower():
            draft.description = cls._clean_description(draft)
        
        # Save with history
        draft._change_reason = (
            f"Rascunho promovido a definitivo por {approving_user.get_full_name()}. "
            f"Originalmente criado via bot sob delegação de {original_created_by.get_full_name()}."
        )
        draft.save()
        
        logger.info(
            f"Draft promoted: id={draft.id}, "
            f"type={draft.get_event_type_display()}, "
            f"original_author={original_created_by.email}, "
            f"approved_by={approving_user.email}"
        )
        
        return draft
    
    @classmethod
    def _validate_approving_user(cls, draft, user):
        """Validate that the user can approve this draft."""
        from apps.core.permissions import is_doctor
        
        if not user.is_active:
            raise ValueError("Approving user is not active")
        
        if user.account_status not in ('active', 'expiring_soon'):
            raise ValueError("Approving user account status does not allow approval")
        
        # Only doctors/residents can approve clinical documents
        if not is_doctor(user):
            raise ValueError("Only doctors can approve clinical documents")
        
        # Optionally: only the delegating physician can approve
        # Uncomment to enforce this restriction:
        # if draft.draft_delegated_by and draft.draft_delegated_by != user:
        #     raise ValueError("Only the delegating physician can approve this draft")
    
    @classmethod
    def _clean_description(cls, draft):
        """Generate a clean description without bot references."""
        event_type = draft.get_event_type_display()
        patient_name = draft.patient.name if hasattr(draft, 'patient') else 'Paciente'
        date_str = draft.event_datetime.strftime('%d/%m/%Y %H:%M')
        return f"{event_type} - {patient_name} - {date_str}"
    
    @classmethod
    def reject_draft(cls, draft, rejecting_user, reason=''):
        """
        Reject and delete a draft.
        
        Args:
            draft: The draft to reject
            rejecting_user: The user rejecting
            reason: Optional reason for rejection
        """
        if not draft.is_draft:
            raise ValueError("Event is not a draft")
        
        logger.info(
            f"Draft rejected: id={draft.id}, "
            f"rejected_by={rejecting_user.email}, "
            f"reason={reason}"
        )
        
        # Hard delete the draft
        draft.delete()
```

### Task 10.2: Create Promotion Views

Add to `apps/botauth/views.py`:

```python
from django.views.generic import DetailView, View
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse
from apps.events.models import Event
from .promotion_service import DraftPromotionService


class DraftDetailView(LoginRequiredMixin, DetailView):
    """View draft details for review."""
    
    template_name = 'botauth/draft_detail.html'
    context_object_name = 'draft'
    
    def get_queryset(self):
        return Event.all_objects.filter(
            is_draft=True,
            draft_delegated_by=self.request.user
        ).select_subclasses()


class DraftPromoteView(LoginRequiredMixin, View):
    """Promote a draft to definitive document."""
    
    def post(self, request, pk):
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
                f'Documento promovido com sucesso. Você é agora o autor do registro.'
            )
            return redirect(promoted.get_absolute_url())
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('botauth:my_drafts')


class DraftRejectView(LoginRequiredMixin, View):
    """Reject and delete a draft."""
    
    def post(self, request, pk):
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
```

### Task 10.3: Create Templates

Create `apps/botauth/templates/botauth/my_drafts.html`:

```html
{% extends "base_app.html" %}
{% load i18n %}

{% block title %}Meus Rascunhos{% endblock %}

{% block content %}
<div class="container mt-4">
    <h2>Rascunhos Pendentes de Revisão</h2>
    
    {% if drafts %}
        <div class="alert alert-info">
            <i class="bi bi-info-circle"></i>
            Estes rascunhos foram criados por bots sob sua delegação. 
            Revise e aprove para torná-los documentos definitivos.
        </div>
        
        <div class="list-group">
            {% for draft in drafts %}
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">
                        {{ draft.get_event_type_display }} - {{ draft.patient.name }}
                    </h5>
                    <small class="text-muted">
                        Expira em {{ draft.draft_expires_at|timesince }}
                    </small>
                </div>
                <p class="mb-1">{{ draft.description }}</p>
                <small class="text-muted">
                    Criado via bot: {{ draft.draft_created_by_bot }}
                </small>
                <div class="mt-2">
                    <a href="{% url 'botauth:draft_detail' draft.pk %}" 
                       class="btn btn-sm btn-primary">
                        Revisar
                    </a>
                    <form method="post" action="{% url 'botauth:draft_reject' draft.pk %}" 
                          class="d-inline">
                        {% csrf_token %}
                        <button type="submit" class="btn btn-sm btn-outline-danger"
                                onclick="return confirm('Rejeitar este rascunho?')">
                            Rejeitar
                        </button>
                    </form>
                </div>
            </div>
            {% endfor %}
        </div>
    {% else %}
        <div class="alert alert-secondary">
            Nenhum rascunho pendente de revisão.
        </div>
    {% endif %}
</div>
{% endblock %}
```

### Task 10.4: Add URL Routes

Update `apps/botauth/urls.py`:

```python
urlpatterns = [
    # ... existing URLs ...
    
    # Draft management
    path('drafts/', views.MyDraftsView.as_view(), name='my_drafts'),
    path('drafts/<uuid:pk>/', views.DraftDetailView.as_view(), name='draft_detail'),
    path('drafts/<uuid:pk>/promote/', views.DraftPromoteView.as_view(), name='draft_promote'),
    path('drafts/<uuid:pk>/reject/', views.DraftRejectView.as_view(), name='draft_reject'),
]
```

## Acceptance Criteria

- [ ] Drafts can be promoted to definitive documents
- [ ] Authorship transfers to approving physician
- [ ] Bot references removed from final document
- [ ] Audit trail preserved via django-simple-history
- [ ] Drafts can be rejected and deleted
- [ ] Only authorized users can approve
- [ ] All tests pass

## Security Notes

- Only doctors/residents can approve clinical documents
- Consider restricting approval to the delegating physician only
- Audit trail must clearly show the promotion event
- Bot client_id is preserved in `draft_created_by_bot` for audit purposes
