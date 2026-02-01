# Update immutable_unaccent to use schema-qualified dictionary

from django.db import migrations


IMMUTABLE_UNACCENT_SQL = (
    "CREATE OR REPLACE FUNCTION immutable_unaccent(text) "
    "RETURNS text AS $$ "
    "SELECT public.unaccent('public.unaccent', $1) "
    "$$ LANGUAGE sql IMMUTABLE"
)


def update_immutable_unaccent(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(IMMUTABLE_UNACCENT_SQL)


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):
    dependencies = [
        ("drugtemplates", "0007_enable_pg_trgm_and_add_name_trgm_index"),
    ]

    operations = [
        migrations.RunPython(update_immutable_unaccent, noop_reverse),
    ]
