# Phase 7: Testing Refactor

**Estimated Time:** 60-90 minutes  
**Complexity:** Medium  
**Dependencies:** Phase 6 completed

## Objectives

1. Remove hospital-related test cases
2. Update existing tests to work without hospital context
3. Ensure core functionality tests still pass
4. Update test fixtures and factories
5. Add new tests for simplified permission system

## Tasks

### 1. Remove Hospital App Tests

**Delete hospital-specific test files:**

- [ ] Delete `apps/hospitals/tests/` (entire directory)
- [ ] Remove hospital model tests
- [ ] Remove hospital view tests
- [ ] Remove hospital form tests

### 2. Update Permission System Tests

**Simplify permission tests (`apps/core/tests/test_permissions.py`):**

**Remove hospital-context tests:**

- [ ] Remove `test_hospital_context_required`
- [ ] Remove `test_patient_hospital_access`
- [ ] Remove `test_cross_hospital_access`
- [ ] Remove hospital membership tests

**Update role-based permission tests:**

```python
# Before (complex hospital + role tests)
def test_doctor_can_access_hospital_patients(self):
    doctor = create_user(profession='doctor', hospitals=[self.hospital1])
    patient = create_patient(current_hospital=self.hospital1)
    self.assertTrue(can_access_patient(doctor, patient))

def test_doctor_cannot_access_other_hospital_patients(self):
    doctor = create_user(profession='doctor', hospitals=[self.hospital1])
    patient = create_patient(current_hospital=self.hospital2)
    self.assertFalse(can_access_patient(doctor, patient))

# After (simple role tests)
def test_doctor_can_access_all_patients(self):
    doctor = create_user(profession='doctor')
    patient = create_patient()
    self.assertTrue(can_access_patient(doctor, patient))

def test_all_roles_can_access_patients(self):
    """All roles can access all patients"""
    student = create_user(profession='student')
    nurse = create_user(profession='nurse')
    inpatient = create_patient(status='inpatient')
    outpatient = create_patient(status='outpatient')
    
    self.assertTrue(can_access_patient(student, inpatient))
    self.assertTrue(can_access_patient(student, outpatient))
    self.assertTrue(can_access_patient(nurse, inpatient))
    self.assertTrue(can_access_patient(nurse, outpatient))
    self.assertFalse(can_access_patient(student, inpatient))
```

### 3. Update Patient Model Tests

**Simplify patient tests (`apps/patients/tests/test_models.py`):**

**Remove hospital validation tests:**

- [ ] Remove `test_inpatient_requires_hospital`
- [ ] Remove `test_outpatient_no_hospital_required`
- [ ] Remove `test_hospital_assignment_validation`

**Update patient creation tests:**

```python
# Before (hospital-aware tests)
def test_patient_creation_with_hospital(self):
    patient = Patient.objects.create(
        first_name="John",
        last_name="Doe",
        status="inpatient",
        current_hospital=self.hospital
    )
    self.assertEqual(patient.current_hospital, self.hospital)

# After (simple patient creation)
def test_patient_creation(self):
    patient = Patient.objects.create(
        first_name="John",
        last_name="Doe",
        status="inpatient"
    )
    self.assertEqual(patient.status, "inpatient")
```

### 4. Update Patient View Tests

**Simplify view tests (`apps/patients/tests/test_views.py`):**

**Remove hospital context tests:**

- [ ] Remove hospital filtering tests
- [ ] Remove hospital selection tests
- [ ] Remove cross-hospital access tests

**Update patient view tests:**

```python
# Before (hospital context required)
def test_patient_list_requires_hospital_context(self):
    user = create_user(hospitals=[self.hospital])
    self.client.force_login(user)
    # Set hospital context
    session = self.client.session
    session['current_hospital_id'] = self.hospital.id
    session.save()
    
    response = self.client.get('/patients/')
    self.assertEqual(response.status_code, 200)

# After (simple role-based access)
def test_patient_list_access(self):
    user = create_user(profession='doctor')
    self.client.force_login(user)
    
    response = self.client.get('/patients/')
    self.assertEqual(response.status_code, 200)
```

