# API Endpoint Inventory

## Date: 2025-01-12

## Core Application API Endpoints

### Medical Procedures API

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/api/procedures/search/` | GET | @login_required | Search medical procedures database | ALLOW - SCOPE: procedure:read |
| `/api/procedures/<uuid:procedure_id>/` | GET | @login_required | Get specific procedure details | ALLOW - SCOPE: procedure:read |
| `/api/procedures/` | GET | @login_required | List procedures with pagination | ALLOW - SCOPE: procedure:read |

### System Configuration APIs

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/manifest.json` | GET | None | Hospital configuration, PWA manifest | DENY - Public endpoint |
| `/test/permission-performance-api/` | GET | @login_required | Permission system performance metrics | DENY - Testing endpoint |

## Patient Management API Endpoints

### Patient Record APIs

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/patients/api/<uuid:patient_id>/record-numbers/` | GET | LoginRequiredMixin + patients.view_patientrecordnumber | Patient record number history | ALLOW - SCOPE: patient:read |
| `/patients/api/<uuid:patient_id>/admissions/` | GET | LoginRequiredMixin + patients.view_patientadmission | Patient admission/discharge history | ALLOW - SCOPE: patient:read |
| `/patients/api/record-number/<str:record_number>/` | GET | LoginRequiredMixin + patients.view_patient | Patient lookup by record number | ALLOW - SCOPE: patient:read |
| `/patients/api/admission/<uuid:admission_id>/` | GET | LoginRequiredMixin + patients.view_patientadmission | Specific admission details | ALLOW - SCOPE: patient:read |
| `/patients/api/patients/search/` | GET | LoginRequiredMixin + patients.view_patient | Patient database search/autocomplete | ALLOW - SCOPE: patient:read |

### Patient Tags API

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/patients/<uuid:patient_id>/tags/api/` | GET | LoginRequiredMixin + custom permission | Patient tags and metadata | SCOPE: patient:read |

## Events Timeline API Endpoints

### Event Data APIs

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/events/<uuid:pk>/api/` | GET | @login_required + patient access check | Event details from medical timeline | ALLOW - SCOPE: exam:read |

## Clinical Research API Endpoints

### Full-Text Search APIs

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/research/search-ajax/` | GET | @login_required + researcher role check | Full-text search across daily notes | SCOPE: summary:generate |

## Sample Content API Endpoints

### Template Management APIs

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/sample-content/api/event-type/<str:event_type>/` | GET | Superuser only | Template content for medical events | DENY - Admin only |

## Media Files API Endpoints

### Photo Management APIs

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/mediafiles/photo-series/<uuid:pk>/add-photo/` | POST | @login_required + patient access check | Add photo to existing series | DENY - File modification |
| `/mediafiles/photo-series/<uuid:pk>/remove-photo/<uuid:photo_id>/` | POST | @login_required + patient access check | Remove photo from series | DENY - File deletion |
| `/mediafiles/photo-series/<uuid:pk>/reorder/` | POST | @login_required + patient access check | Reorder photos in series | DENY - Content modification |

### File Serving APIs

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/mediafiles/serve/<uuid:file_id>/` | GET | @login_required + permission checks | Serve medical images/videos | ALLOW - SCOPE: patient:read |
| `/mediafiles/thumbnail/<uuid:file_id>/` | GET | @login_required + permission checks | Serve medical image thumbnails | ALLOW - SCOPE: patient:read |
| `/mediafiles/secure/<uuid:file_id>/` | GET | @login_required + permission checks | Secure file serving | ALLOW - SCOPE: patient:read |
| `/mediafiles/secure/thumbnail/<uuid:file_id>/` | GET | @login_required + permission checks | Secure thumbnails | ALLOW - SCOPE: patient:read |

## Prescriptions API Endpoints

### Drug Template APIs

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/prescriptions/ajax/drug-template/<uuid:template_id>/` | GET | @login_required + template ownership | Get specific drug template | ALLOW - SCOPE: prescription:read |
| `/prescriptions/ajax/drug-templates/search/` | GET | @login_required + template ownership | Search drug templates | ALLOW - SCOPE: prescription:read |
| `/prescriptions/ajax/prescription-template/<uuid:template_id>/` | GET | @login_required + template ownership | Get prescription template | ALLOW - SCOPE: prescription:read |

