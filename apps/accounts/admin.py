from django.contrib import admin, messages
from django.shortcuts import redirect
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from .models import EqmdCustomUser, UserProfile
from .forms import EqmdCustomUserCreationForm, EqmdCustomUserChangeForm
from apps.matrix_integration.services import (
    MatrixConfig,
    MatrixProvisioningError,
    MatrixProvisioningService,
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fk_name = "user"
    fields = (
        "public_id",
        "display_name",
        "bio",
        "matrix_localpart",
        "matrix_provisioned_at",
        "matrix_provisioned_by",
    )
    readonly_fields = ("public_id", "matrix_provisioned_at", "matrix_provisioned_by")

class EqmdCustomUserAdmin(UserAdmin, SimpleHistoryAdmin):
    add_form = EqmdCustomUserCreationForm
    form = EqmdCustomUserChangeForm
    model = EqmdCustomUser
    
    # Add account_status and access_expires_at to the main list view
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'account_status', 'access_expires_at', 'is_researcher', 'is_active', 'is_staff'
    ]
    history_list_display = ['username', 'email', 'profession_type', 'history_change_reason']

    # Add supervisor to search fields
    search_fields = UserAdmin.search_fields + ('supervisor__username',)

    # Define read-only fields for the detail view
    readonly_fields = UserAdmin.readonly_fields + ('last_meaningful_activity', 'expiration_warning_sent')

    # Reorganize fieldsets to include a new "Lifecycle Management" section
    fieldsets = (
        (None, {'fields': ('username', 'email')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Professional Information', {
            'fields': ('profession_type', 'professional_registration_number',
                      'country_id_number', 'fiscal_number', 'phone')
        }),
        # New Lifecycle Management Section
        (_('Lifecycle Management'), {
            'classes': ('collapse',), # Start collapsed to save space
            'fields': (
                'account_status',
                'supervisor',
                'access_expires_at',
                'expiration_reason',
                'internship_start_date',
                'expected_duration_months',
                'last_meaningful_activity',
                'expiration_warning_sent',
            ),
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Permissões de Pesquisa', {
            'fields': ('is_researcher',),
            'description': 'Controla acesso às funcionalidades de pesquisa clínica'
        }),
        (_('Segurança'), {
            'fields': ('password_change_required', 'terms_accepted', 'terms_accepted_at'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Keep add_fieldsets simple for new user creation
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
        ('Personal info', {
            'fields': ('first_name', 'last_name')
        }),
        (_('Segurança'), {
            'fields': (
                'password_change_required',
            ),
            'description': _('Configurações de segurança para usuários do hospital')
        }),
        ('Professional Information', {
            'fields': ('profession_type', 'professional_registration_number',
                      'country_id_number', 'fiscal_number', 'phone')
        }),
    )
    
    # Add new filters to the sidebar
    list_filter = UserAdmin.list_filter + (
        'account_status',
        'profession_type',
        'expiration_reason',
        'password_change_required',
        'terms_accepted',
        'is_researcher',
    )
    inlines = (UserProfileInline,)

    def get_inline_instances(self, request, obj=None):
        # Avoid double-creating UserProfile on add; signals already create it.
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)
    
    def save_model(self, request, obj, form, change):
        """
        Custom save logic for user creation by admins.
        
        When admin creates a new user, ensure password_change_required is True
        unless explicitly set otherwise.
        """
        if not change:  # New user creation
            # Set flag to require password change for new users
            if not hasattr(obj, 'password_change_required') or obj.password_change_required is None:
                obj.password_change_required = True
        
        super().save_model(request, obj, form, change)
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form with helpful information for admins."""
        form = super().get_form(request, obj, **kwargs)
        
        if 'password_change_required' in form.base_fields:
            form.base_fields['password_change_required'].help_text = _(
                'Marque para forçar o usuário a alterar a senha no primeiro login. '
                'Recomendado para usuários criados pelos administradores.'
            )
        
        return form

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "display_name",
        "matrix_localpart",
        "matrix_user_id",
        "matrix_provisioned",
        "matrix_provisioned_at",
        "matrix_provisioned_by",
    )
    list_select_related = ("user", "matrix_provisioned_by")
    readonly_fields = (
        "public_id",
        "matrix_user_id",
        "matrix_provisioned_at",
        "matrix_provisioned_by",
    )
    fields = (
        "user",
        "public_id",
        "display_name",
        "bio",
        "matrix_localpart",
        "matrix_user_id",
        "matrix_provisioned_at",
        "matrix_provisioned_by",
    )
    search_fields = ("user__email", "user__username", "matrix_localpart")
    actions = ("provision_matrix_users",)
    change_form_template = "admin/accounts/userprofile/change_form.html"

    @admin.display(description="Matrix ID")
    def matrix_user_id(self, obj):
        if not obj.matrix_localpart:
            return "-"
        config = MatrixConfig.from_env()
        return f"@{obj.matrix_localpart}:{config.matrix_fqdn}"

    @admin.display(boolean=True, description="Matrix provisioned")
    def matrix_provisioned(self, obj):
        return bool(obj.matrix_provisioned_at)

    @admin.action(description="Provision Matrix user(s)")
    def provision_matrix_users(self, request, queryset):
        config = MatrixConfig.from_env()
        success_count = 0
        for profile in queryset.select_related("user"):
            try:
                MatrixProvisioningService.provision_user(
                    profile.user,
                    config,
                    performed_by=request.user,
                )
                success_count += 1
            except MatrixProvisioningError as exc:
                self.message_user(
                    request,
                    f"{profile.user}: {exc}",
                    level=messages.ERROR,
                )
        if success_count:
            self.message_user(
                request,
                f"Provisioned {success_count} Matrix user(s).",
                level=messages.SUCCESS,
            )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id) if object_id else None
        extra_context["show_matrix_provision"] = bool(
            obj and obj.matrix_localpart
        )
        return super().changeform_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )

    def response_change(self, request, obj):
        if "_provision_matrix_user" in request.POST:
            self._provision_single(request, obj)
            return redirect(request.path)
        return super().response_change(request, obj)

    def _provision_single(self, request, profile):
        try:
            config = MatrixConfig.from_env()
            matrix_user_id = MatrixProvisioningService.provision_user(
                profile.user,
                config,
                performed_by=request.user,
            )
            self.message_user(
                request,
                f"Provisioned Matrix user {matrix_user_id}.",
                level=messages.SUCCESS,
            )
        except MatrixProvisioningError as exc:
            self.message_user(
                request,
                f"Matrix provisioning failed: {exc}",
                level=messages.ERROR,
            )


admin.site.register(EqmdCustomUser, EqmdCustomUserAdmin)
