# Generated migration to enable PostgreSQL unaccent extension

from django.db import migrations
from django.contrib.postgres.operations import UnaccentExtension


class Migration(migrations.Migration):
    dependencies = [
        ('drugtemplates', '0005_increase_field_lengths'),
    ]

    operations = [
        UnaccentExtension(),
    ]
