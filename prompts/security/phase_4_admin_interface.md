# Phase 4: Admin Interface and Dashboards

## Overview

**Timeline: 2-3 weeks**
**Priority: Medium**

Create comprehensive administrative interfaces for user lifecycle management, providing administrators with intuitive tools for monitoring, managing, and reporting on user accounts across their lifecycle stages.

## Interface Architecture

### Dashboard Structure

```
User Lifecycle Management Dashboard
├── Overview Dashboard
│   ├── Key Metrics Summary
│   ├── Status Distribution Charts  
│   ├── Expiration Timeline
│   └── Recent Activity Feed
├── User Management Interface
│   ├── User Search and Filtering
│   ├── Bulk Operations Panel
│   ├── Individual User Management
│   └── Status Transition Tools
├── Renewal Management
│   ├── Pending Renewal Requests
│   ├── Approval Workflow
│   ├── Supervisor Notifications
│   └── Renewal History
├── Reporting and Analytics
│   ├── Lifecycle Reports
│   ├── Activity Analytics
│   ├── Compliance Dashboards
│   └── Export Tools
└── Configuration and Settings
    ├── Role-Based Expiration Rules
    ├── Notification Templates
    ├── Automated Task Settings
    └── System Health Monitoring
```

## Django Admin Integration

### Enhanced User Admin

