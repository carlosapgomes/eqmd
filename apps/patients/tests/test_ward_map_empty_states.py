"""PMFA-S1: full/fragment totals, source labels and truthful empty wards."""

from apps.core.models import WardMappingCache
from apps.patients.models import AllowedTag
from apps.patients.tests.ward_map_filter_fixtures import MapFilterFixture

NO_MATCH = "Nenhum paciente corresponde aos filtros atuais nesta ala."
NO_INPATIENT = "Nenhum paciente internado nesta ala."
GLOBAL_ZERO = "As alas continuam visíveis"


class MapEmptyStateTests(MapFilterFixture):
    def test_origin_and_display_options_alone_do_not_label_totals_filtered(
        self,
    ) -> None:
        for ajax in (False, True):
            for params in (
                {"tag_filter": "manual"},
                {"tag_filter": "manual", "tag_mode": "all"},
                {"tag_filter": "manual", "show_empty_wards": "true"},
                {"tag_filter": "manual", "q": "   "},
            ):
                response = self.response(ajax=ajax, **params)
                self.assertNotContains(response, "resultado filtrado")
                self.assertEqual(response.context["total_patients"], 5)
        self.assertContains(
            self.response(tag_filter="manual"), "Sem filtro de tags (personalizado)"
        )

    def test_real_applied_predicates_label_totals_filtered(self) -> None:
        for ajax in (False, True):
            for params in (
                {},
                {"tag_filter": "manual", "q": "Ana"},
                {"tag_filter": "manual", "ward": str(self.wards[0].pk)},
                {"tags": str(self.y.pk)},
            ):
                self.assertContains(
                    self.response(ajax=ajax, **params), "resultado filtrado"
                )

    def test_per_ward_text_distinguishes_patient_predicates_from_ward_selection(
        self,
    ) -> None:
        for ajax in (False, True):
            filtered = self.response(
                ajax=ajax, q="sem-correspondencia", show_empty_wards="true"
            )
            self.assertContains(filtered, NO_MATCH, count=3)
            self.assertNotContains(filtered, NO_INPATIENT)
            genuine = self.response(
                ajax=ajax,
                tag_filter="manual",
                ward=str(self.wards[2].pk),
                show_empty_wards="true",
            )
            self.assertContains(genuine, NO_INPATIENT, count=1)
            self.assertNotContains(genuine, NO_MATCH)
            self.assertEqual(genuine.context["total_wards"], 1)

    def test_retained_zero_wards_have_one_visible_notice_and_unchanged_cache(
        self,
    ) -> None:
        before = self.snapshot()
        for ajax in (False, True):
            response = self.response(
                ajax=ajax, q="sem-correspondencia", show_empty_wards="true"
            )
            self.assertEqual(response.context["total_patients"], 0)
            self.assertEqual(response.context["total_wards"], 3)
            self.assertContains(response, GLOBAL_ZERO, count=1)
            body = response.content.decode()
            self.assertLess(body.index(GLOBAL_ZERO), body.index('class="ward-tree"'))
            self.assertNotContains(response, "Remover filtro de tags")
        self.assertEqual(self.snapshot(), before)

    def test_global_notice_is_absent_for_matches_or_unfiltered_empty_wards(
        self,
    ) -> None:
        for ajax in (False, True):
            self.assertNotContains(
                self.response(ajax=ajax, show_empty_wards="true"), GLOBAL_ZERO
            )
        WardMappingCache.objects.filter(cache_key="ward_mapping_full").update(
            ward_data={
                "ward_data": [
                    {
                        "ward": {
                            "id": str(self.wards[2].pk),
                            "name": "PMFA Ala C",
                            "abbreviation": "PC",
                        },
                        "patients": [],
                        "patient_count": 0,
                    }
                ]
            }
        )
        for ajax in (False, True):
            empty = self.response(
                ajax=ajax, tag_filter="manual", show_empty_wards="true"
            )
            self.assertContains(empty, NO_INPATIENT)
            self.assertNotContains(empty, GLOBAL_ZERO)

    def test_checkbox_helper_and_empty_recovery_have_no_extra_controls(self) -> None:
        self.assertContains(
            self.response(),
            "Inclui alas sem pacientes correspondentes aos filtros atuais.",
        )
        for ajax in (False, True):
            response = self.response(
                ajax=ajax, q="sem-correspondencia", tags=str(self.y.pk)
            )
            self.assertContains(response, "barra de ações dos filtros")
            self.assertNotContains(response, GLOBAL_ZERO)
            self.assertNotContains(response, "Remover filtro de tags")
            if ajax:
                self.assertNotContains(response, "data-map-filter-actions")

    def test_unavailable_defaults_and_invalid_or_updating_data_remain_distinct(
        self,
    ) -> None:
        self.preference.tags.add(self.y)
        AllowedTag.objects.filter(pk=self.y.pk).update(is_active=False)
        self.assertContains(self.response(), "aplicado parcialmente")
        AllowedTag.objects.filter(pk=self.x.pk).update(is_active=False)
        self.assertContains(self.response(), "Sem filtro de tags: padrão indisponível")
        for ajax in (False, True):
            invalid = self.response(
                ajax=ajax, tags="999999999", show_empty_wards="true"
            )
            self.assertTrue(invalid.context["tag_filter_error"])
            self.assertContains(invalid, "Filtro de tags inválido")
            self.assertNotContains(invalid, GLOBAL_ZERO)
        WardMappingCache.objects.filter(
            cache_key__in=["ward_mapping_full", "ward_filters"]
        ).delete()
        for ajax in (False, True):
            updating = self.response(ajax=ajax, q="Ana", show_empty_wards="true")
            self.assertTrue(updating.context["updating"])
            self.assertNotContains(updating, GLOBAL_ZERO)
