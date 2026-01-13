"""
Service for promoting drafts to definitive documents.
"""

import logging
from django.db import transaction
from django.utils import timezone

from .audit import AuditLogger, AuditEventType

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
        
        # Audit logging
        AuditLogger.log(
            event_type=AuditEventType.DRAFT_PROMOTED,
            user=approving_user,
            patient=draft.patient if hasattr(draft, 'patient') else None,
            event_object=draft,
            details={
                'original_author': original_created_by.email,
                'bot': draft.draft_created_by_bot,
                'event_type': draft.get_event_type_display(),
                'modifications': modifications or {}
            }
        )
        
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
        
        # Audit logging before deletion
        AuditLogger.log(
            event_type=AuditEventType.DRAFT_REJECTED,
            user=rejecting_user,
            patient=draft.patient if hasattr(draft, 'patient') else None,
            event_object=draft,
            details={
                'reason': reason,
                'event_type': draft.get_event_type_display(),
                'bot': draft.draft_created_by_bot
            }
        )
        
        # Hard delete the draft
        draft.delete()