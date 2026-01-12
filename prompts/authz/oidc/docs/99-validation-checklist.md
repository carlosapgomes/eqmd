# Phase 99 – Validation Checklist

## Goal

Comprehensive validation of the entire bot delegation system before production deployment.

## Prerequisites

- All previous phases completed
- All migrations applied
- All tests passing

## Security Validation Checklist

### Authentication & Authorization

- [ ] **Bot Authentication**
  - [ ] Invalid client_id returns 401
  - [ ] Invalid client_secret returns 401
  - [ ] Suspended bot returns 401
  - [ ] Rate-limited bot returns 429

- [ ] **User Validation**
  - [ ] Unknown Matrix ID returns 403
  - [ ] Unverified binding returns 403
  - [ ] Inactive user returns 403
  - [ ] Expired user returns 403
  - [ ] User with wrong account_status returns 403

- [ ] **Scope Enforcement**
  - [ ] Unknown scope returns 403
  - [ ] Forbidden scope returns 403
  - [ ] Scope not in bot's allowed list returns 403
  - [ ] Non-doctor cannot delegate draft scopes

- [ ] **Token Validation**
  - [ ] Expired token returns 401
  - [ ] Malformed token returns 401
  - [ ] Token with wrong audience returns 401
  - [ ] Token with wrong issuer returns 401
  - [ ] Token for inactive user returns 401
  - [ ] Token for suspended bot returns 401

### Privilege Escalation Prevention

- [ ] Bot cannot request scopes beyond its allowed list
- [ ] Bot cannot request forbidden scopes (write, finalize, sign)
- [ ] Bot cannot access endpoints without proper scopes
- [ ] Bot cannot promote drafts to definitive documents
- [ ] Bot cannot modify user accounts
- [ ] Bot cannot access admin endpoints
- [ ] Bot cannot access other users' data

### Draft Lifecycle

- [ ] All bot-created content has `is_draft=True`
- [ ] Drafts have expiration time set
- [ ] Expired drafts are cleaned up
- [ ] Drafts do not appear in normal queries
- [ ] Only authorized users can promote drafts
- [ ] Promotion transfers authorship
- [ ] Bot references removed from promoted documents

### Kill Switch

- [ ] Kill switch immediately stops new delegations
- [ ] Kill switch check is fast (cached)
- [ ] Maintenance mode returns friendly message
- [ ] Admin can toggle kill switch
- [ ] CLI command works

### Audit Trail

- [ ] All delegation requests are logged
- [ ] All denied requests are logged with reason
- [ ] All bot actions are logged
- [ ] All draft promotions/rejections are logged
- [ ] Audit logs are immutable
- [ ] Audit logs include full context

## Functional Validation Checklist

### Matrix Integration

- [ ] User can create Matrix binding
- [ ] Verification token flow works
- [ ] Verified binding enables delegation
- [ ] User can revoke binding
- [ ] Revoked binding stops delegation

### Bot API

- [ ] Bot can list patients with scope
- [ ] Bot can view patient details with scope
- [ ] Bot can create daily note draft with scope
- [ ] Bot can generate summary with scope
- [ ] Missing scope returns 403

### Draft Management

- [ ] Physician can view their drafts
- [ ] Physician can review draft content
- [ ] Physician can edit draft before promotion
- [ ] Physician can promote draft
- [ ] Physician can reject draft
- [ ] Promoted document shows physician as author

### Human User Experience

- [ ] Login still works via allauth
- [ ] Session authentication still works
- [ ] Existing views exclude drafts
- [ ] No regression in existing functionality

## Performance Validation

- [ ] Delegation endpoint responds < 200ms
- [ ] Kill switch check adds < 5ms
- [ ] Scope validation adds < 10ms
- [ ] Database queries are optimized
- [ ] Cache is working correctly

## Test Commands

```bash
# Run all botauth tests
uv run pytest apps/botauth/tests/ -v

# Run with coverage
uv run pytest apps/botauth/tests/ --cov=apps/botauth --cov-report=html

# Security-specific tests
uv run pytest apps/botauth/tests/test_delegation.py -v
uv run pytest apps/botauth/tests/test_scopes.py -v
uv run pytest apps/botauth/tests/test_authentication.py -v

# Integration test
uv run python manage.py test apps.botauth --verbosity=2
```

## Manual Testing Scenarios

### Scenario 1: Happy Path
1. Create bot via management command
2. User creates and verifies Matrix binding
3. Bot requests delegated token
4. Bot creates daily note draft
5. Physician reviews and promotes draft
6. Verify final document has physician as author

### Scenario 2: Revocation
1. Complete Scenario 1 setup
2. Admin disables user account
3. Bot attempts to request new token
4. Verify token request fails
5. Existing token (if any) expires naturally

### Scenario 3: Kill Switch
1. Complete Scenario 1 setup
2. Admin activates kill switch
3. Bot attempts to request token
4. Verify request returns 503
5. Admin deactivates kill switch
6. Bot can request token again

### Scenario 4: Draft Expiration
1. Bot creates draft
2. Wait for draft to expire (or manually set past expiration)
3. Run cleanup command
4. Verify draft is deleted
5. Verify audit log records expiration

## Sign-Off

### Security Review
- [ ] Reviewed by security-aware team member
- [ ] Penetration testing completed (if applicable)
- [ ] No known vulnerabilities

### Code Review
- [ ] All code reviewed
- [ ] No hardcoded secrets
- [ ] Error handling is complete
- [ ] Logging is appropriate

### Documentation
- [ ] Architecture documented
- [ ] API documented
- [ ] Deployment guide updated
- [ ] Emergency procedures documented

### Deployment Readiness
- [ ] All migrations tested on production-like data
- [ ] Rollback plan documented
- [ ] Monitoring/alerting configured
- [ ] Cron jobs configured

## Final Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Security Review | | | |
| Clinical Lead | | | |
| Operations | | | |

## Post-Deployment Monitoring

First 24 hours:
- [ ] Monitor error rates
- [ ] Monitor delegation volume
- [ ] Monitor response times
- [ ] Check audit logs for anomalies
- [ ] Verify cleanup job runs

First week:
- [ ] Review all denied delegations
- [ ] Check for rate limit hits
- [ ] Gather user feedback
- [ ] Adjust rate limits if needed