```python
# apps/accounts/admin.py - Enhanced admin interface

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import timedelta
from .models import EqmdCustomUser, AccountRenewalRequest
from .forms import UserLifecycleForm, BulkExtensionForm

@admin.register(EqmdCustomUser)
class EqmdCustomUserAdmin(UserAdmin):
    """Enhanced user admin with lifecycle management"""
    
    # Add lifecycle fields to list display
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'get_profession_display', 'account_status_badge', 
        'expiration_info', 'activity_indicator', 'is_active'
    )
    
    list_filter = (
        'account_status', 'profession_type', 'is_active', 'is_staff',
        'access_expires_at', 'last_meaningful_activity'
    )
    
    search_fields = ('username', 'first_name', 'last_name', 'email', 'department')
    
    # Add lifecycle fieldset to user form
    fieldsets = UserAdmin.fieldsets + (
        ('Lifecycle Management', {
            'fields': (
                'account_status', 'access_expires_at', 'expiration_reason',
                'last_meaningful_activity', 'activity_score',
                'supervisor', 'department'
            ),
            'classes': ('collapse',)
        }),
        ('Review and Renewal', {
            'fields': (
                'last_access_review', 'reviewed_by', 'next_review_due',
                'expiration_warning_sent', 'renewal_reminder_count'
            ),
            'classes': ('collapse',)
        }),
        ('Role-Specific Settings', {
            'fields': (
                'internship_start_date', 'expected_duration_months'
            ),
            'classes': ('collapse',)
        }),
    )
    
    # Custom admin actions
    actions = [
        'extend_access_30_days', 'extend_access_90_days', 'extend_access_1_year',
        'mark_as_inactive', 'mark_as_suspended', 'reset_expiration_warnings'
    ]
    
    # Add custom URLs for lifecycle management
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('lifecycle-dashboard/', 
                 self.admin_site.admin_view(self.lifecycle_dashboard_view),
                 name='accounts_eqmdcustomuser_lifecycle_dashboard'),
            path('<int:user_id>/extend-access/',
                 self.admin_site.admin_view(self.extend_access_view),
                 name='accounts_eqmdcustomuser_extend_access'),
            path('bulk-operations/',
                 self.admin_site.admin_view(self.bulk_operations_view),
                 name='accounts_eqmdcustomuser_bulk_operations'),
        ]
        return custom_urls + urls
    
    # Custom display methods
    def get_profession_display(self, obj):
        """Display profession with color coding"""
        profession = obj.get_profession_type_display()
        color_map = {
            'Médico': '#28a745',
            'Residente': '#ffc107', 
            'Enfermeiro': '#17a2b8',
            'Fisioterapeuta': '#6f42c1',
            'Estudante': '#fd7e14'
        }
        color = color_map.get(profession, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, profession
        )
    get_profession_display.short_description = 'Profession'
    
    def account_status_badge(self, obj):
        """Display account status as colored badge"""
        status_colors = {
            'active': ('#28a745', '#ffffff'),
            'expiring_soon': ('#ffc107', '#212529'),
            'expired': ('#dc3545', '#ffffff'),
            'inactive': ('#6c757d', '#ffffff'),
            'suspended': ('#dc3545', '#ffffff'),
            'departed': ('#343a40', '#ffffff'),
            'renewal_required': ('#fd7e14', '#ffffff'),
        }
        
        bg_color, text_color = status_colors.get(obj.account_status, ('#6c757d', '#ffffff'))
        display_text = obj.get_account_status_display()
        
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; '
            'border-radius: 4px; font-size: 12px; font-weight: bold;">{}</span>',
            bg_color, text_color, display_text
        )
    account_status_badge.short_description = 'Status'
    
    def expiration_info(self, obj):
        """Display expiration information with visual indicators"""
        if not obj.access_expires_at:
            return format_html('<em style="color: #6c757d;">Never expires</em>')
        
        days_left = obj.days_until_expiration
        if days_left is None:
            return '-'
        
        if days_left < 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">Expired {} days ago</span>',
                abs(days_left)
            )
        elif days_left <= 7:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{} days left</span>',
                days_left
            )
        elif days_left <= 30:
            return format_html(
                '<span style="color: #ffc107; font-weight: bold;">{} days left</span>',
                days_left
            )
        else:
            return format_html(
                '<span style="color: #28a745;">{} days left</span>',
                days_left
            )
    expiration_info.short_description = 'Expiration'
    
    def activity_indicator(self, obj):
        """Show activity indicator"""
        if not obj.last_meaningful_activity:
            return format_html('<span style="color: #dc3545;">●</span> No activity')
        
        days_since = obj.days_since_last_activity
        if days_since is None:
            return '-'
        
        if days_since <= 7:
            color = '#28a745'  # Green
            status = 'Active'
        elif days_since <= 30:
            color = '#ffc107'  # Yellow
            status = 'Recent'
        elif days_since <= 90:
            color = '#fd7e14'  # Orange
            status = 'Inactive'
        else:
            color = '#dc3545'  # Red
            status = 'Very Inactive'
        
        return format_html(
            '<span style="color: {};">●</span> {} ({} days)',
            color, status, days_since
        )
    activity_indicator.short_description = 'Activity'
    
    # Custom admin actions
    def extend_access_30_days(self, request, queryset):
        """Extend access by 30 days for selected users"""
        count = 0
        for user in queryset:
            if user.account_status != 'departed':
                user.extend_access(30, 'Bulk 30-day extension', request.user)
                count += 1
        
        self.message_user(request, f'Extended access for {count} users by 30 days.')
    extend_access_30_days.short_description = 'Extend access by 30 days'
    
    def extend_access_90_days(self, request, queryset):
        """Extend access by 90 days for selected users"""
        count = 0
        for user in queryset:
            if user.account_status != 'departed':
                user.extend_access(90, 'Bulk 90-day extension', request.user)
                count += 1
        
        self.message_user(request, f'Extended access for {count} users by 90 days.')
    extend_access_90_days.short_description = 'Extend access by 90 days'
    
    def mark_as_inactive(self, request, queryset):
        """Mark selected users as inactive"""
        count = queryset.update(account_status='inactive')
        self.message_user(request, f'Marked {count} users as inactive.')
    mark_as_inactive.short_description = 'Mark as inactive'
    
    # Custom views
    def lifecycle_dashboard_view(self, request):
        """Comprehensive lifecycle dashboard"""
        from django.db.models import Count, Q
        from django.utils import timezone
        from datetime import timedelta
        
        # Gather dashboard statistics
        now = timezone.now()
        
        # Status distribution
        status_counts = EqmdCustomUser.objects.filter(is_active=True).values(
            'account_status'
        ).annotate(count=Count('id'))
        
        # Expiration analysis
        expiration_ranges = {
            'expired': Q(access_expires_at__lt=now),
            'next_7_days': Q(access_expires_at__range=(now, now + timedelta(days=7))),
            'next_30_days': Q(access_expires_at__range=(now + timedelta(days=7), now + timedelta(days=30))),
            'next_90_days': Q(access_expires_at__range=(now + timedelta(days=30), now + timedelta(days=90))),
        }
        
        expiration_counts = {}
        for period, query in expiration_ranges.items():
            expiration_counts[period] = EqmdCustomUser.objects.filter(
                is_active=True
            ).filter(query).count()
        
        # Recent activity
        recent_activity = EqmdCustomUser.objects.filter(
            is_active=True,
            last_meaningful_activity__gte=now - timedelta(days=7)
        ).count()
        
        # Pending renewal requests
        pending_renewals = AccountRenewalRequest.objects.filter(
            status='pending'
        ).count()
        
        context = {
            'title': 'User Lifecycle Dashboard',
            'status_counts': {item['account_status']: item['count'] for item in status_counts},
            'expiration_counts': expiration_counts,
            'recent_activity_count': recent_activity,
            'pending_renewals': pending_renewals,
            'total_users': EqmdCustomUser.objects.filter(is_active=True).count(),
        }
        
        return render(request, 'admin/accounts/user_lifecycle_dashboard.html', context)
    
    def extend_access_view(self, request, user_id):
        """Individual user access extension"""
        user = EqmdCustomUser.objects.get(id=user_id)
        
        if request.method == 'POST':
            form = UserLifecycleForm(request.POST, instance=user)
            if form.is_valid():
                days = form.cleaned_data['extension_days']
                reason = form.cleaned_data['extension_reason']
                
                user.extend_access(days, reason, request.user)
                
                messages.success(
                    request, 
                    f'Extended access for {user.username} by {days} days'
                )
                return redirect('admin:accounts_eqmdcustomuser_change', user_id)
        else:
            form = UserLifecycleForm(instance=user)
        
        context = {
            'title': f'Extend Access - {user.username}',
            'user': user,
            'form': form,
        }
        
        return render(request, 'admin/accounts/extend_access.html', context)
    
    def bulk_operations_view(self, request):
        """Bulk operations interface"""
        if request.method == 'POST':
            form = BulkExtensionForm(request.POST)
            if form.is_valid():
                # Process bulk operation
                operation = form.cleaned_data['operation']
                user_ids = form.cleaned_data['selected_users']
                
                users = EqmdCustomUser.objects.filter(id__in=user_ids)
                
                if operation == 'extend_30':
                    for user in users:
                        user.extend_access(30, 'Bulk 30-day extension', request.user)
                    messages.success(request, f'Extended access for {users.count()} users')
                
                # Add more bulk operations as needed
                
        else:
            form = BulkExtensionForm()
        
        context = {
            'title': 'Bulk User Operations',
            'form': form,
        }
        
        return render(request, 'admin/accounts/bulk_operations.html', context)

@admin.register(AccountRenewalRequest)
class AccountRenewalRequestAdmin(admin.ModelAdmin):
    """Admin interface for renewal requests"""
    
    list_display = (
        'user', 'created_at', 'status_badge', 'current_position', 
        'supervisor_name', 'expected_duration_months', 'reviewed_by'
    )
    
    list_filter = ('status', 'created_at', 'expected_duration_months')
    search_fields = ('user__username', 'user__email', 'supervisor_name', 'current_position')
    
    readonly_fields = ('created_at', 'user')
    
    fieldsets = (
        ('Request Information', {
            'fields': ('user', 'created_at', 'status')
        }),
        ('User Details', {
            'fields': (
                'current_position', 'department', 'supervisor_name', 
                'supervisor_email', 'expected_duration_months'
            )
        }),
        ('Request Details', {
            'fields': ('renewal_reason',)
        }),
        ('Administrative Response', {
            'fields': (
                'reviewed_by', 'reviewed_at', 'admin_notes',
                'approved_duration_months', 'new_expiration_date'
            )
        }),
    )
    
    actions = ['approve_requests', 'deny_requests']
    
    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745', 
            'denied': '#dc3545',
            'more_info_required': '#fd7e14'
        }
        
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 12px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def approve_requests(self, request, queryset):
        """Bulk approve renewal requests"""
        for renewal_request in queryset.filter(status='pending'):
            # Use requested duration or default to 6 months
            duration = renewal_request.expected_duration_months or 6
            renewal_request.approve(request.user, duration, 'Bulk approval')
        
        count = queryset.count()
        self.message_user(request, f'Approved {count} renewal requests.')
    approve_requests.short_description = 'Approve selected requests'
```

