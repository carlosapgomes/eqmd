# Bot-Forbidden Endpoints

## Date: 2025-01-12

These endpoints MUST reject delegated bot tokens regardless of scope. Bots must NEVER access these endpoints under any circumstances.

## Administrative Endpoints

### User Management
- `/admin/\*` - All Django admin endpoints
- `/accounts/\*` - All django-allauth authentication endpoints  
- `/profiles/\*` - User profile management
- `/admin/pdf_forms/pdfformtemplate/<id>/preview-pdf/` - PDF template preview
- `/admin/pdf_forms/pdfformtemplate/<id>/save-fields/` - PDF field configuration
- `/admin/pdf_forms/pdfformtemplate/<id>/export-json/` - Template data export

**Rationale**: Administrative functions require human judgment and accountability. Bots must not have administrative capabilities.

## Document Finalization Endpoints

### Definitive Document Creation
- `/pdf/prescription/` - Generate prescription PDFs
- `/pdf/discharge-report/` - Generate discharge report PDFs  
- `/pdf/exam-request/` - Generate exam request PDFs

**Rationale**: PDF generation creates definitive clinical documents. Bots may only create drafts that require human review and approval.

### Future Document Promotion Endpoints
- Any endpoint that will set `is_draft=False` (to be created in future phases)
- Any endpoint that signs prescriptions (to be created in future phases)
- Any endpoint that finalizes discharge reports (to be created in future phases)

**Rationale**: Finalizing clinical documents is a physician's responsibility. Bots assist in drafting but never make final clinical decisions.

## Patient Status Management Endpoints

### Critical Status Changes
- `/patients/<uuid:patient_id>/admit/` - Admit patient to hospital
- `/patients/<uuid:patient_id>/discharge/` - Discharge patient from hospital
- `/patients/<uuid:patient_id>/transfer/` - Transfer patient between wards
- `/patients/<uuid:patient_id>/emergency/` - Emergency admission
- `/patients/<uuid:patient_id>/declare-death/` - Declare patient death

**Rationale**: Patient status changes have immediate clinical and operational consequences. These require human clinical judgment.

## Data Modification Endpoints

### Patient Personal Data
- `/patients/<uuid:patient_id>/edit/` - Edit patient personal data
- Any POST/PUT/PATCH endpoints that modify patient demographics
- Any endpoints that change patient identification information

**Rationale**: Personal data modification requires verification and human oversight. Bots may read but not modify patient identities.

### Content Modification Endpoints
- `/mediafiles/photo-series/<uuid:pk>/add-photo/` - Add photos to medical records
- `/mediafiles/photo-series/<uuid:pk>/remove-photo/<uuid:photo_id>/` - Remove photos
- `/mediafiles/photo-series/<uuid:pk>/reorder/` - Reorder medical photos
- Any endpoints that modify existing clinical content

**Rationale**: Modifying clinical records changes the medical timeline. Bots may create new content but not modify existing content.

## File Upload/Delete Endpoints

### File Operations
- `/mediafiles/fp/process/` - Upload medical images/videos
- `/mediafiles/fp/patch/` - Chunked file upload
- `/mediafiles/fp/revert/` - Revert file upload
- `/mediafiles/fp/restore/` - Restore interrupted upload
- `/mediafiles/fp/fetch/` - Fetch file from external URL
- Any DELETE endpoints for clinical data

**Rationale**: File upload and deletion capabilities could be abused for data exfiltration or data loss. Bots must not have file modification capabilities.

## Testing and Development Endpoints

### Development/Debugging
- `/test/role-permissions-api/` - Role permissions testing
- `/demo/permissions/api/` - Permission demo data
- `/test/permission-performance-api/` - Performance testing
- Any endpoints with `/test/` or `/demo/` in URL

**Rationale**: Testing endpoints may expose system internals and should never be accessible in production, especially by automated systems.

## Sensitive Configuration Endpoints

### System Configuration
- Any endpoints that modify hospital configuration
- Any endpoints that change system settings
- Any endpoints that manage user roles or permissions
- Any endpoints that access system logs or audit trails (for modification)

**Rationale**: System configuration changes have system-wide impact and require administrative human oversight.

## Future Protected Endpoints

### Endpoints to Be Created in Later Phases
- Any endpoint for draft promotion (`is_draft=False`)
- Any endpoint for prescription signing
- Any endpoint for clinical document finalization
- Any endpoint for user management operations
- Any endpoint for permission/role modifications
- Any endpoint for audit trail modifications

**Rationale**: These endpoints will be created in future OIDC implementation phases and must automatically inherit bot access restrictions.

## Enforcement Requirements

### Implementation Priority
1. **CRITICAL**: Administrative endpoints, file upload/delete, status changes
2. **HIGH**: Document finalization, patient data modification
3. **MEDIUM**: Content modification, configuration changes
4. **LOW**: Development/test endpoints (should be disabled in production)

### Technical Implementation
- Add explicit bot access checks to all these endpoints
- Return 403 Forbidden for any delegated token access
- Log all attempted bot access to these endpoints
- Monitor for attempted bypasses or abuse patterns
- Implement rate limiting as defense-in-depth

### Audit Requirements
- Every forbidden endpoint access attempt must be logged
- Logs must include: bot identity, physician identity, timestamp, endpoint
- Security alerts for repeated access attempts
- Regular review of access attempt patterns

## Special Cases

### Conditional Access
Some endpoints may have limited bot access under specific conditions:
- **Read-only access**: Bot may read but not modify
- **Draft-only operations**: Bot may create drafts but not finalize
- **Scope-restricted**: Bot may only access with explicit physician-granted scope

These special cases will be defined in the scope system implementation and must have explicit approval mechanisms.