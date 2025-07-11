# AGENTS.md

Essential guidelines for coding agents working on EquipeMed Django project.

## Commands

```bash
# Testing
pytest                                      # All tests with coverage
pytest --no-cov                           # Without coverage  
python manage.py test apps.patients.tests  # Single app tests (recommended for patients/events/dailynotes/sample_content)
python manage.py test apps.core.tests.test_permissions  # Single test module

# Development
python manage.py runserver                  # Dev server
python manage.py migrate                   # Apply migrations
npm run build                              # Build frontend assets
uv install                                 # Install Python deps
```

## Code Style

- **Imports**: Standard library, Django, third-party, local apps (separated by blank lines)
- **Types**: Use type hints for function parameters and returns (`from typing import Any, Optional`)
- **Naming**: snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- **Docstrings**: Use triple quotes for module/class/function documentation
- **Models**: Include verbose_name for fields, use UUID primary keys, add created_at/updated_at tracking
- **Permissions**: Always check user permissions before operations using `apps.core.permissions.utils`
- **Error handling**: Use Django's ValidationError for model validation, handle exceptions gracefully