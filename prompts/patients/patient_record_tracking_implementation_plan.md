# Patient Record Tracking Implementation Plan

## Overview

This plan implements a hybrid approach combining separate models for record number tracking and admission/discharge tracking, with denormalized fields in the Patient model for performance, and Event integration for timeline visibility.

## Goals

1. Track patient record numbers with full change history
2. Track admission/discharge events with duration calculations
3. Maintain denormalized current values in Patient model for performance
4. Integrate with existing Event timeline system
5. Reuse existing template references and URL patterns
6. Provide complete audit trail for all changes

## Architecture Overview

```
Patient (denormalized current values)
├── PatientRecordNumber (historical record numbers)
│   └── RecordNumberChangeEvent (timeline integration)
└── PatientAdmission (admission/discharge history)
    ├── AdmissionEvent (timeline integration)
    └── DischargeEvent (timeline integration)
```

## Implementation Phases

### Phase 1: Core Models and Database Schema
**File**: `patient_record_tracking_phase1_models.md`
- Create PatientRecordNumber model
- Create PatientAdmission model
- Add denormalized fields to Patient model
- Create database migrations
- Update admin interfaces

### Phase 2: Event Integration and Timeline
**File**: `patient_record_tracking_phase2_events.md`
- Create RecordNumberChangeEvent model
- Create AdmissionEvent and DischargeEvent models
- Add new event types to Event.EVENT_TYPE_CHOICES
- Create event card templates for timeline
- Update event creation logic

### Phase 3: Business Logic and Automation
**File**: `patient_record_tracking_phase3_logic.md`
- Implement automatic denormalization updates
- Create signal handlers for data consistency
- Add duration calculation methods
- Implement status change automation
- Add validation and business rules

### Phase 4: User Interface and Forms
**File**: `patient_record_tracking_phase4_ui.md`
- Update patient forms with record number fields
- Create admission/discharge forms
- Update patient detail templates
- Restore and update hospital record templates
- Add quick action buttons

### Phase 5: API and Integration
**File**: `patient_record_tracking_phase5_api.md`
- Restore and update hospital record API endpoints
- Add new API endpoints for record tracking
- Update permission checks
- Add bulk operations support
- Update search functionality

### Phase 6: Testing and Validation
**File**: `patient_record_tracking_phase6_testing.md`
- Create comprehensive test suite
- Test data migration scenarios
- Validate business logic
- Performance testing
- Integration testing with existing features

## Dependencies

- Existing Event system
- Patient model and permissions
- Django admin integration
- Timeline template system
- Bootstrap 5 frontend components

## Success Criteria

1. ✅ Complete record number change history
2. ✅ Accurate admission/discharge tracking with duration calculations
3. ✅ Fast patient list queries using denormalized fields
4. ✅ Timeline visibility for all record changes
5. ✅ Backward compatibility with existing patient data
6. ✅ Full audit trail with user tracking
7. ✅ Restored functionality from multi-hospital implementation

## Risk Mitigation

- **Data Migration**: Comprehensive backup and rollback procedures
- **Performance**: Denormalized fields prevent query performance issues
- **Consistency**: Signal handlers maintain data integrity
- **User Experience**: Phased rollout with feature flags
- **Testing**: Extensive test coverage before production deployment

## Next Steps

1. Review and approve this implementation plan
2. Begin with Phase 1: Core Models and Database Schema
3. Implement phases sequentially with testing between each
4. Deploy with feature flags for gradual rollout