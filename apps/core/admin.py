from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.contrib.postgres.search import SearchVector
from .models.renewal_request import AccountRenewalRequest
from .models.medical_procedure import MedicalProcedure

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


@admin.register(MedicalProcedure)
class MedicalProcedureAdmin(admin.ModelAdmin):
    """Admin interface for managing medical procedures."""
    
    list_display = (
        'code',
        'short_description_display', 
        'is_active',
        'created_at',
        'updated_at'
    )
    
    list_filter = (
        'is_active',
        'created_at',
        'updated_at'
    )
    
    search_fields = (
        'code',
        'description'
    )
    
    ordering = ('code',)
    
    readonly_fields = (
        'id',
        'created_at', 
        'updated_at',
        'search_vector'
    )
    
    fieldsets = (
        ('Procedure Information', {
            'fields': ('code', 'description', 'is_active')
        }),
        ('System Fields', {
            'fields': ('id', 'search_vector', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 50
    
    actions = ['activate_procedures', 'deactivate_procedures', 'update_search_vectors']
    
    def short_description_display(self, obj):
        """Display truncated description with tooltip."""
        if len(obj.description) <= 60:
            return obj.description
        
        truncated = obj.description[:57] + "..."
        return format_html(
            '<span title="{}">{}</span>',
            obj.description,
            truncated
        )
    short_description_display.short_description = 'Description'
    
    def activate_procedures(self, request, queryset):
        """Bulk action to activate selected procedures."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} procedure(s) activated successfully.")
    activate_procedures.short_description = "Activate selected procedures"
    
    def deactivate_procedures(self, request, queryset):
        """Bulk action to deactivate selected procedures."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} procedure(s) deactivated successfully.")
    deactivate_procedures.short_description = "Deactivate selected procedures"
    
    def update_search_vectors(self, request, queryset):
        """Bulk action to update search vectors for selected procedures."""
        try:
            # Update search vectors for selected procedures
            for procedure in queryset:
                MedicalProcedure.objects.filter(id=procedure.id).update(
                    search_vector=SearchVector('code', 'description')
                )
            
            count = queryset.count()
            self.message_user(
                request, 
                f"Search vectors updated successfully for {count} procedure(s)."
            )
        except Exception as e:
            self.message_user(
                request,
                f"Error updating search vectors: {str(e)}",
                level='ERROR'
            )
    update_search_vectors.short_description = "Update search vectors"
    
    def get_search_results(self, request, queryset, search_term):
        """Enhanced search functionality using PostgreSQL full-text search."""
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        
        try:
            # Try to use full-text search
            search_queryset = queryset.search(search_term)
            use_distinct = False
            
            return search_queryset, use_distinct
        except Exception:
            # Fallback to default search
            return super().get_search_results(request, queryset, search_term)
    
    def save_model(self, request, obj, form, change):
        """Override save to update search vector after saving."""
        super().save_model(request, obj, form, change)
        
        # Update search vector for this specific procedure
        try:
            MedicalProcedure.objects.filter(id=obj.id).update(
                search_vector=SearchVector('code', 'description')
            )
        except Exception:
            # Silently fail if PostgreSQL extensions not available
            pass