## Dashboard Templates

### Main Lifecycle Dashboard

```html
<!-- templates/admin/accounts/user_lifecycle_dashboard.html -->

{% extends "admin/base_site.html" %}
{% load static %}

{% block title %}{{ title }} | Django Admin{% endblock %}

{% block extrahead %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.dashboard-card {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.dashboard-card h3 {
    margin-top: 0;
    color: #333;
    border-bottom: 2px solid #79aec8;
    padding-bottom: 10px;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 15px;
    margin: 15px 0;
}

.metric-item {
    text-align: center;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 6px;
}

.metric-number {
    font-size: 2em;
    font-weight: bold;
    color: #79aec8;
}

.metric-label {
    font-size: 0.9em;
    color: #666;
    margin-top: 5px;
}

.status-active { color: #28a745; }
.status-expiring { color: #ffc107; }
.status-expired { color: #dc3545; }
.status-inactive { color: #6c757d; }
</style>
{% endblock %}

{% block content %}
<h1>{{ title }}</h1>

<div class="dashboard-grid">
    <!-- Overview Card -->
    <div class="dashboard-card">
        <h3>System Overview</h3>
        <div class="metric-grid">
            <div class="metric-item">
                <div class="metric-number">{{ total_users }}</div>
                <div class="metric-label">Total Active Users</div>
            </div>
            <div class="metric-item">
                <div class="metric-number status-active">{{ status_counts.active|default:0 }}</div>
                <div class="metric-label">Active Users</div>
            </div>
            <div class="metric-item">
                <div class="metric-number status-expiring">{{ status_counts.expiring_soon|default:0 }}</div>
                <div class="metric-label">Expiring Soon</div>
            </div>
            <div class="metric-item">
                <div class="metric-number status-expired">{{ status_counts.expired|default:0 }}</div>
                <div class="metric-label">Expired</div>
            </div>
        </div>
    </div>

    <!-- Expiration Analysis Card -->
    <div class="dashboard-card">
        <h3>Expiration Analysis</h3>
        <div class="metric-grid">
            <div class="metric-item">
                <div class="metric-number status-expired">{{ expiration_counts.expired }}</div>
                <div class="metric-label">Already Expired</div>
            </div>
            <div class="metric-item">
                <div class="metric-number status-expiring">{{ expiration_counts.next_7_days }}</div>
                <div class="metric-label">Next 7 Days</div>
            </div>
            <div class="metric-item">
                <div class="metric-number status-expiring">{{ expiration_counts.next_30_days }}</div>
                <div class="metric-label">Next 30 Days</div>
            </div>
            <div class="metric-item">
                <div class="metric-number">{{ expiration_counts.next_90_days }}</div>
                <div class="metric-label">Next 90 Days</div>
            </div>
        </div>
    </div>

    <!-- Activity and Renewals Card -->
    <div class="dashboard-card">
        <h3>Activity & Renewals</h3>
        <div class="metric-grid">
            <div class="metric-item">
                <div class="metric-number status-active">{{ recent_activity_count }}</div>
                <div class="metric-label">Active This Week</div>
            </div>
            <div class="metric-item">
                <div class="metric-number status-expiring">{{ pending_renewals }}</div>
                <div class="metric-label">Pending Renewals</div>
            </div>
            <div class="metric-item">
                <div class="metric-number status-inactive">{{ status_counts.inactive|default:0 }}</div>
                <div class="metric-label">Inactive Users</div>
            </div>
            <div class="metric-item">
                <div class="metric-number status-expired">{{ status_counts.suspended|default:0 }}</div>
                <div class="metric-label">Suspended Users</div>
            </div>
        </div>
    </div>

    <!-- Status Distribution Chart -->
    <div class="dashboard-card">
        <h3>Status Distribution</h3>
        <canvas id="statusChart" width="400" height="200"></canvas>
    </div>
</div>

<!-- Quick Actions -->
<div class="dashboard-card">
    <h3>Quick Actions</h3>
    <div style="display: flex; gap: 15px; flex-wrap: wrap;">
        <a href="{% url 'admin:accounts_eqmdcustomuser_changelist' %}?account_status=expired" 
           class="button" style="background: #dc3545;">View Expired Users</a>
        <a href="{% url 'admin:accounts_eqmdcustomuser_changelist' %}?account_status=expiring_soon" 
           class="button" style="background: #ffc107;">View Expiring Soon</a>
        <a href="{% url 'admin:accounts_accountrenewalrequest_changelist' %}?status=pending" 
           class="button" style="background: #fd7e14;">Review Renewal Requests</a>
        <a href="{% url 'admin:accounts_eqmdcustomuser_bulk_operations' %}" 
           class="button" style="background: #28a745;">Bulk Operations</a>
    </div>
</div>

<script>
// Status distribution chart
const ctx = document.getElementById('statusChart').getContext('2d');
const statusChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
        labels: [
            'Active', 'Expiring Soon', 'Expired', 'Inactive', 'Suspended', 'Renewal Required'
        ],
        datasets: [{
            data: [
                {{ status_counts.active|default:0 }},
                {{ status_counts.expiring_soon|default:0 }},
                {{ status_counts.expired|default:0 }},
                {{ status_counts.inactive|default:0 }},
                {{ status_counts.suspended|default:0 }},
                {{ status_counts.renewal_required|default:0 }}
            ],
            backgroundColor: [
                '#28a745', '#ffc107', '#dc3545', '#6c757d', '#343a40', '#fd7e14'
            ]
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom'
            }
        }
    }
});
</script>
{% endblock %}
```

