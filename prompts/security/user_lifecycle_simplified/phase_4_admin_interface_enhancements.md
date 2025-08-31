# Phase 4: Enhanced Admin Interface

## Overview
**Timeline: 2-3 days**
**Priority: High**

This phase focuses on enhancing the standard Django Admin interface to provide administrators with the necessary tools to view and manage user lifecycle data. This is a high-value, low-complexity enhancement that directly addresses the visibility gap in the current system.

## Problem Statement

The previous implementation phases successfully added lifecycle-related fields to the `EqmdCustomUser` model and created the `AccountRenewalRequest` model. However, these fields and models are not visible or manageable in the Django admin panel. Administrators currently lack the ability to:

-   View a user's current `account_status` or `access_expires_at` date.
-   Manually edit a user's lifecycle information.
-   Filter or search for users based on their lifecycle status.
-   Review, approve, or deny account renewal requests.

This plan details the specific changes required to integrate these features directly into the existing admin interface.

## Implementation Details

### Step 1: Enhance `EqmdCustomUser` Admin

**Target File**: `apps/accounts/admin.py`

The `EqmdCustomUserAdmin` class will be updated to display, filter, and edit the new lifecycle fields.

```python
# apps/accounts/admin.py

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
        """
        if not change:
            if not hasattr(obj, 'password_change_required') or obj.password_change_required is None:
                obj.password_change_required = True
        
        super().save_model(request, obj, form, change)

admin.site.register(EqmdCustomUser, EqmdCustomUserAdmin)
admin.site.register(UserProfile)
```

### Step 2: Create Admin Interface for `AccountRenewalRequest`

**Target File**: `apps/core/admin.py`

A new admin interface will be created for the `AccountRenewalRequest` model to allow administrators to easily manage renewal requests.

```python
# apps/core/admin.py

from django.contrib import admin
from django.utils import timezone
from .models.renewal_request import AccountRenewalRequest

@admin.register(AccountRenewalRequest)
class AccountRenewalRequestAdmin(admin.ModelAdmin):
    """Admin interface for managing account renewal requests."""
    
    list_display = (
        'user',
        'status',
        'created_at',
        'supervisor_name',
        'expected_duration_months',
        'reviewed_by',
        'reviewed_at',
    )
    
    list_filter = ('status',)
    search_fields = ('user__username', 'supervisor_name', 'supervisor_email')
    ordering = ('-created_at',)
    
    # Make most fields read-only in the detail view
    readonly_fields = (
        'user',
        'created_at',
        'current_position',
        'supervisor_name',
        'supervisor_email',
        'renewal_reason',
        'expected_duration_months',
        'reviewed_by',
        'reviewed_at',
    )
    
    fieldsets = (
        ('Request Details', {
            'fields': ('user', 'status', 'created_at')
        }),
        ('User Provided Information', {
            'fields': ('current_position', 'supervisor_name', 'supervisor_email', 'renewal_reason', 'expected_duration_months')
        }),
        ('Administrative Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'admin_notes')
        }),
    )
    
    actions = ['approve_requests', 'deny_requests']
    
    def approve_requests(self, request, queryset):
        """Bulk action to approve selected renewal requests."""
        for r in queryset.filter(status='pending'):
            r.approve(
                reviewed_by_user=request.user,
                duration_months=r.expected_duration_months,
                admin_notes=f"Bulk approved by {request.user.username} on {timezone.now().strftime('%Y-%m-%d')}."
            )
        self.message_user(request, f"{queryset.filter(status='approved').count()} request(s) approved.")
    approve_requests.short_description = "Approve selected renewal requests"
    
    def deny_requests(self, request, queryset):
        """Bulk action to deny selected renewal requests."""
        for r in queryset.filter(status='pending'):
            r.deny(
                reviewed_by_user=request.user,
                admin_notes=f"Bulk denied by {request.user.username} on {timezone.now().strftime('%Y-%m-%d')}."
            )
        self.message_user(request, f"{queryset.filter(status='denied').count()} request(s) denied.")
    deny_requests.short_description = "Deny selected renewal requests"

```

## Testing Requirements

After implementation, the following should be manually tested in the Django admin panel:

1.  **User List View**:
    *   Confirm the new columns (`Account Status`, `Access Expires At`) are visible.
    *   Test sorting by clicking on the new column headers.
    *   Test the new sidebar filters for `Account Status` and `Expiration Reason`.
    *   Use the search bar to find a user by their supervisor's name.
2.  **User Detail View**:
    *   Open a user and find the "Lifecycle Management" section.
    *   Verify that the correct fields are editable and read-only.
    *   Modify a user's `account_status` and `access_expires_at` date and save to confirm it works.
3.  **Renewal Request View**:
    *   Confirm that "Account Renewal Requests" appears in the admin index.
    *   Create a test renewal request and verify it appears in the list.
    *   Use the bulk actions to approve and deny pending requests and confirm the status changes.

## Success Metrics

-   ✅ Administrators can view and sort by `account_status` and `access_expires_at` in the user list.
-   ✅ Administrators can edit all relevant lifecycle fields from the user detail page.
-   ✅ Administrators can filter the user list by `account_status`.
-   ✅ Administrators can view and manage `AccountRenewalRequest` objects, including bulk approval/denial.
