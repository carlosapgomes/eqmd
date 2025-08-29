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
    list_display = ['username', 'email', 'first_name', 'last_name',
                    'is_active', 'profession_type', 'password_change_required', 'is_staff']
    history_list_display = ['username', 'email', 'profession_type', 'history_change_reason']

    # Custom fieldsets for editing existing users
    fieldsets = (
        (None, {'fields': ('username', 'email')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
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

    # Custom add_fieldsets for creating new users
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
    
    list_filter = UserAdmin.list_filter + (
        'password_change_required',
        'profession_type',
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
