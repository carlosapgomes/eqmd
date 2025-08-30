"""
Simple notification service for user lifecycle management
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

logger = logging.getLogger('lifecycle.notifications')


def send_simple_renewal_notification(renewal_request):
    """Send basic renewal request notification to admin"""
    subject = f'EquipeMed: Nova solicitação de renovação - {renewal_request.user.username}'
    
    context = {
        'renewal_request': renewal_request,
        'user': renewal_request.user,
        'admin_url': f"{settings.SITE_URL}/admin/core/accountrenewalrequest/{renewal_request.id}/change/",
    }
    
    message = render_to_string('emails/renewal_request_admin.txt', context)
    
    # Send to all admin users
    admin_emails = list(
        get_user_model().objects.filter(
            is_staff=True, is_active=True
        ).values_list('email', flat=True)
    )
    
    if admin_emails:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=True
        )


def send_expiration_warning_email(user, warning_days):
    """
    Send simplified expiration warning email to user
    """
    try:
        # Prepare context
        context = {
            'user': user,
            'warning_days': warning_days,
            'expiration_date': user.access_expires_at,
            'hospital_name': getattr(settings, 'HOSPITAL_NAME', 'EquipeMed'),
        }
        
        # Prepare email content
        subject = f'Aviso: Seu acesso expira em {warning_days} dia(s)'
        if warning_days == 1:
            subject = 'Aviso: Seu acesso expira amanhã'
        elif warning_days == 0:
            subject = 'URGENTE: Seu acesso expira hoje'
        
        # Simple text message (could be enhanced with HTML template later)
        message = f"""
Olá {user.get_full_name()},

Este é um aviso automático sobre a expiração do seu acesso ao sistema {context['hospital_name']}.

Detalhes:
- Usuário: {user.username}
- Profissão: {user.get_profession_type_display()}
- Data de expiração: {user.access_expires_at.strftime('%d/%m/%Y')}
- Dias restantes: {warning_days}

{'AÇÃO URGENTE NECESSÁRIA!' if warning_days <= 1 else 'Providencie a renovação do seu acesso com antecedência.'}

Para renovar seu acesso, entre em contato com seu supervisor ou com a administração do sistema.

---
Esta é uma mensagem automática. Não responda a este e-mail.
{context['hospital_name']}
        """
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@equipemd.com'),
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f'Expiration warning email sent to {user.username} ({warning_days} days)')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send expiration warning email to {user.username}: {e}')
        return False


def send_access_extended_notification(user, extended_by_days, reason, admin_user=None):
    """
    Send notification when user access is extended
    """
    try:
        context = {
            'user': user,
            'extended_by_days': extended_by_days,
            'reason': reason,
            'admin_user': admin_user,
            'new_expiration_date': user.access_expires_at,
            'hospital_name': getattr(settings, 'HOSPITAL_NAME', 'EquipeMed'),
        }
        
        subject = f'Acesso estendido - {extended_by_days} dia(s)'
        
        message = f"""
Olá {user.get_full_name()},

Seu acesso ao sistema {context['hospital_name']} foi estendido.

Detalhes da extensão:
- Usuário: {user.username}
- Dias estendidos: {extended_by_days}
- Nova data de expiração: {user.access_expires_at.strftime('%d/%m/%Y')}
- Motivo: {reason}
{f"- Estendido por: {admin_user.get_full_name()}" if admin_user else ""}

Seu acesso continuará funcionando normalmente até a nova data de expiração.

---
Esta é uma mensagem automática. Não responda a este e-mail.
{context['hospital_name']}
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@equipemd.com'),
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f'Access extension notification sent to {user.username} (+{extended_by_days} days)')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send access extension notification to {user.username}: {e}')
        return False