### User Extension Form

```python
# apps/accounts/forms.py - Admin forms

from django import forms
from django.core.exceptions import ValidationError
from .models import EqmdCustomUser

class UserLifecycleForm(forms.ModelForm):
    """Form for managing individual user lifecycle"""
    
    extension_days = forms.IntegerField(
        min_value=1,
        max_value=730,  # Max 2 years
        help_text="Number of days to extend access",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    extension_reason = forms.CharField(
        max_length=200,
        help_text="Reason for access extension",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = EqmdCustomUser
        fields = ['account_status', 'supervisor', 'department']
        widgets = {
            'account_status': forms.Select(attrs={'class': 'form-control'}),
            'supervisor': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_extension_days(self):
        days = self.cleaned_data['extension_days']
        
        if days > 365:
            # Require additional justification for extensions > 1 year
            if not self.cleaned_data.get('extension_reason'):
                raise ValidationError(
                    'Extensions longer than 1 year require detailed justification'
                )
        
        return days

class BulkExtensionForm(forms.Form):
    """Form for bulk user operations"""
    
    operation = forms.ChoiceField(
        choices=[
            ('extend_30', 'Extend access by 30 days'),
            ('extend_90', 'Extend access by 90 days'),
            ('extend_180', 'Extend access by 180 days'),
            ('mark_inactive', 'Mark as inactive'),
            ('reset_warnings', 'Reset expiration warnings'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    user_filter = forms.ChoiceField(
        choices=[
            ('selected', 'Selected users only'),
            ('role_resident', 'All residents'),
            ('role_student', 'All students'),
            ('status_expiring', 'All users expiring soon'),
            ('status_expired', 'All expired users'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    reason = forms.CharField(
        max_length=200,
        help_text="Reason for bulk operation",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    selected_users = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        operation = cleaned_data.get('operation')
        user_filter = cleaned_data.get('user_filter')
        
        # Validate that we have users to operate on
        if user_filter == 'selected' and not cleaned_data.get('selected_users'):
            raise ValidationError('No users selected for operation')
        
        return cleaned_data
```

