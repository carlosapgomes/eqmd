from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import path
from simple_history.admin import SimpleHistoryAdmin

from .forms import AllowedTagAdminForm
from .models import (
    AllowedTag,
    Patient,
    PatientAdmission,
    PatientRecordNumber,
    Tag,
    Ward,
)
from .services import tag_catalogue, tag_policy

ARCHIVE_ACTION = "Arquivar tags selecionadas"
RESTORE_ACTION = "Restaurar tags selecionadas"
DEACTIVATE_ACTION = "Desativar tags selecionadas"
REACTIVATE_ACTION = "Reativar tags selecionadas"


@admin.register(AllowedTag)
class AllowedTagAdmin(SimpleHistoryAdmin):
    form = AllowedTagAdminForm
    list_display = (
        'name', 'origin', 'visibility', 'specialty', 'responsible_user',
        'lifecycle_state', 'is_active', 'is_deleted', 'deleted_at',
        'created_at'
    )
    list_filter = (
        'origin', 'visibility', 'specialty', 'is_deleted', 'is_active',
    )
    search_fields = ('name', 'description', 'specialty__name', 'specialty__abbreviation')
    readonly_fields = (
        'lifecycle_state',
        'is_active', 'is_deleted', 'deleted_at', 'deleted_by', 'deletion_reason',
        'deactivated_at', 'deactivated_by', 'reactivated_at', 'reactivated_by',
        'archived_at', 'archived_by',
        'restored_at', 'restored_by',
        'created_at', 'created_by', 'updated_at', 'updated_by',
    )
    history_list_display = (
        'name', 'origin', 'visibility', 'specialty', 'is_active',
        'history_change_reason',
    )
    actions = (
        'archive_selected',
        'restore_selected',
        'deactivate_selected',
        'reactivate_selected',
    )

    fieldsets = (
        ('Tag Information', {
            'fields': ('name', 'description', 'color')
        }),
        ('Classificação e Namespace', {
            'fields': ('origin', 'visibility', 'specialty', 'responsible_user'),
            'description': (
                'Tags restritas exigem exatamente uma especialidade. Nomes '
                'normalizados ficam reservados no namespace em todos os '
                'estados, inclusive arquivadas. A responsabilidade só muda '
                'por transferência para um líder atual da mesma equipe.'
            ),
        }),
        ('Ciclo de vida', {
            'fields': (
                'lifecycle_state', 'is_active', 'is_deleted',
                'deactivated_at', 'deactivated_by',
                'reactivated_at', 'reactivated_by',
                'archived_at', 'archived_by',
                'deleted_at', 'deleted_by', 'deletion_reason',
                'restored_at', 'restored_by',
            ),
            'description': (
                'Use as ações de desativar, reativar, arquivar e restaurar. '
                'Restaurar mantém a tag inativa na mesma identidade.'
            ),
            'classes': ('collapse',),
        }),
        ('Audit Information', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        # Show all tags including deleted ones in admin
        return AllowedTag.all_objects.all()

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is None:
            readonly.append("responsible_user")
        return readonly

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        field = form.base_fields.get("responsible_user")
        if field is not None:
            field.queryset = tag_policy.eligible_transfer_recipient_queryset(
                include_user_id=(
                    obj.responsible_user_id if obj is not None else None
                )
            ).order_by("username")
        return form

    @admin.display(description="Estado")
    def lifecycle_state(self, obj: AllowedTag) -> str:
        return str(AllowedTag.LifecycleState(obj.lifecycle_state).label)

    def has_add_permission(self, request) -> bool:
        return super().has_add_permission(
            request
        ) and tag_policy.is_catalogue_administrator(request.user)

    def has_change_permission(self, request, obj=None) -> bool:
        return super().has_change_permission(
            request, obj
        ) and tag_policy.is_catalogue_administrator(request.user)

    def has_delete_permission(self, request, obj=None) -> bool:
        # Archiving is a bulk action; never expose a per-object hard-delete.
        if obj is not None:
            return False
        return (
            tag_policy.is_catalogue_administrator(request.user)
            and request.user.has_perm(tag_policy.CATALOGUE_DELETE_PERMISSION)
        )

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/restore/',
                self.admin_site.admin_view(self.restore_allowedtag),
                name='patients_allowedtag_restore',
            ),
        ]
        return custom_urls + urls

    def restore_allowedtag(self, request, object_id):
        """Restore a soft-deleted allowed tag into the inactive state."""
        allowedtag = AllowedTag.all_objects.get(id=object_id)
        try:
            tag_catalogue.restore_tag(actor=request.user, tag=allowedtag)
        except ValidationError as exc:
            messages.error(request, self._error_text(exc))
        else:
            messages.success(
                request,
                f'Allowed tag "{allowedtag.name}" has been restored (inactive).'
            )

        return HttpResponseRedirect(f'/admin/patients/allowedtag/{object_id}/change/')

    @admin.action(description=ARCHIVE_ACTION, permissions=["delete"])
    def archive_selected(self, request, queryset):
        self._run_lifecycle_action(
            request,
            queryset,
            lambda tag: tag_catalogue.archive_tag(actor=request.user, tag=tag),
            "arquivada(s)",
        )

    @admin.action(description=RESTORE_ACTION, permissions=["change"])
    def restore_selected(self, request, queryset):
        self._run_lifecycle_action(
            request,
            queryset,
            lambda tag: tag_catalogue.restore_tag(actor=request.user, tag=tag),
            "restaurada(s) como inativa(s)",
        )

    @admin.action(description=DEACTIVATE_ACTION, permissions=["change"])
    def deactivate_selected(self, request, queryset):
        self._run_lifecycle_action(
            request,
            queryset,
            lambda tag: tag_catalogue.deactivate_tag(
                actor=request.user, tag=tag
            ),
            "desativada(s)",
        )

    @admin.action(description=REACTIVATE_ACTION, permissions=["change"])
    def reactivate_selected(self, request, queryset):
        self._run_lifecycle_action(
            request,
            queryset,
            lambda tag: tag_catalogue.reactivate_tag(
                actor=request.user, tag=tag
            ),
            "reativada(s)",
        )

    def _run_lifecycle_action(self, request, queryset, operation, label) -> None:
        tags = list(queryset)
        try:
            with transaction.atomic():
                for tag in tags:
                    operation(tag)
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, self._error_text(exc))
            return
        messages.success(request, f'{len(tags)} allowed tag(s) were {label}.')

    def _error_text(self, exc: Exception) -> str:
        if isinstance(exc, ValidationError):
            return " ".join(str(message) for message in exc.messages)
        return str(exc)

    def save_model(self, request, obj, form, change):
        recipient = None
        if change:
            previous_responsible_id = (
                AllowedTag.all_objects.filter(pk=obj.pk)
                .values_list("responsible_user_id", flat=True)
                .first()
            )
            if obj.responsible_user_id != previous_responsible_id:
                recipient = obj.responsible_user
                obj.responsible_user_id = previous_responsible_id
            obj.updated_by = request.user
            obj._change_reason = f"Admin change by {request.user.username}"
        else:
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.responsible_user = None
        super().save_model(request, obj, form, change)
        if recipient is not None:
            tag_catalogue.transfer_responsibility(
                actor=request.user, tag=obj, recipient=recipient
            )

    def delete_model(self, request, obj):
        """Archive instead of hard-deleting a catalogue row."""
        tag_catalogue.archive_tag(actor=request.user, tag=obj)

    def delete_queryset(self, request, queryset):
        """Archive every selected row through the audited service."""
        self._run_lifecycle_action(
            request,
            queryset,
            lambda tag: tag_catalogue.archive_tag(actor=request.user, tag=tag),
            "arquivada(s)",
        )



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
    list_display = ('patient', 'record_number', 'is_current', 'effective_date', 'created_by')
    list_filter = ('is_current', 'effective_date', 'created_at')
    search_fields = ('patient__name', 'record_number', 'previous_record_number')
    readonly_fields = ('created_at', 'updated_at')

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

    def get_readonly_fields(self, request, obj=None):
        """Freeze the assigned number on persisted assignments (R6)."""
        readonly = list(self.readonly_fields)
        if obj is not None:
            readonly.append("record_number")
        return readonly

    def has_delete_permission(self, request, obj=None):
        """Persisted assignments are immutable history: no admin delete (R7)."""
        return False

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
    list_display = ('patient', 'admission_datetime', 'discharge_datetime', 'admission_type', 'ward', 'initial_bed', 'is_active', 'stay_duration_days')
    list_filter = ('admission_type', 'discharge_type', 'ward', 'is_active', 'admission_datetime')
    search_fields = ('patient__name', 'admission_diagnosis', 'discharge_diagnosis')
    readonly_fields = ('stay_duration_hours', 'stay_duration_days', 'created_at', 'updated_at')
    
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
    list_display = (
        "abbreviation",
        "name",
        "floor",
        "capacity_estimate",
        "is_active",
        "current_patients_count",
        "created_at",
    )
    list_filter = ("is_active", "floor", "created_at")
    search_fields = ("name", "abbreviation", "description")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

    fieldsets = (
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
    )
    
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
    list_display = (
        'name', 'birthday', 'gender', 'status', 'ward', 'bed', 
        'current_record_number', 'total_admissions_count', 'is_currently_admitted', 
        'is_deleted', 'deleted_at', 'deleted_by', 'created_at'
    )
    list_filter = ('is_deleted', 'status', 'gender', 'ward', 'deleted_at')
    search_fields = ('name', 'id_number', 'fiscal_number', 'healthcard_number', 'current_record_number')
    readonly_fields = (
        'current_record_number', 'total_admissions_count', 'total_inpatient_days', 
        'current_admission_id', 'deleted_at', 'deleted_by', 'deletion_reason',
        'created_at', 'created_by', 'updated_at', 'updated_by'
    )
    history_list_display = ('name', 'status', 'history_change_reason')
    
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
        ('Informações de Exclusão', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by', 'deletion_reason'),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        # Show all patients including deleted ones in admin
        return Patient.all_objects.all()

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/restore/',
                self.admin_site.admin_view(self.restore_patient),
                name='patients_patient_restore',
            ),
        ]
        return custom_urls + urls

    def restore_patient(self, request, object_id):
        """Restore a soft-deleted patient."""
        patient = Patient.all_objects.get(id=object_id)
        patient.restore(restored_by=request.user)

        messages.success(
            request,
            f'Patient "{patient.name}" has been successfully restored.'
        )

        return HttpResponseRedirect(f'/admin/patients/patient/{object_id}/change/')

    actions = ('soft_delete_selected', 'restore_selected')

    def soft_delete_selected(self, request, queryset):
        """Soft delete selected patients."""
        count = 0
        for patient in queryset:
            if not patient.is_deleted:
                patient.delete(
                    deleted_by=request.user,
                    reason=f'Bulk deletion by admin {request.user.username}'
                )
                count += 1

        messages.success(
            request,
            f'{count} patient(s) were soft deleted.'
        )
    soft_delete_selected.short_description = "Soft delete selected patients"

    def restore_selected(self, request, queryset):
        """Restore selected patients."""
        count = 0
        for patient in queryset:
            if patient.is_deleted:
                patient.restore(restored_by=request.user)
                count += 1

        messages.success(
            request,
            f'{count} patient(s) were restored.'
        )
    restore_selected.short_description = "Restore selected patients"

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.updated_by = request.user
        # Add change reason for admin modifications
        if change:
            obj._change_reason = f"Admin change by {request.user.username}"
        super().save_model(request, obj, form, change)

