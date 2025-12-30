# Testing Guide for EquipeMed

This document provides comprehensive information about the testing framework and strategy implemented for the EquipeMed Django project.

## Testing Framework

We use **pytest** as our primary testing framework with Django integration, along with several supporting libraries:

### Dependencies

- **pytest**: Modern testing framework
- **pytest-django**: Django integration for pytest
- **pytest-cov**: Coverage reporting
- **factory-boy**: Test data generation
- **faker**: Realistic fake data generation

### Installation

All testing dependencies are managed through `uv`. To install:

```bash
uv add --dev pytest pytest-django pytest-cov factory-boy faker
```

## Testing Strategy

### Testing Pyramid Structure

```
    🔺 E2E Tests (Future - Selenium)
   🔺🔺 Integration Tests (Django TestCase)
  🔺🔺🔺 Unit Tests (pytest/Django)
```

### Testing Levels

- **Unit Tests (70% of tests)**: Models, views, forms, utilities
- **Integration Tests (20% of tests)**: URL routing, template rendering, database interactions  
- **End-to-End Tests (10% of tests - Future)**: Complete user workflows with browser testing

### Coverage Goals

- **Overall**: 80%+ coverage
- **Critical Business Logic**: 100% coverage
- **Models**: 90%+ coverage
- **Views**: 85%+ coverage
- **Forms**: 90%+ coverage

## Configuration Files

### pytest.ini

```ini
[tool:pytest]
DJANGO_SETTINGS_MODULE = config.test_settings
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*
addopts = 
    --cov=apps
    --cov-report=html
    --cov-report=term-missing
    --reuse-db
    --nomigrations
    --tb=short
    -v
```

### .coveragerc

```ini
[run]
source = apps
omit = 
    */migrations/*
    */venv/*
    */tests/*
    */__pycache__/*
    manage.py
    config/settings.py
    config/wsgi.py
    config/asgi.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    def __str__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod

[html]
directory = htmlcov
```

### Test Settings (config/test_settings.py)

Optimized settings for fast test execution:

- In-memory SQLite database
- Disabled migrations
- Simple password hashing
- Console email backend
- Disabled logging

## Test Structure

### Directory Organization

```
apps/
├── accounts/
│   └── tests/
│       ├── __init__.py
│       ├── factories.py      # Test data factories
│       ├── test_models.py     # Model tests
│       ├── test_forms.py      # Form tests
│       └── test_views.py      # View tests
└── core/
    └── tests/
        ├── __init__.py
        ├── test_views.py      # View tests
        ├── test_urls.py       # URL pattern tests
        └── test_templates.py  # Template tests
```

## Test Categories

### 1. Model Tests (`test_models.py`)

Tests for Django models including:

- Model creation and validation
- Model methods and properties
- Model relationships
- Signal handling
- String representations

**Example:**

```python
def test_user_creation_with_factory(self):
    """Test that a user can be created using the factory."""
    user = UserFactory()
    self.assertIsInstance(user, User)
    self.assertTrue(user.is_active)
    self.assertIsNotNone(user.username)
```

### 2. Form Tests (`test_forms.py`)

Tests for Django forms including:

- Form validation
- Form saving
- Error handling
- Field validation

**Example:**

```python
def test_form_valid_data(self):
    """Test form with valid data."""
    form_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password1': 'complexpassword123',
        'password2': 'complexpassword123',
    }
    form = EqmdCustomUserCreationForm(data=form_data)
    self.assertTrue(form.is_valid())
```

### 3. View Tests (`test_views.py`)

Tests for Django views including:

- HTTP response codes
- Template usage
- Context data
- Authentication requirements
- Permissions

**Example:**

```python
def test_landing_page_accessible(self):
    """Test that landing page is accessible without authentication."""
    url = reverse('core:landing_page')
    response = self.client.get(url)
    self.assertEqual(response.status_code, 200)
```

### 4. URL Tests (`test_urls.py`)

Tests for URL patterns including:

- URL resolution
- Reverse URL lookup
- URL accessibility
- Parameter handling

### 5. Template Tests (`test_templates.py`)

Tests for Django templates including:

- Template existence
- Template inheritance
- Content verification
- Responsive elements

## Test Factories

We use Factory Boy to create test data. Factories are defined in `factories.py` files:

### User Factory

```python
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    profession_type = factory.Faker('random_int', min=0, max=4)
    is_active = True
```

### Specialized Factories

- `DoctorFactory`: Creates users with medical doctor profession
- `NurseFactory`: Creates users with nurse profession
- `StudentFactory`: Creates users with student profession
- `UserProfileFactory`: Creates user profiles (handles signal conflicts)