## Reporting Interface

### Lifecycle Reports View

```python
# apps/accounts/views.py - Add reporting views

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
import csv
import json

@staff_member_required
def lifecycle_reports_view(request):
    """Generate and display lifecycle reports"""
    report_type = request.GET.get('type', 'summary')
    format_type = request.GET.get('format', 'html')
    
    # Generate report data based on type
    if report_type == 'expiration':
        report_data = generate_expiration_report()
    elif report_type == 'activity':
        report_data = generate_activity_report()
    elif report_type == 'renewals':
        report_data = generate_renewal_report()
    else:
        report_data = generate_summary_report()
    
    # Return appropriate format
    if format_type == 'json':
        return JsonResponse(report_data)
    elif format_type == 'csv':
        return export_report_csv(report_data, report_type)
    else:
        context = {
            'report_data': report_data,
            'report_type': report_type,
        }
        return TemplateResponse(request, 'admin/accounts/lifecycle_reports.html', context)

def generate_summary_report():
    """Generate comprehensive summary report"""
    now = timezone.now()
    
    # User counts by status
    status_counts = EqmdCustomUser.objects.filter(is_active=True).values(
        'account_status'
    ).annotate(count=Count('id'))
    
    # User counts by role
    role_counts = EqmdCustomUser.objects.filter(is_active=True).values(
        'profession_type'
    ).annotate(count=Count('id'))
    
    # Expiration timeline
    expiration_periods = {
        'overdue': Q(access_expires_at__lt=now),
        'next_week': Q(access_expires_at__range=(now, now + timedelta(days=7))),
        'next_month': Q(access_expires_at__range=(now, now + timedelta(days=30))),
        'next_quarter': Q(access_expires_at__range=(now, now + timedelta(days=90))),
    }
    
    expiration_counts = {}
    for period, query in expiration_periods.items():
        expiration_counts[period] = EqmdCustomUser.objects.filter(
            is_active=True
        ).filter(query).count()
    
    return {
        'generated_at': now.isoformat(),
        'summary': {
            'total_users': EqmdCustomUser.objects.filter(is_active=True).count(),
            'status_distribution': {item['account_status']: item['count'] for item in status_counts},
            'role_distribution': {str(item['profession_type']): item['count'] for item in role_counts},
            'expiration_timeline': expiration_counts,
        }
    }

def export_report_csv(report_data, report_type):
    """Export report data as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="lifecycle_report_{report_type}_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    if report_type == 'summary':
        # Write summary data
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Users', report_data['summary']['total_users']])
        writer.writerow([''])
        writer.writerow(['Status Distribution'])
        for status, count in report_data['summary']['status_distribution'].items():
            writer.writerow([status, count])
    
    # Add more report types as needed
    
    return response
```

