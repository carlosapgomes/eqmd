# User Lifecycle Management

**EquipeMed** includes a comprehensive user lifecycle management system to automatically handle user account expiration, activity tracking, and renewal workflows. This system is designed to enhance security by ensuring departed users lose access automatically while providing streamlined renewal processes for active users.

## Overview

The User Lifecycle Management system provides:

- **Automated Account Expiration**: Residents and students automatically lose access after defined periods
- **Activity Tracking**: Simple timestamp-based tracking of meaningful user activities  
- **Renewal Workflows**: Self-service renewal requests with administrative approval
- **Status Management**: Automatic status updates based on expiration and activity patterns
- **Email Notifications**: Automated warnings before account expiration
- **Administrative Tools**: Management commands for bulk operations and reporting

## Architecture

### Core Components

1. **Database Schema** (`apps/accounts/models.py`)
   - Essential expiration fields (`access_expires_at`, `expiration_reason`, `account_status`)
   - Simple activity tracking (`last_meaningful_activity`)
   - Role-specific fields (`internship_start_date`, `expected_duration_months`)
   - Supervisor relationships for approval workflows

2. **Middleware** (`apps/core/middleware.py`)
   - `UserLifecycleMiddleware` blocks access for expired/suspended users
   - Updates activity timestamps automatically
   - Handles status transitions and redirects

3. **Management Commands** (`apps/accounts/management/commands/`)
   - Daily automation commands for expiration checking and notifications
   - Administrative tools for user extension and bulk operations
   - Reporting commands for inactive user analysis

4. **Notification Service** (`apps/core/services/simple_notifications.py`)
   - Email-only notifications for expiration warnings
   - Renewal request notifications to administrators

## User Account Statuses

The system tracks users through these lifecycle statuses:

| Status | Description | Access Level |
|--------|-------------|--------------|
| `active` | Normal active user | Full access |
| `expiring_soon` | Expires within 30 days | Full access with warnings |
| `expired` | Past expiration date | Blocked access |
| `inactive` | No activity for 90+ days | Full access (flagged for review) |
| `suspended` | Administratively suspended | Blocked access |
| `departed` | No longer with institution | Permanently blocked |
| `renewal_required` | Must confirm renewal | Restricted to renewal workflow |

## Role-Based Expiration Rules

Default expiration periods by profession:

- **Medical Doctors**: No automatic expiration
- **Residents**: 1 year from start date
- **Nurses**: No automatic expiration  
- **Physiotherapists**: No automatic expiration
- **Students**: 6 months from start date

## Key Features

### 1. Automatic Expiration Checking

The system automatically:
- Updates user statuses based on expiration dates
- Transitions users from `active` → `expiring_soon` → `expired`
- Blocks access for expired users via middleware
- Logs all status changes for audit trails

### 2. Activity Tracking

Simple timestamp-based tracking:
- Updates `last_meaningful_activity` on significant actions
- Excludes static files, AJAX polling, and health checks
- Identifies inactive users for administrative review
- No complex scoring - just timestamps

### 3. Renewal Workflow

Self-service renewal process:
1. User accesses renewal form when required
2. Provides current position, supervisor info, and justification
3. Creates renewal request record for admin review
4. Email notification sent to administrators
5. Admin approves/denies via Django admin interface

### 4. Email Notifications

Automated email warnings sent at:
- 30 days before expiration
- 14 days before expiration
- 7 days before expiration
- 3 days before expiration
- 1 day before expiration

Rate limiting prevents spam (max one notification per week).

### 5. Administrative Tools

Management commands provide:
- Daily expiration checking and status updates
- Bulk user access extension
- Inactive user reporting
- Lifecycle data export to CSV
- Individual user access extension

## Integration with Existing Systems

### Middleware Stack Integration

The lifecycle middleware is positioned in the middleware stack after authentication and terms acceptance but before standard request processing:

```python
MIDDLEWARE = [
    # ... authentication middleware ...
    "apps.core.middleware.PasswordChangeRequiredMiddleware",
    "apps.core.middleware.TermsAcceptanceRequiredMiddleware", 
    "apps.core.middleware.UserLifecycleMiddleware",  # Lifecycle enforcement
    # ... other middleware ...
]
```

### Audit History Integration

All lifecycle changes are tracked through the existing audit history system:
- User status changes logged with reasons
- Admin actions tracked with user attribution  
- Historical data available through Django admin "History" buttons

### Permission System Integration

Lifecycle management respects existing permissions:
- Superusers bypass all lifecycle restrictions
- Medical staff have different expiration rules than students/residents
- Supervisor relationships enable approval workflows

## Security Considerations

### Data Protection
- Activity tracking uses simple timestamps (no sensitive patient data)
- All lifecycle changes logged in audit trails
- Supervisor assignments require proper admin permissions

### Privacy Compliance
- Minimal data collection (timestamps only)
- Clear expiration notifications to users
- Self-service renewal reduces administrative burden

### Access Control
- Expired users immediately blocked from all access
- Departed users cannot access system at all
- Renewal requests require supervisor verification

## Performance Impact

The system is designed for minimal performance impact:
- Simple database fields with appropriate indexes
- Efficient middleware with graceful error handling
- Activity updates only on meaningful actions
- Daily batch processing via management commands

## Monitoring and Alerting

### Logging
All lifecycle events are logged to `security.user_lifecycle` logger:
- Status transitions
- Access attempts by restricted users  
- Command execution results
- Error conditions

### Metrics
Key metrics tracked:
- Users by status distribution
- Expiration warning delivery success rate
- Renewal request processing time
- Command execution success/failure rates

## Future Enhancements

The current implementation provides essential functionality with room for growth:

### Phase 4 (Future): Enhanced Admin Interface
- Custom dashboard views with visualizations
- Advanced bulk operations interface  
- Renewal request management interface

### Phase 5 (Future): Advanced Features
- Predictive analytics and behavior analysis
- API endpoints for external integrations
- Multi-channel notifications (SMS, Slack)
- Advanced monitoring and compliance tools

## Related Documentation

- [Admin Setup Guide](user-lifecycle-admin-setup.md) - Detailed setup and configuration instructions
- [Management Commands Reference](user-lifecycle-commands.md) - Complete command documentation
- [Cronjob Setup](user-lifecycle-cronjobs.md) - Automated scheduling configuration
- [Audit History](audit-history.md) - General audit system documentation
- [Permissions System](../permissions/) - Role-based access control documentation

## Support

For implementation questions or issues:
1. Check the admin setup guide for configuration steps
2. Review management command documentation for usage examples
3. Check logs in `/var/log/django/` for error details
4. Consult existing audit history documentation for context