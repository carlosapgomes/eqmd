from django.contrib import admin
from django.utils import timezone
from .models.renewal_request import AccountRenewalRequest

@admin.register(AccountRenewalRequest)
class AccountRenewalRequestAdmin(admin.ModelAdmin):
    """Admin interface for managing account renewal requests."""
    
    list_display = (
        'user',
        'status',
        'created_at',
        'supervisor_name',
        'expected_duration_months',
        'reviewed_by',
        'reviewed_at',
    )
    
    list_filter = ('status',)
    search_fields = ('user__username', 'supervisor_name', 'supervisor_email')
    ordering = ('-created_at',)
    
    # Make most fields read-only in the detail view
    readonly_fields = (
        'user',
        'created_at',
        'current_position',
        'supervisor_name',
        'supervisor_email',
        'renewal_reason',
        'expected_duration_months',
        'reviewed_by',
        'reviewed_at',
    )
    
    fieldsets = (
        ('Request Details', {
            'fields': ('user', 'status', 'created_at')
        }),
        ('User Provided Information', {
            'fields': ('current_position', 'supervisor_name', 'supervisor_email', 'renewal_reason', 'expected_duration_months')
        }),
        ('Administrative Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'admin_notes')
        }),
    )
    
    actions = ['approve_requests', 'deny_requests']
    
    def approve_requests(self, request, queryset):
        """Bulk action to approve selected renewal requests."""
        for r in queryset.filter(status='pending'):
            r.approve(
                reviewed_by_user=request.user,
                duration_months=r.expected_duration_months,
                admin_notes=f"Bulk approved by {request.user.username} on {timezone.now().strftime('%Y-%m-%d')}."
            )
        self.message_user(request, f"{queryset.filter(status='approved').count()} request(s) approved.")
    approve_requests.short_description = "Approve selected renewal requests"
    
    def deny_requests(self, request, queryset):
        """Bulk action to deny selected renewal requests."""
        for r in queryset.filter(status='pending'):
            r.deny(
                reviewed_by_user=request.user,
                admin_notes=f"Bulk denied by {request.user.username} on {timezone.now().strftime('%Y-%m-%d')}."
            )
        self.message_user(request, f"{queryset.filter(status='denied').count()} request(s) denied.")
    deny_requests.short_description = "Deny selected renewal requests"
