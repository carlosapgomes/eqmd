from django.contrib import admin
from .models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem


@admin.register(DrugTemplate)
class DrugTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'presentation', 'creator', 'is_public', 'created_at')
    list_filter = ('is_public', 'creator', 'created_at')
    search_fields = ('name', 'presentation')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'presentation', 'usage_instructions', 'is_public')
        }),
        ('Auditoria', {
            'fields': ('creator', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_public', 'make_private']

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.creator = request.user
        super().save_model(request, obj, form, change)

    def make_public(self, request, queryset):
        """Bulk action to make selected drug templates public."""
        updated = queryset.update(is_public=True)
        self.message_user(request, f'{updated} template(s) marcado(s) como público(s).')
    make_public.short_description = "Marcar selecionados como públicos"

    def make_private(self, request, queryset):
        """Bulk action to make selected drug templates private."""
        updated = queryset.update(is_public=False)
        self.message_user(request, f'{updated} template(s) marcado(s) como privado(s).')
    make_private.short_description = "Marcar selecionados como privados"


class PrescriptionTemplateItemInline(admin.TabularInline):
    """Inline admin for prescription template items."""
    model = PrescriptionTemplateItem
    extra = 1
    fields = ('order', 'drug_name', 'presentation', 'usage_instructions', 'quantity')
    ordering = ('order', 'drug_name')


@admin.register(PrescriptionTemplate)
class PrescriptionTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'is_public', 'item_count', 'created_at')
    list_filter = ('is_public', 'creator', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PrescriptionTemplateItemInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'is_public')
        }),
        ('Auditoria', {
            'fields': ('creator', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_public', 'make_private']

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.creator = request.user
        super().save_model(request, obj, form, change)

    def item_count(self, obj):
        """Display the number of items in the prescription template."""
        return obj.items.count()
    item_count.short_description = "Número de Itens"

    def make_public(self, request, queryset):
        """Bulk action to make selected prescription templates public."""
        updated = queryset.update(is_public=True)
        self.message_user(request, f'{updated} template(s) de prescrição marcado(s) como público(s).')
    make_public.short_description = "Marcar selecionados como públicos"

    def make_private(self, request, queryset):
        """Bulk action to make selected prescription templates private."""
        updated = queryset.update(is_public=False)
        self.message_user(request, f'{updated} template(s) de prescrição marcado(s) como privado(s).')
    make_private.short_description = "Marcar selecionados como privados"


@admin.register(PrescriptionTemplateItem)
class PrescriptionTemplateItemAdmin(admin.ModelAdmin):
    list_display = ('drug_name', 'presentation', 'template', 'order', 'created_at')
    list_filter = ('template', 'created_at')
    search_fields = ('drug_name', 'presentation', 'template__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('template', 'order', 'drug_name', 'presentation', 'usage_instructions', 'quantity')
        }),
        ('Auditoria', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
