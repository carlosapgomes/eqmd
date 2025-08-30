from datetime import timedelta

# Simplified default expiration periods by role
ROLE_EXPIRATION_DEFAULTS = {
    0: None,                     # MEDICAL_DOCTOR - no auto expiration
    1: timedelta(days=365),      # RESIDENT - 1 year
    2: None,                     # NURSE - no auto expiration
    3: None,                     # PHYSIOTERAPIST - no auto expiration
    4: timedelta(days=180),      # STUDENT - 6 months
}

# Simple notification thresholds
NOTIFICATION_THRESHOLDS = {
    'expiration_warning_days': [30, 14, 7, 3, 1],  # Days before expiration
    'inactivity_threshold_days': 90,                # Days before marking inactive
}

# Simplified status transitions
STATUS_TRANSITIONS = {
    'active': ['expiring_soon', 'inactive', 'suspended', 'renewal_required'],
    'expiring_soon': ['active', 'expired', 'renewal_required'],
    'expired': ['active', 'departed'],
    'inactive': ['active', 'suspended', 'departed'],
    'suspended': ['active', 'departed'],
    'departed': [],  # Terminal status
    'renewal_required': ['active', 'suspended', 'expired'],
}