from django.contrib import admin
from .models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem


@admin.register(DrugTemplate)
class DrugTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'concentration_display', 'pharmaceutical_form_display', 'import_status_display', 'creator', 'is_public', 'created_at')
    list_filter = ('is_public', 'is_imported', 'pharmaceutical_form', 'import_source', 'creator', 'created_at')
    search_fields = ('name', 'concentration', 'pharmaceutical_form', 'import_source')
    readonly_fields = ('created_at', 'updated_at', 'presentation')
    
    fieldsets = (
        ('Informações do Medicamento', {
            'fields': ('name', 'concentration', 'pharmaceutical_form', 'usage_instructions', 'is_public')
        }),
        ('Informações de Importação', {
            'fields': ('is_imported', 'import_source'),
            'classes': ('collapse',)
        }),
        ('Compatibilidade', {
            'fields': ('presentation',),
            'description': 'Campo de apresentação gerado automaticamente para compatibilidade',
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('creator', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def concentration_display(self, obj):
        """Display method for concentration."""
        return obj.concentration or '-'
    concentration_display.short_description = 'Concentração'
    
    def pharmaceutical_form_display(self, obj):
        """Display method for pharmaceutical form.""" 
        return obj.pharmaceutical_form or '-'
    pharmaceutical_form_display.short_description = 'Forma Farmacêutica'
    
    def import_status_display(self, obj):
        """Display method for import status and source."""
        if obj.is_imported:
            source = obj.import_source or 'Fonte desconhecida'
            return f'Importado ({source})'
        return 'Criado por usuário'
    import_status_display.short_description = 'Origem'
    
    actions = ['make_public', 'make_private', 'mark_as_imported', 'mark_as_user_created']

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.creator = request.user
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        """Make core fields readonly for imported drugs."""
        readonly = list(self.readonly_fields)
        if obj and obj.is_imported:
            readonly.extend(['name', 'concentration', 'pharmaceutical_form', 'is_imported', 'import_source'])
        return readonly

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

    def mark_as_imported(self, request, queryset):
        """Bulk action to mark selected drug templates as imported."""
        imported_count = 0
        for obj in queryset:
            if not obj.is_imported:
                obj.is_imported = True
                obj.import_source = 'Admin - Conversão Manual'
                obj.save()
                imported_count += 1
        self.message_user(request, f'{imported_count} template(s) marcado(s) como importado(s).')
    mark_as_imported.short_description = "Marcar como importado"

    def mark_as_user_created(self, request, queryset):
        """Bulk action to mark selected drug templates as user-created."""
        user_created_count = 0
        for obj in queryset:
            if obj.is_imported:
                obj.is_imported = False
                obj.import_source = None
                obj.save()
                user_created_count += 1
        self.message_user(request, f'{user_created_count} template(s) marcado(s) como criado por usuário.')
    mark_as_user_created.short_description = "Marcar como criado por usuário"


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
