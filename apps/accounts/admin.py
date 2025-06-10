from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import EqmdCustomUser, UserProfile
from .forms import EqmdCustomUserCreationForm, EqmdCustomUserChangeForm

class EqmdCustomUserAdmin(UserAdmin):
    add_form = EqmdCustomUserCreationForm
    form = EqmdCustomUserChangeForm
    model = EqmdCustomUser
    list_display = ['username', 'email', 'first_name', 'last_name',
                    'is_active', 'profession_type', 'is_staff', 'last_hospital']

    # Custom fieldsets for editing existing users
    fieldsets = (
        (None, {'fields': ('username', 'email')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Professional Information', {
            'fields': ('profession_type', 'professional_registration_number',
                      'country_id_number', 'fiscal_number', 'phone')
        }),
        ('Hospital Information', {
            'fields': ('hospitals', 'last_hospital')
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
        ('Professional Information', {
            'fields': ('profession_type', 'professional_registration_number',
                      'country_id_number', 'fiscal_number', 'phone')
        }),
        ('Hospital Information', {
            'fields': ('hospitals',)
        }),
    )

admin.site.register(EqmdCustomUser, EqmdCustomUserAdmin)
admin.site.register(UserProfile)
