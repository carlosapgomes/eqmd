# Generated manually for user lifecycle management
# Population of essential lifecycle data for existing users

from django.db import migrations
from django.utils import timezone
from datetime import timedelta

def populate_essential_lifecycle_data(apps, schema_editor):
    """Set initial lifecycle data for existing users"""
    EqmdCustomUser = apps.get_model('accounts', 'EqmdCustomUser')

    # Set all existing users as active with basic activity
    EqmdCustomUser.objects.update(
        account_status='active',
        last_meaningful_activity=timezone.now() - timedelta(days=30),
    )

    # Set role-specific defaults
    residents = EqmdCustomUser.objects.filter(profession_type=1)  # RESIDENT
    students = EqmdCustomUser.objects.filter(profession_type=4)   # STUDENT

    # Residents: Default 1-year expiration
    for resident in residents:
        if not resident.access_expires_at:
            resident.access_expires_at = timezone.now() + timedelta(days=365)
            resident.expiration_reason = 'end_of_internship'
            resident.save()

    # Students: Default 6-month expiration
    for student in students:
        if not student.access_expires_at:
            student.access_expires_at = timezone.now() + timedelta(days=180)
            student.expiration_reason = 'end_of_rotation'
            student.save()

def reverse_populate_lifecycle_data(apps, schema_editor):
    """Reverse migration - clear lifecycle data"""
    EqmdCustomUser = apps.get_model('accounts', 'EqmdCustomUser')
    EqmdCustomUser.objects.update(
        access_expires_at=None,
        expiration_reason='',
        account_status='active',
    )

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_add_essential_lifecycle_fields'),
    ]

    operations = [
        migrations.RunPython(
            populate_essential_lifecycle_data,
            reverse_populate_lifecycle_data,
        ),
    ]