## Configuration Interface

### Lifecycle Settings Admin

```python
# apps/core/admin.py - Add settings configuration

from django.contrib import admin
from django.conf import settings
from django import forms

class LifecycleSettingsForm(forms.Form):
    """Form for configuring lifecycle settings"""
    
    enable_activity_tracking = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Enable automatic user activity tracking"
    )
    
    inactivity_threshold_days = forms.IntegerField(
        initial=90,
        min_value=30,
        max_value=365,
        help_text="Days of inactivity before marking user as inactive"
    )
    
    expiration_warning_days = forms.CharField(
        initial="30,14,7,3,1",
        help_text="Comma-separated days before expiration to send warnings"
    )
    
    auto_suspend_inactive_days = forms.IntegerField(
        initial=180,
        min_value=90,
        max_value=730,
        help_text="Days of inactivity before auto-suspension"
    )
    
    default_resident_duration_months = forms.IntegerField(
        initial=12,
        min_value=6,
        max_value=60,
        help_text="Default duration for resident accounts (months)"
    )
    
    default_student_duration_months = forms.IntegerField(
        initial=6,
        min_value=3,
        max_value=24,
        help_text="Default duration for student accounts (months)"
    )

class LifecycleSettingsAdmin(admin.ModelAdmin):
    """Admin interface for lifecycle settings"""
    
    def has_module_permission(self, request):
        return request.user.is_superuser
    
    def changelist_view(self, request, extra_context=None):
        """Display settings configuration form"""
        if request.method == 'POST':
            form = LifecycleSettingsForm(request.POST)
            if form.is_valid():
                # Save settings to Django cache or database
                self._save_settings(form.cleaned_data)
                self.message_user(request, 'Lifecycle settings updated successfully.')
        else:
            # Load current settings
            current_settings = self._load_settings()
            form = LifecycleSettingsForm(initial=current_settings)
        
        context = {
            'title': 'Lifecycle Management Settings',
            'form': form,
        }
        context.update(extra_context or {})
        
        return TemplateResponse(request, 'admin/core/lifecycle_settings.html', context)
    
    def _load_settings(self):
        """Load current settings from configuration"""
        from django.core.cache import cache
        
        settings_key = 'lifecycle_management_settings'
        current_settings = cache.get(settings_key)
        
        if not current_settings:
            # Load from Django settings or defaults
            current_settings = {
                'enable_activity_tracking': getattr(settings, 'LIFECYCLE_ENABLE_ACTIVITY_TRACKING', True),
                'inactivity_threshold_days': getattr(settings, 'LIFECYCLE_INACTIVITY_THRESHOLD', 90),
                'expiration_warning_days': ','.join(map(str, getattr(settings, 'LIFECYCLE_WARNING_DAYS', [30, 14, 7, 3, 1]))),
                'auto_suspend_inactive_days': getattr(settings, 'LIFECYCLE_AUTO_SUSPEND_DAYS', 180),
                'default_resident_duration_months': 12,
                'default_student_duration_months': 6,
            }
            cache.set(settings_key, current_settings, timeout=3600)
        
        return current_settings
    
    def _save_settings(self, settings_data):
        """Save settings to cache and optionally database"""
        from django.core.cache import cache
        
        settings_key = 'lifecycle_management_settings'
        cache.set(settings_key, settings_data, timeout=None)  # Persist until manually cleared
```

