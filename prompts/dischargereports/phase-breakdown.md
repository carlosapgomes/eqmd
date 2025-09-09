# Discharge Reports - Phase Breakdown

## Detailed Implementation Phases with Tasks

### Phase 1: Foundation (Core Model) - ~2-3 hours
**Goal**: Create the basic Django app structure and model

#### Tasks:
1. **Create Django App** (30 min)
   - Run `python manage.py startapp dischargereports`
   - Create proper directory structure
   - Add to INSTALLED_APPS

2. **Create DischargeReport Model** (1 hour)
   - Define model extending Event
   - Add all required fields with proper types and validation
   - Implement save(), get_absolute_url(), get_edit_url()
   - Add Meta class with Portuguese verbose names

3. **Create and Run Migration** (30 min)
   - Generate initial migration
   - Test migration runs successfully
   - Verify database table creation

4. **Basic Admin Setup** (30 min)
   - Create admin.py with ModelAdmin
   - Test admin interface displays correctly
   - Configure basic list display

**Deliverables**: Working model with admin interface

---

### Phase 2: Basic CRUD Operations - ~3-4 hours
**Goal**: Implement create, read, update, delete functionality

#### Tasks:
1. **Create Forms** (1 hour)
   - DischargeReportForm with all fields
   - Draft/save toggle implementation
   - Field validation and widgets

2. **Create Views** (1.5 hours)
   - CreateView (separate from update)
   - UpdateView 
   - DetailView
   - ListView with filtering
   - DeleteView (draft only)

3. **Create Templates** (1.5 hours)
   - Create form template (Bootstrap 5.3)
   - Update form template (different from create)
   - Detail template
   - List template
   - Delete confirmation template

4. **URL Configuration** (30 min)
   - Create urls.py with proper URL patterns
   - Include in main project URLs
   - Test all URLs work

**Deliverables**: Full CRUD interface working

---

### Phase 3: Event System Integration - ~2-3 hours
**Goal**: Integrate with patient timeline and event system

#### Tasks:
1. **Create Event Card Template** (1 hour)
   - event_card_dischargereport.html
   - Extend event_card_base.html
   - Show key info and action buttons

2. **Update Event Model** (30 min)
   - Verify DISCHARGE_REPORT_EVENT constant
   - Update badge/icon mappings
   - Test timeline display

3. **Timeline Integration** (1 hour)
   - Add discharge report filter option
   - Update filter JavaScript
   - Test filtering works

4. **Permission Integration** (30 min)
   - Test with different user roles
   - Verify 24h edit window for non-drafts
   - Test draft-only delete functionality

**Deliverables**: Discharge reports appear in timeline with proper filtering

---

### Phase 4: Print/PDF Generation - ~2-3 hours
**Goal**: Create print-friendly reports in Portuguese

#### Tasks:
1. **Create Print Template** (1.5 hours)
   - dischargereport_print.html
   - All required sections in Portuguese
   - Hospital branding and patient info
   - Proper pagination support

2. **Print View and CSS** (1 hour)
   - Create print view
   - Print-specific CSS styling
   - Test multi-page reports

3. **Add Print Buttons** (30 min)
   - Add to detail template
   - Add to event card template
   - Test print functionality

**Deliverables**: Professional PDF reports in Brazilian Portuguese

---

### Phase 5: Firebase Import Command - ~3-4 hours
**Goal**: Import existing discharge reports from Firebase

#### Tasks:
1. **Create Management Command** (2 hours)
   - import_firebase_discharge_reports.py
   - Command-line arguments and validation
   - Firebase connection and data fetching

2. **Data Mapping Logic** (1 hour)
   - Map Firebase fields to Django fields
   - Handle date conversions (strings to dates)
   - Patient lookup via PatientRecordNumber

3. **PatientAdmission Creation** (1 hour)
   - Create AdmissionRecord for each report
   - Set proper admission/discharge types
   - Calculate stay duration

4. **Testing and Documentation** (30 min)
   - Test with sample Firebase data
   - Create docs/apps/dischargereports.md with comprehensive feature documentation
   - Document Firebase import command usage and Docker examples

**Deliverables**: Working Firebase import command with feature documentation in docs/

---

### Phase 6: Advanced Features - ~2-3 hours
**Goal**: Draft logic, permissions, and polish

#### Tasks:
1. **Draft Logic Implementation** (1 hour)
   - Implement draft-only editing
   - Update templates to show draft status
   - Test save as draft vs save final

2. **Permission Refinement** (30 min)
   - Test all permission scenarios
   - Ensure proper access control
   - Verify 24h edit window after finalized

3. **UI Polish** (1 hour)
   - Improve form layouts
   - Add proper field help text
   - Responsive design testing

4. **Admin Enhancements** (30 min)
   - Improve admin list display
   - Add filters and search
   - Configure history tracking

**Deliverables**: Polished user interface with proper permissions

---

### Phase 7: Testing and Documentation - ~2-3 hours
**Goal**: Comprehensive testing and documentation

#### Tasks:
1. **Model and View Tests** (1.5 hours)
   - Unit tests for model methods
   - View tests for CRUD operations
   - Permission tests

2. **Integration Testing** (1 hour)
   - Timeline integration tests
   - Print functionality tests
   - Firebase import tests

3. **Documentation** (30 min)
   - Complete docs/apps/dischargereports.md with testing commands
   - Document new features and troubleshooting notes
   - Update any necessary project documentation

**Deliverables**: Comprehensive test suite and documentation

---

## Total Estimated Time: ~16-20 hours

## Critical Dependencies Between Phases:
- Phase 1 must complete before Phase 2
- Phase 3 depends on Phase 2 completion  
- Phase 4 can be developed in parallel with Phase 3
- Phase 5 requires Phase 1 model completion
- Phase 6 and 7 can be done after core functionality (Phases 1-3)

## Risk Mitigation:
- **Firebase Data Format**: Validate data structure early in Phase 5
- **Print Layout**: Test print CSS across different browsers in Phase 4
- **Timeline Integration**: Test with existing events to avoid conflicts in Phase 3
- **Permission System**: Thoroughly test draft logic in Phase 6

## Success Criteria:
- ✅ Discharge reports display in patient timeline
- ✅ Print generates professional Portuguese PDFs
- ✅ Firebase import successfully migrates existing data
- ✅ Draft system works as specified
- ✅ All CRUD operations work with proper permissions
- ✅ Responsive design works on mobile/desktop
- ✅ Comprehensive test coverage