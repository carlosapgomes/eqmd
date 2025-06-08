from django.contrib import admin
from .models import Patient, PatientHospitalRecord, AllowedTag, Tag

@admin.register(AllowedTag)
class AllowedTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'color', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('allowed_tag', 'notes', 'created_at')
    list_filter = ('allowed_tag',)
    search_fields = ('allowed_tag__name', 'notes')
    readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'birthday', 'status', 'current_hospital', 'created_at')
    list_filter = ('status', 'current_hospital', 'tags')
    search_fields = ('name', 'id_number', 'fiscal_number', 'healthcard_number')
    readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')
    filter_horizontal = ('tags',)

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(PatientHospitalRecord)
class PatientHospitalRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'hospital', 'record_number', 'created_at')
    list_filter = ('hospital',)
    search_fields = ('patient__name', 'record_number')
    readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)