# User Acceptance Testing Documentation

# MediaFiles Photo Functionality - Single Image Implementation

## Overview

This document outlines the User Acceptance Testing (UAT) scenarios for the MediaFiles photo functionality in the EquipeMed medical collaboration platform. These tests validate that the system meets the real-world needs of healthcare professionals.

## Test Environment Setup

### Prerequisites

- Django test environment with mediafiles app installed
- Test database with sample users and patients
- Temporary media storage configured
- All security settings properly configured

### Test Data

- Medical professional users (doctors, nurses)
- Patient records with appropriate permissions
- Sample medical images (X-rays, wound photos, diagnostic images)
- Various file types and sizes for validation testing

## UAT Scenarios

### Scenario 1: Emergency Room X-ray Upload

**User Story**: As an emergency room doctor, I need to quickly upload and view X-ray images during patient examination to make immediate treatment decisions.

**Acceptance Criteria**:

- [ ] Doctor can access photo upload form from patient record
- [ ] Upload form accepts JPEG, PNG, WebP images up to 5MB
- [ ] Form includes medical description and timestamp fields
- [ ] Upload completes within 2 seconds for typical X-ray files
- [ ] Photo appears immediately in patient timeline
- [ ] Photo can be viewed in full resolution for diagnosis
- [ ] File is stored securely with UUID-based filename
- [ ] Original filename is preserved for reference

**Test Steps**:

1. Login as emergency room doctor
2. Navigate to patient record
3. Click "Add Photo" or similar upload button
4. Select X-ray image file (2-3MB JPEG)
5. Enter description: "Chest X-ray - Emergency admission, suspected pneumonia"
6. Add clinical notes in caption field
7. Set event datetime to current time
8. Submit form
9. Verify photo appears in patient timeline
10. Click photo to view full resolution
11. Verify all metadata is correctly displayed

**Expected Results**:

- Upload completes successfully within 2 seconds
- Photo is immediately visible in patient timeline
- Full resolution image loads quickly (<1 second)
- All metadata (description, timestamp, creator) is accurate
- File is stored securely (UUID filename, no patient info in path)

### Scenario 2: Wound Care Progress Documentation

**User Story**: As a wound care nurse, I need to document wound healing progress with photos to track patient recovery and adjust treatment plans.

**Acceptance Criteria**:

- [ ] Nurse can upload multiple photos for same patient
- [ ] Photos can be edited within 24-hour window
- [ ] Caption field supports detailed clinical notes
- [ ] Photos are chronologically ordered in timeline
- [ ] Each photo maintains audit trail (creator, timestamps)
- [ ] Photos integrate with existing event system

**Test Steps**:

1. Login as wound care nurse
2. Upload initial wound photo with description "Post-surgical wound - Day 1"
3. Add detailed caption with wound assessment
4. Verify photo appears in timeline
5. Within 24 hours, edit photo to add additional notes
6. Upload follow-up photo "Post-surgical wound - Day 7"
7. Verify both photos appear chronologically
8. Attempt to edit photo after 24-hour window (should be restricted)

**Expected Results**:

- Both photos upload successfully
- Photos appear in correct chronological order
- Edit functionality works within 24-hour window
- Edit restrictions enforced after 24 hours
- All clinical notes are preserved and displayed

### Scenario 3: Specialist Consultation Photo Sharing

**User Story**: As a primary care physician, I need to share patient photos with specialists for remote consultation while maintaining patient privacy.

**Acceptance Criteria**:

- [ ] Photos are stored with secure, non-identifiable filenames
- [ ] Access is restricted to authorized healthcare providers
- [ ] Original filename is preserved for medical reference
- [ ] File serving includes proper security headers
- [ ] Unauthorized access attempts are blocked
- [ ] Audit trail tracks all photo access

**Test Steps**:

1. Login as primary care physician
2. Upload diagnostic photo for specialist consultation
3. Verify file is stored with UUID filename
4. Verify original filename is preserved in database
5. Test authorized access to photo
6. Test unauthorized access (different user without patient access)
7. Verify security headers in file serving response

**Expected Results**:

- File stored with secure UUID filename
- Original filename preserved for reference
- Authorized users can access photo
- Unauthorized users receive 403/404 error
- Security headers present in responses

### Scenario 4: Patient Timeline Integration

**User Story**: As a healthcare provider, I need to see patient photos integrated chronologically with other medical events in the patient timeline.

**Acceptance Criteria**:

- [ ] Photos appear as events in patient timeline
- [ ] Photos are ordered chronologically with other events
- [ ] Photo events display appropriate metadata
- [ ] Timeline performance remains good with multiple photos
- [ ] Photos can be filtered/searched within timeline
- [ ] Event type is correctly set to PHOTO_EVENT

