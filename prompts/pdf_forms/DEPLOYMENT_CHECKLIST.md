# PDF Forms App - Deployment Checklist

## Phase 12: Documentation and Deployment

This checklist ensures proper deployment of the PDF Forms app in production environments.

## Pre-Deployment Requirements

### 1. Dependencies Installation
- [ ] **ReportLab installed**: `uv add reportlab`
- [ ] **PyPDF2 installed**: `uv add pypdf2` (or `uv add pypdf` as alternative)
- [ ] **Dependencies verified**: Check `uv lock` for PDF processing libraries

### 2. Media Directories Setup
- [ ] **Base media directory exists**: Verify `MEDIA_ROOT` directory permissions
- [ ] **PDF forms directories created**: 
  ```bash
  mkdir -p media/pdf_forms/templates
  mkdir -p media/pdf_forms/completed
  chmod 755 media/pdf_forms/
  chmod 755 media/pdf_forms/templates/
  chmod 755 media/pdf_forms/completed/
  ```
- [ ] **Directory permissions verified**: Web server can read/write to media directories

### 3. Environment Variables Configuration
- [ ] **PDF forms enabled**: `HOSPITAL_PDF_FORMS_ENABLED=true`
- [ ] **Templates path set**: `HOSPITAL_PDF_FORMS_PATH=/path/to/templates` (optional)
- [ ] **File size limit**: `PDF_FORMS_MAX_FILE_SIZE=10485760` (10MB default)
- [ ] **Form validation**: `PDF_FORMS_REQUIRE_VALIDATION=true` (recommended)

Example `.env` configuration:
```bash
# PDF Forms Configuration
HOSPITAL_PDF_FORMS_ENABLED=true
HOSPITAL_PDF_FORMS_PATH=/app/media/pdf_forms/templates/
PDF_FORMS_MAX_FILE_SIZE=10485760  # 10MB
PDF_FORMS_REQUIRE_VALIDATION=true
```

## Database Setup

### 4. Migrations
- [ ] **App added to INSTALLED_APPS**: Verify `'apps.pdf_forms'` in `config/settings.py`
- [ ] **Migrations created**: `uv run python manage.py makemigrations pdf_forms`
- [ ] **Migrations applied**: `uv run python manage.py migrate`
- [ ] **Database tables verified**: Check `pdf_forms_pdfformtemplate` and `pdf_forms_pdfformsubmission` tables exist

### 5. Event System Integration
- [ ] **Event type added**: Verify `PDF_FORM_EVENT = 11` in `apps/events/models.py`
- [ ] **Event choices updated**: Check `EVENT_TYPE_CHOICES` includes PDF Form entry
- [ ] **Timeline integration**: Test PDF submissions appear in patient timeline

## Static Files and Assets

### 6. Static Files Collection
- [ ] **CSS files collected**: Verify `pdf_forms/css/pdf_forms.css` in static root
- [ ] **JavaScript files collected**: Verify `pdf_forms/js/pdf_forms.js` in static root
- [ ] **Static files served**: Test static file serving in production environment
- [ ] **Icons and images**: Verify PDF icons load correctly

### 7. Template Integration
- [ ] **Base template extends**: Verify `pdf_forms/base.html` extends `base_app.html`
- [ ] **Timeline cards render**: Test PDF form event cards display properly
- [ ] **Bootstrap styling**: Verify CSS classes and Bootstrap integration work

## Security and Permissions

### 8. File System Permissions
- [ ] **Media directory writable**: Web server can create files in `/media/pdf_forms/`
- [ ] **Secure file serving**: PDF files only accessible through Django views
- [ ] **UUID file naming**: Generated PDFs use UUID-based filenames
- [ ] **File validation**: Upload validation prevents malicious files

### 9. User Permissions
- [ ] **Patient access control**: Users can only access forms for patients they have permission to view
- [ ] **Role-based access**: Verify different user types can access PDF forms appropriately
- [ ] **Admin permissions**: Superusers can manage PDF form templates

## Production Configuration

### 10. Settings Validation
- [ ] **PDF forms configuration**: Verify `PDF_FORMS_CONFIG` in `config/settings.py`
- [ ] **Media URL serving**: Ensure media files serve correctly in production
- [ ] **File upload limits**: Configure appropriate file size limits
- [ ] **Error handling**: Test error scenarios (missing files, invalid PDFs)

Example production configuration:
```python
# config/settings.py
PDF_FORMS_CONFIG = {
    'enabled': True,
    'templates_path': '/app/media/pdf_forms/templates/',
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'allowed_extensions': ['.pdf'],
    'require_form_validation': True,
}

# Ensure media directories exist
if PDF_FORMS_CONFIG['enabled']:
    PDF_FORMS_MEDIA_ROOT = MEDIA_ROOT / 'pdf_forms'
    PDF_FORMS_MEDIA_ROOT.mkdir(exist_ok=True)
    (PDF_FORMS_MEDIA_ROOT / 'templates').mkdir(exist_ok=True)
    (PDF_FORMS_MEDIA_ROOT / 'completed').mkdir(exist_ok=True)
```