## Mobile-Responsive Design

### Responsive Dashboard CSS

```css
/* static/css/admin_lifecycle.css */

/* Mobile-first responsive design for lifecycle dashboard */
@media (max-width: 768px) {
    .dashboard-grid {
        grid-template-columns: 1fr;
        gap: 15px;
        margin: 15px 0;
    }
    
    .metric-grid {
        grid-template-columns: 1fr;
        gap: 10px;
    }
    
    .metric-item {
        padding: 10px;
    }
    
    .metric-number {
        font-size: 1.5em;
    }
    
    /* Responsive table for user lists */
    .user-lifecycle-table {
        font-size: 14px;
    }
    
    .user-lifecycle-table td {
        padding: 8px 4px;
    }
    
    /* Stack action buttons vertically on mobile */
    .bulk-actions {
        flex-direction: column;
        gap: 10px;
    }
    
    .bulk-actions .button {
        width: 100%;
        text-align: center;
    }
}

/* Tablet adjustments */
@media (min-width: 769px) and (max-width: 1024px) {
    .dashboard-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    
    .metric-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* Status badge improvements */
.status-badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.status-badge.active { background: #28a745; color: white; }
.status-badge.expiring { background: #ffc107; color: #212529; }
.status-badge.expired { background: #dc3545; color: white; }
.status-badge.inactive { background: #6c757d; color: white; }
.status-badge.suspended { background: #343a40; color: white; }

/* Enhanced table styling */
.lifecycle-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}

.lifecycle-table th,
.lifecycle-table td {
    padding: 12px 8px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

.lifecycle-table th {
    background-color: #f8f9fa;
    font-weight: bold;
    color: #495057;
}

.lifecycle-table tr:hover {
    background-color: #f8f9fa;
}

/* Chart container improvements */
.chart-container {
    position: relative;
    height: 300px;
    margin: 20px 0;
}

@media (max-width: 768px) {
    .chart-container {
        height: 250px;
    }
}
```

## Integration with Existing Admin

### Admin Menu Integration

```python
# apps/core/admin.py - Add to existing admin configuration

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

# Custom admin site configuration
class LifecycleAdminSite(admin.AdminSite):
    site_header = "EquipeMed Administration"
    site_title = "EquipeMed Admin"
    index_title = "User Lifecycle Management"
    
    def index(self, request, extra_context=None):
        """Enhanced admin index with lifecycle quick stats"""
        extra_context = extra_context or {}
        
        # Add lifecycle quick stats to admin index
        from apps.accounts.models import EqmdCustomUser
        
        quick_stats = {
            'total_users': EqmdCustomUser.objects.filter(is_active=True).count(),
            'expired_users': EqmdCustomUser.objects.filter(
                is_active=True, 
                account_status='expired'
            ).count(),
            'expiring_soon': EqmdCustomUser.objects.filter(
                is_active=True,
                account_status='expiring_soon'
            ).count(),
        }
        
        extra_context['lifecycle_quick_stats'] = quick_stats
        
        return super().index(request, extra_context)

# Register custom admin site
lifecycle_admin_site = LifecycleAdminSite(name='lifecycle_admin')
```

## Performance Optimizations

### Query Optimization

