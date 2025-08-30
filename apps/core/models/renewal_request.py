from django.db import models
from django.utils import timezone
from datetime import timedelta

class AccountRenewalRequest(models.Model):
    """Track user account renewal requests (simplified)"""
    
    user = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.CASCADE,
        related_name='renewal_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # User-provided information
    current_position = models.CharField(max_length=200)
    supervisor_name = models.CharField(max_length=200)
    supervisor_email = models.EmailField()
    renewal_reason = models.TextField()
    expected_duration_months = models.PositiveIntegerField()
    
    # Simple request status
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Administrative response (simplified)
    reviewed_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_renewal_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Renewal request for {self.user.username} - {self.status}"
    
    def approve(self, reviewed_by_user, duration_months, admin_notes=''):
        """Approve renewal request and extend user access"""
        self.status = 'approved'
        self.reviewed_by = reviewed_by_user
        self.reviewed_at = timezone.now()
        self.admin_notes = admin_notes
        
        # Calculate new expiration date
        current_expiration = self.user.access_expires_at or timezone.now()
        extension = timedelta(days=duration_months * 30)  # Approximate months
        new_expiration = current_expiration + extension
        
        # Update user account
        self.user.access_expires_at = new_expiration
        self.user.account_status = 'active'
        self.user._change_reason = f'Access renewed via request #{self.id}'
        
        # Save changes
        self.save()
        self.user.save()
    
    def deny(self, reviewed_by_user, admin_notes):
        """Deny renewal request"""
        self.status = 'denied'
        self.reviewed_by = reviewed_by_user
        self.reviewed_at = timezone.now()
        self.admin_notes = admin_notes
        self.save()