from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from .models import EqmdCustomUser, UserProfile
from .forms import EqmdCustomUserCreationForm, EqmdCustomUserChangeForm

class EqmdCustomUserAdmin(UserAdmin, SimpleHistoryAdmin):
    add_form = EqmdCustomUserCreationForm
    form = EqmdCustomUserChangeForm
    model = EqmdCustomUser
    
    # Add account_status and access_expires_at to the main list view
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'account_status', 'access_expires_at', 'is_active', 'is_staff'
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
        (_('Segurança'), {
            'fields': ('password_change_required', 'terms_accepted', 'terms_accepted_at'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Keep add_fieldsets simple for new user creation
    add_fieldsets = UserAdmin.add_fieldsets + (
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
    )
    
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

admin.site.register(EqmdCustomUser, EqmdCustomUserAdmin)
admin.site.register(UserProfile)