**Test Steps**:

1. Create patient with existing medical events
2. Upload photos at different timestamps
3. View patient timeline
4. Verify photos appear chronologically
5. Verify photo events show correct metadata
6. Test timeline performance with 10+ photos
7. Test filtering/searching functionality

**Expected Results**:

- Photos integrate seamlessly with timeline
- Chronological ordering is correct
- Performance remains acceptable
- All metadata displays correctly

### Scenario 5: File Security and Validation

**User Story**: As a system administrator, I need to ensure that only safe, valid medical images can be uploaded and that all security measures are properly enforced.

**Acceptance Criteria**:

- [ ] Only allowed file types (JPEG, PNG, WebP) are accepted
- [ ] File size limits are enforced (5MB for images)
- [ ] Malicious files are detected and rejected
- [ ] Path traversal attacks are prevented
- [ ] File content is validated (not just extension)
- [ ] Error messages are user-friendly

**Test Steps**:

1. Attempt to upload various file types (valid and invalid)
2. Test file size limits with oversized files
3. Test malicious file upload attempts
4. Test files with misleading extensions
5. Verify error handling and user feedback
6. Test filename sanitization

**Expected Results**:

- Only valid image files are accepted
- File size limits are enforced
- Malicious files are rejected
- Security validations work correctly
- User receives clear error messages

## Performance Acceptance Criteria

### Upload Performance

- [ ] Image upload completes within 2 seconds for files up to 5MB
- [ ] Thumbnail generation completes within 1 second
- [ ] Form submission provides immediate feedback
- [ ] Multiple uploads don't significantly degrade performance

### Viewing Performance

- [ ] Photo detail view loads within 1 second
- [ ] File serving responds within 0.5 seconds
- [ ] Thumbnail serving responds within 0.3 seconds
- [ ] Timeline with 20+ photos loads within 2 seconds

### Database Performance

- [ ] Photo queries use optimized select_related
- [ ] No N+1 query problems in photo lists
- [ ] Database operations complete within acceptable timeframes

## Security Acceptance Criteria

### File Security

- [ ] All files stored with UUID-based filenames
- [ ] No patient information in file paths
- [ ] File extension validation works correctly
- [ ] MIME type validation prevents spoofing
- [ ] File content validation detects malicious files

### Access Security

- [ ] Authentication required for all photo operations
- [ ] Authorization enforced based on patient access
- [ ] File enumeration attacks prevented
- [ ] Direct file access blocked
- [ ] Audit logging captures all access attempts

## Integration Acceptance Criteria

### Event System Integration

- [ ] Photos properly extend Event model
- [ ] Event type set correctly (PHOTO_EVENT = 3)
- [ ] Timeline integration works seamlessly
- [ ] Permission system integration functions correctly

### User Interface Integration

- [ ] Photo upload forms integrate with existing UI
- [ ] Photo display integrates with patient views
- [ ] Navigation between photos and other events works
- [ ] Mobile responsiveness maintained

## Regression Testing

### Existing Functionality

- [ ] Patient management still works correctly
- [ ] Other event types unaffected
- [ ] User authentication/authorization unchanged
- [ ] System performance not degraded

### Data Integrity

- [ ] Existing patient data preserved
- [ ] Database migrations complete successfully
- [ ] No data corruption during photo operations

## Sign-off Criteria

The MediaFiles photo functionality is considered ready for production when:

1. **All UAT scenarios pass** - 100% success rate on all test scenarios
2. **Performance criteria met** - All performance benchmarks achieved
3. **Security validation complete** - All security tests pass
4. **Integration verified** - Seamless integration with existing system
5. **User feedback positive** - Healthcare professionals approve usability
6. **Documentation complete** - All user and technical documentation ready

## Test Execution Log

| Scenario | Date | Tester | Status | Notes |
|----------|------|--------|--------|-------|
| Emergency X-ray Upload | | | | |
| Wound Care Documentation | | | | |
| Specialist Consultation | | | | |
| Timeline Integration | | | | |
| Security Validation | | | | |

## Issues and Resolutions

| Issue ID | Description | Severity | Status | Resolution |
|----------|-------------|----------|--------|------------|
| | | | | |

## Final Approval

- [ ] Medical Professional Review: _________________ Date: _______
- [ ] IT Security Review: _________________ Date: _______
- [ ] System Administrator Review: _________________ Date: _______
- [ ] Project Manager Approval: _________________ Date: _______

---

**Document Version**: 1.0  
**Last Updated**: [Current Date]  
**Next Review**: [Date + 6 months]
