# Generated migration to enable PostgreSQL pg_trgm extension and add trigram index

from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension


IMMUTABLE_UNACCENT_SQL = (
    "CREATE OR REPLACE FUNCTION immutable_unaccent(text) "
    "RETURNS text AS $$ "
    "SELECT unaccent('unaccent', $1) "
    "$$ LANGUAGE sql IMMUTABLE"
)
DROP_IMMUTABLE_UNACCENT_SQL = "DROP FUNCTION IF EXISTS immutable_unaccent(text)"

INDEX_NAME = "drugtpl_name_trgm_idx"
INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS {name} "
    "ON drugtemplates_drugtemplate "
    "USING gin (immutable_unaccent(lower(name)) gin_trgm_ops)"
)
DROP_INDEX_SQL = "DROP INDEX IF EXISTS {name}"


def add_trigram_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(IMMUTABLE_UNACCENT_SQL)
    schema_editor.execute(INDEX_SQL.format(name=INDEX_NAME))


def remove_trigram_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(DROP_INDEX_SQL.format(name=INDEX_NAME))
    schema_editor.execute(DROP_IMMUTABLE_UNACCENT_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ("drugtemplates", "0006_enable_unaccent_extension"),
    ]

    operations = [
        TrigramExtension(),
        migrations.RunPython(add_trigram_index, remove_trigram_index),
    ]