## Running Tests

### Using uv (Recommended)

```bash
# Run all tests
uv run python manage.py test --settings=config.test_settings

# Run specific app tests
uv run python manage.py test apps.accounts --settings=config.test_settings

# Run specific test file
uv run python manage.py test apps.accounts.tests.test_models --settings=config.test_settings

# Run with coverage
uv run pytest --cov=apps --cov-report=html
```

### Using pytest directly

```bash
# Run all tests with coverage
uv run pytest

# Run specific tests
uv run pytest apps/accounts/tests/test_models.py

# Run with verbose output
uv run pytest -v

# Generate coverage report
uv run pytest --cov=apps --cov-report=html
```

## Coverage Reporting

Coverage reports are generated in multiple formats:

1. **Terminal output**: Shows missing lines during test run
2. **HTML report**: Detailed coverage report in `htmlcov/` directory

To view HTML coverage report:

```bash
# Generate report
uv run pytest --cov=apps --cov-report=html

# Open in browser
open htmlcov/index.html
```

## Test Data Management

### Database Handling

- Tests use in-memory SQLite for speed
- Database is recreated for each test run
- `--reuse-db` flag can speed up development

### Fixtures and Factories

- Use factories instead of fixtures for better maintainability
- Factories generate realistic test data using Faker
- Avoid hard-coded test data when possible

## Best Practices

### Writing Tests

1. **Descriptive test names**: Use clear, descriptive test method names
2. **One assertion per test**: Focus each test on a single behavior
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Use factories**: Generate test data with factories, not fixtures
5. **Test edge cases**: Include boundary conditions and error cases

### Test Organization

1. **Group related tests**: Use test classes to group related functionality
2. **Separate concerns**: Different test files for models, views, forms
3. **Clear documentation**: Add docstrings to test methods
4. **Consistent naming**: Follow naming conventions

### Performance

1. **Use test settings**: Optimized settings for faster test execution
2. **Minimize database hits**: Use `select_related` and `prefetch_related`
3. **Mock external services**: Don't make real API calls in tests
4. **Parallel execution**: Consider using `pytest-xdist` for parallel tests

## Continuous Integration

Tests should be run automatically in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    uv run python manage.py test --settings=config.test_settings
    uv run pytest --cov=apps --cov-report=xml
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure `DJANGO_SETTINGS_MODULE` is set correctly
2. **Database errors**: Check test database configuration
3. **Factory conflicts**: Use `django_get_or_create` for models with signals
4. **Template not found**: Ensure templates exist for view tests

### Debug Tips

1. Use `--pdb` flag to drop into debugger on failures
2. Use `--lf` to run only last failed tests
3. Use `-k` to run tests matching a pattern
4. Check test database state with `--keepdb`

## Current Test Status

### ✅ Fully Working (97 tests)

- **Accounts Models**: 20/20 tests passing
- **Core Views**: 27/27 tests passing  
- **Core URLs**: 23/23 tests passing
- **Core Templates**: 27/27 tests passing

### ⚠️ Partially Working

- **Accounts Forms**: 16/18 tests passing (minor validation issues)
- **Accounts Views**: 10/25 tests passing (missing templates and auth issues)

### Test Implementation Summary

**Total**: 123 tests implemented, 107 passing (87% success rate)

#### Key Features Tested

**Model Testing**:

- User creation with different profession types
- Profile automatic creation via Django signals
- Model validation and constraints
- Relationship testing (OneToOne User-Profile)

**Form Testing**:

- Valid and invalid data scenarios
- Password strength validation
- Email format validation
- Username uniqueness testing

**View Testing**:

- Authentication requirements
- Template rendering
- Context data validation
- Permission checks

**Template Testing**:

- Template inheritance
- Content verification
- Bootstrap integration
- Responsive elements

### Next Testing Priorities

1. **Complete Accounts Views**: Fix missing templates and authentication flows
2. **Accounts Forms**: Resolve remaining validation issues
3. **Patient Management**: Implement patient app testing
4. **Events System**: Add comprehensive event testing
5. **MediaFiles**: Security and file handling tests

## Next Steps

1. Complete Accounts app testing (views and forms)
2. Implement patient management tests
3. Add events system testing
4. Implement integration tests
5. Set up automated testing in CI/CD
6. Add performance and security testing

## Resources

- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [pytest Documentation](https://docs.pytest.org/)
- [Factory Boy Documentation](https://factoryboy.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