## Hospital-Specific Setup

### 11. PDF Template Upload
- [ ] **Template files uploaded**: Hospital-specific PDF forms uploaded to admin
- [ ] **Field configuration**: Form fields configured with coordinate positioning
- [ ] **Template testing**: Test form filling with sample data
- [ ] **PDF generation**: Verify generated PDFs have correct overlay positioning

### 12. Sample Data Creation
- [ ] **Sample templates created**: `uv run python manage.py create_sample_pdf_forms`
- [ ] **Test submissions**: Create test PDF form submissions
- [ ] **Download functionality**: Test PDF download and viewing

## Testing and Validation

### 13. Functional Testing
- [ ] **Form selection**: Test PDF form selection for patients
- [ ] **Form filling**: Test dynamic form generation and submission
- [ ] **PDF generation**: Verify PDF overlay creation works correctly
- [ ] **Timeline integration**: Check PDF submissions appear in patient timeline
- [ ] **Download/view**: Test PDF download and viewing functionality

### 14. Test Suite Execution
- [ ] **Unit tests pass**: `uv run python manage.py test apps.pdf_forms.tests`
- [ ] **Integration tests**: Test form workflow end-to-end
- [ ] **Permission tests**: Verify access control works correctly
- [ ] **File handling tests**: Test file upload, generation, and download

### 15. Performance and Security Testing
- [ ] **File size limits**: Test maximum file size enforcement
- [ ] **Invalid file handling**: Test handling of non-PDF files
- [ ] **Permission boundaries**: Test access to unauthorized patient forms
- [ ] **Error scenarios**: Test missing templates, corrupted files

## URL Configuration

### 16. URL Integration
- [ ] **App URLs included**: Verify `path('pdf-forms/', include('apps.pdf_forms.urls'))` in main URLs
- [ ] **URL patterns work**: Test all PDF form URL patterns
- [ ] **Menu integration**: Add PDF forms menu items if applicable
- [ ] **Navigation tested**: Verify all form workflow navigation works

## Monitoring and Logging

### 17. Production Monitoring
- [ ] **Error logging**: Configure logging for PDF generation errors
- [ ] **File operations**: Log file uploads, downloads, and generation
- [ ] **Performance monitoring**: Monitor PDF generation performance
- [ ] **Storage monitoring**: Monitor media directory disk usage

### 18. Health Checks
- [ ] **Service availability**: PDF forms functionality accessible
- [ ] **Dependency verification**: ReportLab and PyPDF2 working correctly
- [ ] **File generation**: Test PDF generation under load
- [ ] **Database performance**: Monitor PDF form queries

## Documentation

### 19. User Documentation
- [ ] **Admin guide**: Document PDF template configuration process
- [ ] **User guide**: Document form filling workflow for medical staff
- [ ] **Field configuration**: Document coordinate-based positioning system
- [ ] **Troubleshooting**: Common issues and solutions documented

### 20. Technical Documentation
- [ ] **API documentation**: Document PDF form models and services
- [ ] **Configuration guide**: Environment variables and settings
- [ ] **Deployment notes**: Hospital-specific deployment considerations
- [ ] **Maintenance guide**: Backup, monitoring, and update procedures

## Post-Deployment Verification

### 21. Final Validation
- [ ] **End-to-end workflow**: Complete form filling workflow works
- [ ] **Multi-user testing**: Multiple users can access forms simultaneously
- [ ] **Data integrity**: Form submissions properly linked to patients and events
- [ ] **Backup verification**: PDF files included in backup procedures

### 22. Go-Live Checklist
- [ ] **Hospital staff trained**: Medical staff familiar with PDF forms workflow
- [ ] **Admin access configured**: Superusers can manage PDF templates
- [ ] **Support procedures**: Help desk familiar with PDF forms functionality
- [ ] **Rollback plan**: Procedure to disable PDF forms if issues arise

## Emergency Procedures

### Quick Disable
If issues arise, PDF forms can be quickly disabled:
```bash
# Disable PDF forms
export HOSPITAL_PDF_FORMS_ENABLED=false
# Restart application
```

### Common Issues and Solutions

1. **PDF generation fails**: Check ReportLab installation and dependencies
2. **Files not accessible**: Verify media directory permissions
3. **Forms not displaying**: Check template configuration and static files
4. **Permission errors**: Verify user has patient access permissions

## Success Criteria

Deployment is successful when:
- [ ] All checklist items completed
- [ ] Test PDF forms can be filled and generated
- [ ] Generated PDFs display correctly with proper field overlays
- [ ] All user types can access forms according to permissions
- [ ] Performance is acceptable for expected user load
- [ ] Error handling works gracefully
- [ ] Hospital staff can successfully use the system

---

**Deployment Date**: ___________  
**Deployed By**: ___________  
**Hospital**: ___________  
**Version**: ___________