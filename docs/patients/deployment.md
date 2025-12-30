# Patients App Deployment Checklist

## Pre-Deployment Checks

- [ ] Run all tests and verify they pass:

  ```bash
  python manage.py test apps.patients
  ```

- [ ] Check for any pending migrations:

  ```bash
  python manage.py showmigrations patients
  ```

- [ ] Verify permissions and groups are correctly set up:

  ```bash
  python manage.py shell -c "from django.contrib.auth.models import Group; print(Group.objects.filter(name__contains='Patient').values('name', 'permissions__codename'))"
  ```

- [ ] Check for any deprecation warnings:

  ```bash
  python -Wd manage.py check patients
  ```

## Deployment Steps

- [ ] Apply any pending migrations:

  ```bash
  python manage.py migrate patients
  ```

- [ ] Collect static files:

  ```bash
  python manage.py collectstatic --noinput
  ```

- [ ] Update cache if using caching:

  ```bash
  python manage.py clear_cache
  ```

- [ ] Restart web server:

  ```bash
  sudo systemctl restart gunicorn
  sudo systemctl restart nginx
  ```

## Post-Deployment Verification

- [ ] Verify the patients app is accessible
- [ ] Test creating a new patient
- [ ] Test patient hospital record creation
- [ ] Verify dashboard widgets are displaying correctly
- [ ] Check permissions work correctly for different user roles
- [ ] Monitor error logs for any issues:

  ```bash
  tail -f /var/log/nginx/error.log
  tail -f /path/to/django/logs/error.log
  ```
