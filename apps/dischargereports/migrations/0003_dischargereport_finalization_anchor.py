"""Add the finalization anchor that opens the 24h correction window (S3).

Finalizing a draft records who finalized it and when; the correction window is
anchored at that instant (design D6). Legacy finals are backfilled with
``created_at``/``created_by`` so their verdicts stay row-for-row identical to
the creation-anchored rule; drafts stay null.
"""

from django.conf import settings
from django.db import migrations, models


def backfill_finalization_anchor(apps, schema_editor):
    """Anchor legacy finals at their creation timestamp and author.

    The report is multi-table: ``is_draft``/``created_at``/``created_by`` live
    on the ``Event`` parent row while the anchor columns are new on the child,
    so the join is expressed directly (an ORM ``update()`` with ``F()`` cannot
    reference joined columns). Drafts stay null.
    """
    DischargeReport = apps.get_model("dischargereports", "DischargeReport")
    Event = apps.get_model("events", "Event")
    report_table = schema_editor.quote_name(DischargeReport._meta.db_table)
    event_table = schema_editor.quote_name(Event._meta.db_table)
    schema_editor.execute(
        f"UPDATE {report_table} SET "
        "finalized_at = event.created_at, "
        "finalized_by_id = event.created_by_id "
        f"FROM {event_table} AS event "
        f"WHERE {report_table}.event_ptr_id = event.id "
        "AND event.is_draft = false"
    )


def clear_finalization_anchor(apps, schema_editor):
    """Reverse step: the anchor is derived data, so dropping it is safe."""
    DischargeReport = apps.get_model("dischargereports", "DischargeReport")
    schema_editor.execute(
        f"UPDATE {schema_editor.quote_name(DischargeReport._meta.db_table)} "
        "SET finalized_at = NULL, finalized_by_id = NULL"
    )


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012 — declarative migration attribute.
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        (
            "dischargereports",
            "0002_remove_dischargereport_dischargere_is_draf_26e620_idx_and_more",
        ),
    ]

    operations = [  # noqa: RUF012 — declarative migration attribute.
        migrations.AddField(
            model_name="dischargereport",
            name="finalized_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Data/hora da finalização que ancora a janela de correção",
                null=True,
                verbose_name="Finalizado em",
            ),
        ),
        migrations.AddField(
            model_name="dischargereport",
            name="finalized_by",
            field=models.ForeignKey(
                blank=True,
                help_text="Usuário que finalizou o relatório",
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="finalized_discharge_reports",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Finalizado por",
            ),
        ),
        migrations.RunPython(
            backfill_finalization_anchor,
            clear_finalization_anchor,
        ),
    ]