### 5. Update Form Tests

**Simplify form tests (`apps/patients/tests/test_forms.py`):**

**Remove hospital field tests:**

- [ ] Remove hospital field validation tests
- [ ] Remove hospital selection tests
- [ ] Remove PatientHospitalRecord form tests

**Update patient form tests:**

```python
# Before (complex hospital validation)
def test_patient_form_hospital_required_for_inpatient(self):
    form_data = {
        'first_name': 'John',
        'last_name': 'Doe',
        'status': 'inpatient',
        # No current_hospital - should fail
    }
    form = PatientCreateForm(data=form_data)
    self.assertFalse(form.is_valid())
    self.assertIn('current_hospital', form.errors)

# After (simple form validation)
def test_patient_form_valid_data(self):
    form_data = {
        'first_name': 'John',
        'last_name': 'Doe',
        'status': 'inpatient'
    }
    form = PatientCreateForm(data=form_data)
    self.assertTrue(form.is_valid())
```

### 6. Update Event Tests

**Simplify event tests (`apps/events/tests/`, `apps/dailynotes/tests/`):**

**Remove hospital context from event tests:**

- [ ] Remove hospital filtering from event tests
- [ ] Remove hospital context from event creation tests
- [ ] Simplify event permission tests

### 7. Update Test Factories

**Simplify factory_boy factories:**

**Update UserFactory (`apps/accounts/tests/factories.py`):**

```python
# Before (hospital assignments)
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    profession = 'doctor'
    
    @factory.post_generation
    def hospitals(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for hospital in extracted:
                self.hospitals.add(hospital)

# After (no hospital assignments)
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    profession = 'doctor'
```

**Update PatientFactory (`apps/patients/tests/factories.py`):**

```python
# Before (hospital assignments)
class PatientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Patient
    
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    status = 'outpatient'
    current_hospital = factory.SubFactory(HospitalFactory)

# After (no hospital assignments)
class PatientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Patient
    
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    status = 'outpatient'
```

### 8. Remove Hospital-Related Fixtures

**Clean up test fixtures:**

- [ ] Remove hospital JSON fixtures
- [ ] Remove PatientHospitalRecord fixtures
- [ ] Update patient fixtures to remove hospital references

### 9. Update Integration Tests

**Simplify integration tests:**

- [ ] Remove hospital context from integration tests
- [ ] Update user workflow tests to remove hospital selection
- [ ] Simplify patient management workflow tests

### 10. Performance Tests

**Update performance tests:**

- [ ] Remove hospital-related performance tests
- [ ] Update query performance tests (should be faster)
- [ ] Test simplified permission checking performance

### 11. Add New Tests for Simplified System

**Add tests for simplified permission system:**

```python
class SimplifiedPermissionTests(TestCase):
    def test_doctor_access_all_patients(self):
        """Doctors can access all patients regardless of status"""
        doctor = UserFactory(profession='doctor')
        inpatient = PatientFactory(status='inpatient')
        outpatient = PatientFactory(status='outpatient')
        
        self.assertTrue(can_access_patient(doctor, inpatient))
        self.assertTrue(can_access_patient(doctor, outpatient))
    
    def test_all_roles_patient_access(self):
        """All roles can access all patients"""
        student = UserFactory(profession='student')
        nurse = UserFactory(profession='nurse')
        inpatient = PatientFactory(status='inpatient')
        outpatient = PatientFactory(status='outpatient')
        
        self.assertTrue(can_access_patient(student, inpatient))
        self.assertTrue(can_access_patient(student, outpatient))
        self.assertTrue(can_access_patient(nurse, inpatient))
        self.assertTrue(can_access_patient(nurse, outpatient))
    
    def test_role_based_discharge_permissions(self):
        """Only doctors/residents can discharge patients"""
        doctor = UserFactory(profession='doctor')
        resident = UserFactory(profession='resident')
        nurse = UserFactory(profession='nurse')
        student = UserFactory(profession='student')
        patient = PatientFactory(status='inpatient')
        
        self.assertTrue(can_change_patient_status(doctor, patient, 'discharged'))
        self.assertTrue(can_change_patient_status(resident, patient, 'discharged'))
        self.assertFalse(can_change_patient_status(nurse, patient, 'discharged'))
        self.assertFalse(can_change_patient_status(student, patient, 'discharged'))
    
    def test_role_based_personal_data_permissions(self):
        """Only doctors/residents can edit patient personal data"""
        doctor = UserFactory(profession='doctor')
        resident = UserFactory(profession='resident')
        nurse = UserFactory(profession='nurse')
        student = UserFactory(profession='student')
        patient = PatientFactory()
        
        self.assertTrue(can_change_patient_personal_data(doctor, patient))
        self.assertTrue(can_change_patient_personal_data(resident, patient))
        self.assertFalse(can_change_patient_personal_data(nurse, patient))
        self.assertFalse(can_change_patient_personal_data(student, patient))
```

