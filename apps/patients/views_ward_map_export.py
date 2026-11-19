"""The ward map's named XLSX export endpoint (design D1 and D5).

The endpoint inherits ``WardMapFilterActionsView`` and resolves its context
exactly once, so the exported rows are the rows the map page renders for the
same query string: same filters, same viewer projection, same permission
gates. An empty applied result is refused with one plain-text 409 (no file);
any other result is answered with one valid workbook attachment named
``mapa_pacientes_YYYYMMDD_HHMMSS.xlsx``. The view stays thin: the refusal
rule and the response assembly live here, the workbook itself is owned by
the WMX-S1 service.
"""

from __future__ import annotations

import io
from collections.abc import Mapping, Sequence
from typing import Any, cast

from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from apps.patients.services.ward_map_export import (
    build_ward_map_workbook,
    export_filename,
)
from apps.patients.views_ward_map_filters import WardMapFilterActionsView

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
REFUSAL_CONTENT_TYPE = "text/plain; charset=utf-8"
REFUSAL_STATUS = 409
REFUSAL_MESSAGE = (
    "Nenhum paciente no resultado da busca. Ajuste os filtros do mapa ou "
    "aguarde a atualização dos dados antes de exportar."
)


def empty_result_response() -> HttpResponse:
    """Answer the single refusal rule: 409, plain text, no file (design D1)."""
    return HttpResponse(
        REFUSAL_MESSAGE,
        status=REFUSAL_STATUS,
        content_type=REFUSAL_CONTENT_TYPE,
    )


def workbook_response(ward_data: Sequence[Mapping[str, Any]]) -> HttpResponse:
    """Serialize the resolved rows as one XLSX attachment (design D5)."""
    workbook = build_ward_map_workbook(ward_data, today=timezone.localdate())
    buffer = io.BytesIO()
    workbook.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = (
        f'attachment; filename="{export_filename(now=timezone.localtime())}"'
    )
    return response


class WardMapExportXlsxView(WardMapFilterActionsView):
    """Download the map's current search/filter result as one XLSX workbook."""

    def get(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        """Serve the already-resolved map result, refusing an empty one."""
        context = self.get_context_data(**kwargs)
        if cast(int, context["total_patients"]) == 0:
            return empty_result_response()
        return workbook_response(
            cast(Sequence[Mapping[str, Any]], context["ward_data"])
        )
