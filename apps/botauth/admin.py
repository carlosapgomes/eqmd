from django.contrib import admin
from oidc_provider.models import Client
from .models import MatrixUserBinding, MatrixBindingAuditLog, BotClientProfile, BotClientAuditLog
from .bot_service import BotClientService, ALLOWED_BOT_SCOPES
from .audit import BotAuditLog


@admin.register(MatrixUserBinding)
class MatrixUserBindingAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'matrix_id', 'verified', 'delegation_enabled',
        'created_at', 'verified_at'
    ]
    list_filter = ['verified', 'delegation_enabled']
    search_fields = ['user__email', 'user__username', 'matrix_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'verified_at']
    
    fieldsets = [
        ('Binding', {
            'fields': ['id', 'user', 'matrix_id']
        }),
        ('Verification', {
            'fields': ['verified', 'verified_at', 'verification_token', 
                      'verification_token_expires']
        }),
        ('Delegation Control', {
            'fields': ['delegation_enabled']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ['user', 'matrix_id']
        return self.readonly_fields


@admin.register(MatrixBindingAuditLog)
class MatrixBindingAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'matrix_id', 'user_email', 'created_at', 'ip_address'
    ]
    list_filter = ['event_type', 'created_at']
    search_fields = ['matrix_id', 'user_email']
    readonly_fields = [
        'id', 'binding', 'matrix_id', 'user_email', 'event_type',
        'event_details', 'ip_address', 'user_agent', 'created_at'
    ]
    
    def has_add_permission(self, request):
        return False  # Audit logs are created programmatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Audit logs are immutable
    
    def has_delete_permission(self, request, obj=None):
        return False  # Audit logs should never be deleted


class BotClientProfileInline(admin.StackedInline):
    """Inline for BotClientProfile on Client admin."""
    model = BotClientProfile
    can_delete = False
    verbose_name_plural = 'Bot Profile'
    
    readonly_fields = ['created_at', 'updated_at', 'last_delegation_at', 
                       'total_delegations', 'suspended_at']


@admin.register(BotClientProfile)
class BotClientProfileAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'client_id_short', 'is_active', 
        'scope_count', 'total_delegations', 'last_delegation_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['display_name', 'client__client_id', 'description']
    readonly_fields = [
        'client', 'created_at', 'updated_at', 'created_by',
        'last_delegation_at', 'total_delegations', 'suspended_at'
    ]
    
    fieldsets = [
        ('Bot Identity', {
            'fields': ['client', 'display_name', 'description']
        }),
        ('Scopes', {
            'fields': ['allowed_scopes'],
            'description': f'Allowed scopes: {", ".join(ALLOWED_BOT_SCOPES)}'
        }),
        ('Rate Limiting', {
            'fields': ['max_delegations_per_hour', 'max_api_calls_per_minute']
        }),
        ('Status', {
            'fields': ['is_active', 'suspended_at', 'suspension_reason']
        }),
        ('Activity', {
            'fields': ['last_delegation_at', 'total_delegations'],
            'classes': ['collapse']
        }),
        ('Audit', {
            'fields': ['created_at', 'updated_at', 'created_by'],
            'classes': ['collapse']
        }),
    ]
    
    actions = ['suspend_bots', 'reactivate_bots']
    
    def client_id_short(self, obj):
        return obj.client.client_id[:12] + '...'
    client_id_short.short_description = 'Client ID'
    
    def scope_count(self, obj):
        return len(obj.allowed_scopes)
    scope_count.short_description = 'Scopes'
    
    def suspend_bots(self, request, queryset):
        for bot in queryset:
            BotClientService.suspend_bot(
                bot, 
                reason='Admin bulk suspension',
                performed_by=request.user
            )
        self.message_user(request, f'{queryset.count()} bot(s) suspended.')
    suspend_bots.short_description = 'Suspend selected bots'
    
    def reactivate_bots(self, request, queryset):
        for bot in queryset:
            BotClientService.reactivate_bot(bot, performed_by=request.user)
        self.message_user(request, f'{queryset.count()} bot(s) reactivated.')
    reactivate_bots.short_description = 'Reactivate selected bots'


@admin.register(BotClientAuditLog)
class BotClientAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'bot_name', 'performed_by', 'created_at'
    ]
    list_filter = ['event_type', 'created_at']
    search_fields = ['bot_name', 'client_id']
    readonly_fields = [
        'id', 'bot_profile', 'client_id', 'bot_name', 'event_type',
        'event_details', 'performed_by', 'created_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BotAuditLog)
class BotAuditLogAdmin(admin.ModelAdmin):
    """Admin interface for the centralized bot audit log."""
    list_display = [
        'timestamp', 'event_type', 'user_email', 'bot_name', 
        'success', 'ip_address'
    ]
    list_filter = ['event_type', 'success', 'timestamp']
    search_fields = ['user_email', 'bot_name', 'bot_client_id', 'ip_address']
    readonly_fields = [
        'id', 'event_type', 'event_id', 'timestamp',
        'user_id', 'user_email', 'bot_client_id', 'bot_name',
        'patient_id', 'event_object_id',
        'ip_address', 'user_agent', 'token_jti', 'scopes',
        'details', 'success', 'error_message'
    ]
    
    fieldsets = [
        ('Event Information', {
            'fields': ['id', 'event_type', 'event_id', 'timestamp']
        }),
        ('Actor Information', {
            'fields': ['user_id', 'user_email', 'bot_client_id', 'bot_name']
        }),
        ('Target Information', {
            'fields': ['patient_id', 'event_object_id']
        }),
        ('Request Context', {
            'fields': ['ip_address', 'user_agent', 'token_jti', 'scopes']
        }),
        ('Event Details', {
            'fields': ['details', 'success', 'error_message']
        }),
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