```python
# apps/accounts/managers.py - Optimized querysets

from django.db import models
from django.utils import timezone
from datetime import timedelta

class LifecycleUserQuerySet(models.QuerySet):
    """Optimized querysets for lifecycle operations"""
    
    def with_lifecycle_data(self):
        """Prefetch related data for lifecycle operations"""
        return self.select_related(
            'supervisor', 'reviewed_by'
        ).prefetch_related(
            'renewal_requests'
        )
    
    def active_users(self):
        """Get active users only"""
        return self.filter(is_active=True)
    
    def expiring_soon(self, days=30):
        """Get users expiring within specified days"""
        cutoff = timezone.now() + timedelta(days=days)
        return self.filter(
            access_expires_at__lte=cutoff,
            access_expires_at__gte=timezone.now()
        )
    
    def expired(self):
        """Get expired users"""
        return self.filter(
            access_expires_at__lt=timezone.now()
        )
    
    def inactive(self, days=90):
        """Get inactive users"""
        cutoff = timezone.now() - timedelta(days=days)
        return self.filter(
            Q(last_meaningful_activity__lt=cutoff) |
            Q(last_meaningful_activity__isnull=True)
        )

class LifecycleUserManager(models.Manager):
    """Manager with lifecycle-specific methods"""
    
    def get_queryset(self):
        return LifecycleUserQuerySet(self.model, using=self._db)
    
    def with_lifecycle_data(self):
        return self.get_queryset().with_lifecycle_data()
    
    def dashboard_stats(self):
        """Get optimized stats for admin dashboard"""
        queryset = self.get_queryset().active_users()
        
        return {
            'total': queryset.count(),
            'by_status': dict(queryset.values_list('account_status').annotate(
                count=models.Count('id')
            )),
            'expiring_counts': {
                'next_7_days': queryset.expiring_soon(7).count(),
                'next_30_days': queryset.expiring_soon(30).count(),
                'expired': queryset.expired().count(),
            }
        }

# Add to EqmdCustomUser model
class EqmdCustomUser(AbstractUser):
    # ... existing fields ...
    
    objects = LifecycleUserManager()
```

## Testing Strategy

### Admin Interface Tests

```python
# apps/accounts/tests/test_admin_interface.py

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

class AdminLifecycleTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.force_login(self.admin_user)
        
        # Create test users
        self.active_user = get_user_model().objects.create_user(
            username='active_user',
            email='active@test.com',
            account_status='active'
        )
        
        self.expired_user = get_user_model().objects.create_user(
            username='expired_user',
            email='expired@test.com',
            account_status='expired',
            access_expires_at=timezone.now() - timedelta(days=5)
        )
    
    def test_lifecycle_dashboard_access(self):
        """Test admin can access lifecycle dashboard"""
        url = reverse('admin:accounts_eqmdcustomuser_lifecycle_dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Lifecycle Dashboard')
    
    def test_bulk_extension_action(self):
        """Test bulk access extension admin action"""
        url = reverse('admin:accounts_eqmdcustomuser_changelist')
        
        response = self.client.post(url, {
            'action': 'extend_access_30_days',
            '_selected_action': [self.expired_user.id]
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after action
        
        # Verify user was extended
        self.expired_user.refresh_from_db()
        self.assertTrue(self.expired_user.access_expires_at > timezone.now())
    
    def test_renewal_request_admin(self):
        """Test renewal request admin interface"""
        # Create renewal request
        renewal_request = AccountRenewalRequest.objects.create(
            user=self.expired_user,
            current_position='Test Position',
            department='Test Department',
            supervisor_name='Test Supervisor',
            supervisor_email='supervisor@test.com',
            renewal_reason='Test renewal',
            expected_duration_months=6
        )
        
        url = reverse('admin:accounts_accountrenewalrequest_change', args=[renewal_request.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Position')
```

## Success Metrics

### Administrative Efficiency

- ✅ **Dashboard Load Time**: <2 seconds for lifecycle dashboard
- ✅ **Bulk Operations**: Support for 100+ user operations efficiently
- ✅ **Report Generation**: Reports generated within 30 seconds
- ✅ **Mobile Usability**: Fully functional on tablet and mobile devices

### User Experience

- ✅ **Intuitive Interface**: Admins can perform common tasks without training
- ✅ **Visual Clarity**: Status indicators immediately comprehensible
- ✅ **Quick Access**: One-click access to common lifecycle operations
- ✅ **Error Prevention**: Clear validation and confirmation dialogs

---

**Next Phase**: [Phase 5: Advanced Features and Monitoring](phase_5_advanced_features.md)
