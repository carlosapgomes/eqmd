from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Patient, PatientRecordNumber, PatientAdmission, AllowedTag, Tag, Ward

@admin.register(AllowedTag)
class AllowedTagAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'description', 'color', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')
    history_list_display = ['name', 'color', 'is_active', 'history_change_reason']

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.updated_by = request.user
        # Add change reason for admin modifications
        if change:
            obj._change_reason = f"Admin change by {request.user.username}"
        super().save_model(request, obj, form, change)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('allowed_tag', 'patient', 'notes', 'created_at')
    list_filter = ('allowed_tag', 'patient')
    search_fields = ('allowed_tag__name', 'patient__name', 'notes')
    readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.updated_by = request.user
        # Add change reason for admin modifications
        if change:
            obj._change_reason = f"Admin change by {request.user.username}"
        super().save_model(request, obj, form, change)


@admin.register(PatientRecordNumber)
class PatientRecordNumberAdmin(admin.ModelAdmin):
    list_display = ['patient', 'record_number', 'is_current', 'effective_date', 'created_by']
    list_filter = ['is_current', 'effective_date', 'created_at']
    search_fields = ['patient__name', 'record_number', 'previous_record_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informações do Prontuário', {
            'fields': ('patient', 'record_number', 'is_current')
        }),
        ('Histórico de Mudanças', {
            'fields': ('previous_record_number', 'change_reason', 'effective_date')
        }),
        ('Auditoria', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.updated_by = request.user
        # Add change reason for admin modifications
        if change:
            obj._change_reason = f"Admin change by {request.user.username}"
        super().save_model(request, obj, form, change)


@admin.register(PatientAdmission)
class PatientAdmissionAdmin(admin.ModelAdmin):
    list_display = ['patient', 'admission_datetime', 'discharge_datetime', 'admission_type', 'ward', 'initial_bed', 'is_active', 'stay_duration_days']
    list_filter = ['admission_type', 'discharge_type', 'ward', 'is_active', 'admission_datetime']
    search_fields = ['patient__name', 'admission_diagnosis', 'discharge_diagnosis']
    readonly_fields = ['stay_duration_hours', 'stay_duration_days', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informações da Internação', {
            'fields': ('patient', 'admission_datetime', 'admission_type')
        }),
        ('Localização', {
            'fields': ('ward', 'initial_bed')
        }),
        ('Informações da Alta', {
            'fields': ('discharge_datetime', 'discharge_type', 'final_bed', 'is_active')
        }),
        ('Diagnósticos', {
            'fields': ('admission_diagnosis', 'discharge_diagnosis')
        }),
        ('Duração', {
            'fields': ('stay_duration_hours', 'stay_duration_days'),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.updated_by = request.user
        # Add change reason for admin modifications
        if change:
            obj._change_reason = f"Admin change by {request.user.username}"
        super().save_model(request, obj, form, change)


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = [
        "abbreviation", 
        "name", 
        "floor", 
        "capacity_estimate", 
        "is_active",
        "current_patients_count",
        "created_at"
    ]
    list_filter = ["is_active", "floor", "created_at"]
    search_fields = ["name", "abbreviation", "description"]
    readonly_fields = ["created_at", "updated_at", "created_by", "updated_by"]
    
    fieldsets = [
        ("Informações Básicas", {
            "fields": ("name", "abbreviation", "description", "is_active")
        }),
        ("Localização", {
            "fields": ("floor", "capacity_estimate"),
            "classes": ("collapse",)
        }),
        ("Auditoria", {
            "fields": ("created_at", "created_by", "updated_at", "updated_by"),
            "classes": ("collapse",)
        }),
    ]
    
    def current_patients_count(self, obj):
        return obj.get_current_patients_count()
    current_patients_count.short_description = "Pacientes Atuais"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Patient)
class PatientAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'birthday', 'gender', 'status', 'ward', 'bed', 'current_record_number', 'total_admissions_count', 'is_currently_admitted', 'created_at')
    list_filter = ('status', 'gender', 'ward')
    search_fields = ('name', 'id_number', 'fiscal_number', 'healthcard_number', 'current_record_number')
    readonly_fields = ('current_record_number', 'total_admissions_count', 'total_inpatient_days', 'current_admission_id', 'created_at', 'created_by', 'updated_at', 'updated_by')
    history_list_display = ['name', 'status', 'history_change_reason']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'birthday', 'gender')
        }),
        ('Documentos', {
            'fields': ('healthcard_number', 'id_number', 'fiscal_number', 'phone')
        }),
        ('Endereço', {
            'fields': ('address', 'city', 'state', 'zip_code'),
            'classes': ('collapse',)
        }),
        ('Status Hospitalar', {
            'fields': ('status', 'ward', 'bed', 'last_admission_date', 'last_discharge_date')
        }),
        ('Informações do Prontuário', {
            'fields': ('current_record_number',),
            'classes': ('collapse',)
        }),
        ('Estatísticas de Internação', {
            'fields': ('total_admissions_count', 'total_inpatient_days', 'current_admission_id'),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.updated_by = request.user
        # Add change reason for admin modifications
        if change:
            obj._change_reason = f"Admin change by {request.user.username}"
        super().save_model(request, obj, form, change)

