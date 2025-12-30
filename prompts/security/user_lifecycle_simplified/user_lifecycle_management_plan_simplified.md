# User Lifecycle Management Implementation Plan (Simplified)

## Overview

This simplified plan implements **essential** user lifecycle management for EquipeMed, focusing on core security benefits while reducing complexity. Based on the current project scale (~50 users, ~8000 patients), this approach delivers critical security features quickly and efficiently.

## Problem Statement

**Current Issues:**

- No automated account expiration for residents/students
- Manual deactivation is error-prone and often delayed
- LGPD compliance risk from departed users retaining access
- No systematic tracking of user activity

**Security Risks:**

- Departed staff maintaining access to patient data
- Inactive accounts vulnerable to compromise
- Regulatory compliance violations
- Difficulty tracking who has current valid access

## Simplified Architecture Overview

### Core Components (Phases 1-3 Only)

1. **Minimal Database Schema**: Essential fields for expiration and activity tracking
2. **Middleware Enhancement**: Basic authentication flow integration for expired user blocking
3. **Essential Management Commands**: Automated daily tasks and basic admin tools
4. **Standard Django Admin**: Enhanced admin interface using existing Django admin (no custom dashboards)

### What's Different from Original Plan

**✅ Kept (Essential)**:

- Core expiration fields (`access_expires_at`, `expiration_reason`, `account_status`)
- Basic activity tracking (`last_meaningful_activity` - timestamp only)
- Role-specific fields (`internship_start_date`, `expected_duration_months`, `supervisor`)
- User lifecycle middleware for blocking expired users
- Essential management commands (expiration checking, notifications, user extension)
- Enhanced Django admin with lifecycle fields and bulk operations

**❌ Removed (Simplified)**:

- Access review workflow (`last_access_review`, `reviewed_by`, `next_review_due`)
- Complex activity scoring system (keeping simple timestamp)
- Custom dashboard views with Chart.js graphs
- Advanced analytics and predictive features
- API endpoints and external integrations
- Multi-channel notifications (email only)
- Advanced monitoring and compliance tools

## Implementation Phases (Simplified)

### Phase 1: Minimal Database Schema

**Timeline: 1 week**
**Priority: High**

Implement only essential database fields for expiration and basic activity tracking.

### Phase 2: Core Middleware and Logic

**Timeline: 1-2 weeks**
**Priority: High**

Basic authentication flow integration to block expired users and simple renewal workflow.

### Phase 3: Essential Management Commands

**Timeline: 1 week**
**Priority: Medium**

Core automation commands for daily expiration checking and email notifications only.

## Future Enhancements (Optional)

**Phase 4 (Future)**: Enhanced Admin Interface

- Custom dashboard views with visualizations
- Advanced bulk operations interface
- Renewal request management interface

**Phase 5 (Future)**: Advanced Features

- Predictive analytics and behavior analysis
- API endpoints for external integrations
- Multi-channel notifications (SMS, Slack)
- Advanced monitoring and compliance tools

## Success Criteria (Simplified)

- ✅ **Automated Expiration**: Users automatically disabled based on role-specific rules
- ✅ **Basic Activity Tracking**: Simple timestamp-based activity monitoring
- ✅ **Essential Admin Tools**: Django admin with lifecycle fields and basic bulk operations
- ✅ **Email Notifications**: Automated expiration warnings via email
- ✅ **Zero Disruption**: No impact on current user workflows during implementation

## Benefits of Simplified Approach

1. **Faster Delivery**: Core security features delivered in 3-4 weeks instead of 8-10 weeks
2. **Reduced Risk**: Fewer dependencies and external services to manage
3. **Focused Value**: Solves primary business problem without feature bloat
4. **Iterative Improvement**: Solid foundation for future enhancements based on actual usage

## Implementation Timeline

**Week 1**: Phase 1 - Database schema implementation and migrations
**Week 2-3**: Phase 2 - Middleware and core logic implementation  
**Week 4**: Phase 3 - Management commands and admin enhancements

**Total Estimated Time: 3-4 weeks** (vs 8-10 weeks for full plan)

---

**Next Steps**: Begin with [Phase 1: Simplified Database Schema](phase_1_database_schema_simplified.md)