## Test Command Updates

**Update test runner commands:**

```bash
# Remove hospital-specific test commands
# Update test configurations to exclude removed apps

# Test specific areas
uv run python manage.py test apps.core.tests.test_permissions
uv run python manage.py test apps.patients.tests
uv run python manage.py test apps.events.tests
uv run python manage.py test apps.accounts.tests
```

## Coverage Analysis

**Update test coverage:**

- [ ] Remove hospital app from coverage reports
- [ ] Ensure core functionality maintains coverage
- [ ] Test coverage for simplified permission system
- [ ] Verify no untested code paths in refactored areas

## Mock and Patch Updates

**Update test mocks:**

- [ ] Remove hospital context mocks
- [ ] Remove hospital membership mocks
- [ ] Simplify permission checking mocks

## Database Test Optimizations

**Optimize test database:**

- [ ] Remove hospital-related test database setup
- [ ] Simplify test data creation
- [ ] Update database transaction tests

## Files to Modify

### Test Files to Update

- [ ] `apps/core/tests/test_permissions.py` - Major simplification
- [ ] `apps/patients/tests/test_models.py` - Remove hospital tests
- [ ] `apps/patients/tests/test_views.py` - Remove hospital context
- [ ] `apps/patients/tests/test_forms.py` - Remove hospital fields
- [ ] `apps/accounts/tests/test_models.py` - Remove hospital relationships
- [ ] `apps/events/tests/` - Remove hospital context
- [ ] `apps/dailynotes/tests/` - Remove hospital context

### Test Factories to Update

- [ ] `apps/accounts/tests/factories.py` - Remove hospital assignments
- [ ] `apps/patients/tests/factories.py` - Remove hospital fields

### Files to Delete

- [ ] `apps/hospitals/tests/` (entire directory)
- [ ] Hospital-specific test fixtures
- [ ] Hospital integration test files

## Validation Checklist

**Run comprehensive tests:**

```bash
# Run all tests
uv run python manage.py test

# Run tests with coverage
uv run pytest --cov=apps --cov-report=html

# Run specific test categories
uv run python manage.py test apps.core.tests.test_permissions
uv run python manage.py test apps.patients.tests
uv run python manage.py test apps.accounts.tests
```

Before proceeding to Phase 8:

- [ ] All existing tests pass
- [ ] No hospital-related test failures
- [ ] Permission tests cover simplified system
- [ ] Core functionality tests work
- [ ] No import errors in test files
- [ ] Test coverage maintained for critical paths

## Performance Testing

**Expected test performance improvements:**

- Faster test execution (simpler setup)
- Faster database operations in tests
- Reduced test complexity
- Fewer test scenarios to maintain

## Test Documentation

**Update test documentation:**

- [ ] Update test README files
- [ ] Remove hospital testing documentation
- [ ] Update testing guidelines
- [ ] Document simplified test patterns
