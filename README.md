# EquipeMed

EquipeMed is a Django 5-based medical team collaboration platform for tracking patients across multiple hospitals.

## Patients App

The Patients app provides comprehensive patient management functionality:

- Patient registration and tracking
- Hospital record management
- Patient status tracking (inpatient, outpatient, deceased)
- Tagging system for patient categorization
- Dashboard integration with patient statistics

## UV

```bash
uv venv create
source .venv/bin/activate
uv add django
uv add --group dev django-debug-toolbar
uv add --group prod gunicorn
uv sync
uv run django-admin startproject config .
uv run python manage.py migrate
uv run python manage.py setup_permissions
uv run python manage.py setup_site
uv run python manage.py createsuperuser
uv run python manage.py runserver 8778
```
