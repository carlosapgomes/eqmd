from django.contrib import admin
from .models import SampleContent


@admin.register(SampleContent)
class SampleContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_event_type_display_formatted', 'created_by', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')
    
    fieldsets = (
        (None, {
            'fields': ('title', 'event_type', 'content')
        }),
        ('Auditoria', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        """Only superusers can add sample content."""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Only superusers can change sample content."""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete sample content."""
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        """All authenticated users can view sample content."""
        return request.user.is_authenticated