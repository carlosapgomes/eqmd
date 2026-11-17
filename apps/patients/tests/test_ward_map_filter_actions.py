"""PMFA-S1: distinct map action scopes and inherited permissions."""

from urllib.parse import parse_qs, urlsplit

from django.urls import reverse

from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.tests.ward_map_filter_fixtures import MapFilterFixture


class MapFilterActionTests(MapFilterFixture):
    def test_clear_all_drops_every_parameter_and_never_changes_saved_settings(
        self,
    ) -> None:
        before = self.snapshot()
        response = self.response(
            q="Ana",
            ward=str(self.wards[0].pk),
            tags=str(self.y.pk),
            tag_mode="all",
            show_empty_wards="true",
        )
        href = self.action_href(response, "Limpar todos os filtros")
        self.assertEqual(
            parse_qs(urlsplit(href).query),
            {"tag_filter": ["manual"], "tag_mode": ["any"]},
        )
        for ajax in (False, True):
            cleared = self.client.get(
                href, HTTP_X_REQUESTED_WITH="XMLHttpRequest" if ajax else ""
            )
            self.assertEqual(cleared.context["total_patients"], 5)
            self.assertEqual(cleared.context["total_wards"], 2)
            self.assertTrue(cleared.context["tag_selection"].is_manual)
            self.assertFalse(cleared.context["tag_selection"].has_predicate)
            self.assertEqual(cleared.context["tag_selection"].mode, "any")
            self.assertFalse(cleared.context["show_empty_wards"])
        self.assertEqual(self.client.get(href).context["total_patients"], 5)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.response().context["tag_selection"].tag_ids, (self.x.pk,))

    def test_restore_preserves_applied_search_ward_and_empty_visibility(self) -> None:
        before = self.snapshot()
        response = self.response(
            q="Ana",
            ward=str(self.wards[0].pk),
            tags=str(self.y.pk),
            show_empty_wards="true",
            page="7",
        )
        href = self.action_href(response, "Usar padrão de tags da especialidade")
        self.assertEqual(
            parse_qs(urlsplit(href).query),
            {
                "q": ["Ana"],
                "ward": [str(self.wards[0].pk)],
                "show_empty_wards": ["true"],
            },
        )
        restored = self.client.get(href)
        self.assertEqual(restored.context["tag_selection"].tag_ids, (self.x.pk,))
        self.assertEqual(restored.context["tag_selection"].mode, "all")
        self.assertEqual(restored.context["total_patients"], 2)
        self.assertTrue(restored.context["show_empty_wards"])
        self.assertEqual(self.snapshot(), before)

    def test_manual_and_filtered_empty_pages_have_one_bar_and_no_applied_removal(
        self,
    ) -> None:
        for q in ("Ana", "sem-correspondencia"):
            response = self.response(
                q=q, ward=str(self.wards[0].pk), tags=str(self.y.pk)
            )
            self.action_href(response, "Limpar todos os filtros")
            self.action_href(response, "Usar padrão de tags da especialidade")
            self.assertContains(response, "> Aplicar filtros", count=1)
            self.assertNotContains(response, "Remover filtro de tags")
            self.assertNotContains(response, "Restaurar padrão da especialidade")
            self.assertNotContains(response, 'aria-label="Limpar filtros"')
            self.assertNotContains(response, "dos filtros aplicados")
            self.assertNotContains(response, "Limpar seleção")
            ajax = self.response(ajax=True, q=q, tags=str(self.y.pk))
            self.assertNotContains(ajax, "Remover filtro de tags")
            self.assertNotContains(ajax, "Restaurar padrão da especialidade")

    def test_initial_entry_hides_restore_and_identifies_saved_default(self) -> None:
        response = self.response()
        self.assertNotContains(response, "Usar padrão de tags da especialidade")
        self.assertContains(response, "Padrão salvo da especialidade aplicado")
        self.assertEqual(response.context["total_patients"], 2)
        self.assertContains(
            self.response(tags=str(self.y.pk)), "Filtros personalizados em uso"
        )

    def test_restore_saved_empty_without_principal_is_configured(self) -> None:
        self.preference.tags.clear()
        self.assertContains(self.response(), "Padrão salvo sem filtro de tags aplicado")
        response = self.response(tag_filter="manual")
        href = self.action_href(response, "Usar padrão de tags da especialidade")
        restored = self.client.get(href)
        self.assertFalse(restored.context["tag_selection"].has_predicate)
        self.assertEqual(restored.context["total_patients"], 5)

    def test_missing_default_and_specialty_hide_restore(self) -> None:
        self.preference.delete()
        self.assertNotContains(
            self.response(tags=str(self.y.pk)), "Usar padrão de tags da especialidade"
        )
        self.assertContains(self.response(), "Sem padrão de tags aplicado")
        self.specialty.principal_tag = self.x
        self.specialty.save(update_fields=["principal_tag"])
        self.assertContains(self.response(), "Padrão inicial da especialidade aplicado")
        self.action_href(
            self.response(tags=str(self.y.pk)), "Usar padrão de tags da especialidade"
        )
        profile = self.viewer.profile
        profile.current_specialty = None
        profile.save(update_fields=["current_specialty"])
        self.assertNotContains(
            self.response(tags=str(self.y.pk)), "Usar padrão de tags da especialidade"
        )

    def test_native_apply_is_an_explicit_manual_submitter(self) -> None:
        self.assertRegex(
            self.response().content.decode(),
            r'<button[^>]*type="submit"[^>]*name="tag_filter"[^>]*value="manual"',
        )
        response = self.client.get(
            reverse("patients:patient_map")
            + "?tag_filter=&tag_mode=all&tag_filter=manual"
        )
        self.assertTrue(response.context["tag_selection"].is_manual)
        self.assertFalse(response.context["tag_selection"].has_predicate)
        self.assertEqual(response.context["total_patients"], 5)

    def test_legacy_scoped_urls_keep_applied_non_tag_fields(self) -> None:
        response = self.response(
            q="Ana",
            ward=str(self.wards[0].pk),
            tag=str(self.y.pk),
            show_empty_wards="true",
        )
        href = (
            reverse("patients:patient_map")
            + "?"
            + response.context["clear_tags_querystring"]
        )
        before = self.snapshot()
        cleared = self.client.get(href)
        self.assertEqual(cleared.context["search_query"], "Ana")
        self.assertEqual(cleared.context["ward_filter"], str(self.wards[0].pk))
        self.assertTrue(cleared.context["show_empty_wards"])
        self.assertEqual(cleared.context["total_patients"], 3)
        self.assertEqual(self.snapshot(), before)

    def test_permissions_and_inaccessible_tags_are_not_weakened(self) -> None:
        invalid = self.response(tags=str(self.hidden.pk))
        self.assertTrue(invalid.context["tag_filter_error"])
        self.assertEqual(invalid.context["total_patients"], 0)
        self.assertNotContains(invalid, self.hidden.name)
        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("patients:patient_map")).status_code, 302
        )
        user = create_navigation_user(
            username="pmfa-denied", email="pmfa-denied@example.com"
        )
        self.client.force_login(user)
        self.assertEqual(
            self.client.get(reverse("patients:patient_map")).status_code, 403
        )
