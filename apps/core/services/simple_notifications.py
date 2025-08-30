"""
Simple notification service for user lifecycle management
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model


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


def send_expiration_warning_email(user, days_left):
    """Send basic expiration warning email"""
    subject = f'EquipeMD: Seu acesso expira em {days_left} dias'
    
    context = {
        'user': user,
        'days_left': days_left,
        'expiration_date': user.access_expires_at,
        'renewal_url': f"{settings.SITE_URL}/account/renewal-required/",
        'contact_email': getattr(settings, 'ADMIN_EMAIL', 'admin@equipemd.com'),
    }
    
    message = render_to_string('emails/expiration_warning_simple.txt', context)
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True
    )