## PDF Generation API Endpoints

### Document Generation APIs

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/pdf/prescription/` | POST | LoginRequiredMixin + medical staff | Generate prescription PDF | DENY - Creates definitive documents |
| `/pdf/discharge-report/` | POST | LoginRequiredMixin + medical staff | Generate discharge report PDF | DENY - Creates definitive documents |
| `/pdf/exam-request/` | POST | LoginRequiredMixin + medical staff | Generate exam request PDF | DENY - Creates definitive documents |

## PDF Forms Admin API Endpoints

### Admin Configuration APIs

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/admin/pdf_forms/pdfformtemplate/<id>/preview-pdf/` | GET | Admin user + change permission | PDF form template preview | DENY - Admin only |
| `/admin/pdf_forms/pdfformtemplate/<id>/save-fields/` | POST | Admin user + change permission | Save PDF field configuration | DENY - Admin configuration |
| `/admin/pdf_forms/pdfformtemplate/<id>/export-json/` | GET | Admin user + change permission | Export template as JSON | DENY - Admin data export |

## File Upload API Endpoints

### FilePond Upload APIs

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/mediafiles/fp/process/` | POST | DRF SessionAuthentication | Upload medical images/videos | DENY - File upload capability |
| `/mediafiles/fp/patch/` | PATCH | DRF SessionAuthentication | Chunked file upload | DENY - File upload capability |
| `/mediafiles/fp/revert/` | DELETE | DRF SessionAuthentication | Revert file upload | DENY - File deletion capability |
| `/mediafiles/fp/load/` | GET | DRF SessionAuthentication | Load file from server | DENY - File access capability |
| `/mediafiles/fp/restore/` | GET | DRF SessionAuthentication | Restore interrupted upload | DENY - File upload capability |
| `/mediafiles/fp/fetch/` | GET | DRF SessionAuthentication | Fetch file from URL | DENY - External file fetching |

## Testing/Demo API Endpoints

### Development Test APIs

| URL | Methods | Auth | Data Access | Bot Access |
| --- | --- | --- | --- | --- |
| `/test/role-permissions-api/` | GET | @login_required | User role permission information | DENY - Testing endpoint |
| `/demo/permissions/api/` | GET | @login_required | Permission system demo data | DENY - Testing endpoint |

## Summary Statistics

- **Total Endpoints Identified**: 38
- **Public Endpoints**: 1 (manifest.json)
- **Authenticated Endpoints**: 37
- **Admin-Only Endpoints**: 3
- **File Upload/Delete Endpoints**: 6
- **Search/Autocomplete Endpoints**: 5

## Security Categories

### High-Risk Endpoints (Require Strict Bot Control)
- File upload/delete operations (6 endpoints)
- Admin configuration endpoints (3 endpoints)
- PDF generation for definitive documents (3 endpoints)
- Photo modification operations (3 endpoints)

### Medium-Risk Endpoints (Require Scoped Bot Access)
- Patient data access (7 endpoints)
- Medical record access (1 endpoint)
- Prescription template access (3 endpoints)
- Media file serving (4 endpoints)

### Low-Risk Endpoints (Bot-Friendly with Proper Scope)
- Medical procedures lookup (3 endpoints)
- Search/autocomplete functionality (2 endpoints)
- Clinical research search (1 endpoint)

## Recommendations for Bot Access Implementation

1. **Implement scope-based access control** for all medium-risk endpoints
2. **Strictly deny bot access** to all high-risk endpoints
3. **Add rate limiting** to all search endpoints to prevent data harvesting
4. **Implement audit logging** for all bot-accessible endpoints
5. **Consider read-only replicas** for heavy read operations by bots
6. **Add request throttling** for computationally expensive operations like PDF generation