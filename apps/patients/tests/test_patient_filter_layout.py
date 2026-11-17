"""DOM contracts for the operator-approved list/map visual alignment."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

from django.urls import reverse

from apps.patients.tests.ward_map_filter_fixtures import MapFilterFixture


@dataclass
class Element:
    tag: str
    attrs: dict[str, str | None]
    parents: tuple[Element, ...]
    position: int

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())


class LayoutDocument(HTMLParser):
    void_tags = frozenset(
        (
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        )
    )

    def __init__(self, html: str) -> None:
        super().__init__()
        self.elements: list[Element] = []
        self.stack: list[Element] = []
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = Element(tag, dict(attrs), tuple(self.stack), len(self.elements))
        self.elements.append(element)
        if tag not in self.void_tags:
            self.stack.append(element)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def one(self, attribute: str, value: str | None = None) -> Element:
        found = [
            element
            for element in self.elements
            if attribute in element.attrs
            and (value is None or element.attrs[attribute] == value)
        ]
        assert len(found) == 1, f"Expected one {attribute}={value}, got {len(found)}"
        return found[0]


class PatientFilterLayoutTests(MapFilterFixture):
    def layout(self, route: str = "patients:patient_map") -> LayoutDocument:
        response = self.client.get(reverse(route), {"tags": str(self.y.pk)})
        self.assertEqual(response.status_code, 200)
        return LayoutDocument(response.content.decode())

    def test_both_action_bars_are_left_aligned_and_wrappable(self) -> None:
        for route, attribute in (
            ("patients:patient_list", "data-patient-filter-actions"),
            ("patients:patient_map", "data-map-filter-actions"),
        ):
            with self.subTest(route=route):
                actions = self.layout(route).one(attribute)
                self.assertTrue(
                    {"justify-content-start", "flex-wrap", "gap-2"} <= actions.classes
                )
                self.assertNotIn("justify-content-lg-end", actions.parents[-1].classes)

    def test_map_options_follow_and_are_outside_the_filter_panel(self) -> None:
        document = self.layout()
        panel = document.one("data-patient-filter-panel")
        options = document.one("data-map-display-options")
        self.assertGreater(options.position, panel.position)
        self.assertNotIn(panel, options.parents)
        self.assertTrue({"border", "rounded", "p-3"} <= options.classes)
        self.assertEqual(options.attrs["aria-labelledby"], "map-display-options-title")

    def test_checkbox_and_tree_controls_remain_inside_the_get_form(self) -> None:
        document = self.layout()
        form = document.one("data-patient-filter-form")
        options = document.one("data-map-display-options")
        checkbox = document.one("id", "show-empty-wards")
        self.assertIn(form, options.parents)
        self.assertIn(options, checkbox.parents)
        self.assertEqual(checkbox.attrs["aria-describedby"], "map-empty-wards-help")
        self.assertEqual(document.one("id", "map-empty-wards-help").tag, "p")
        for identifier in ("expand-all", "collapse-all", "refresh-data"):
            control = document.one("id", identifier)
            self.assertIn(options, control.parents)
            self.assertEqual(control.attrs["type"], "button")

    def test_dirty_status_is_by_apply_not_inside_map_options(self) -> None:
        document = self.layout()
        status = document.one("data-patient-filter-dirty")
        self.assertIn(document.one("data-patient-filter-panel"), status.parents)
        self.assertNotIn(document.one("data-map-display-options"), status.parents)
        self.assertGreater(
            status.position, document.one("data-map-filter-actions").position
        )

    def test_preferences_are_a_separate_card_and_independent_post(self) -> None:
        for route in ("patients:patient_list", "patients:patient_map"):
            with self.subTest(route=route):
                document = self.layout(route)
                panel = document.one("data-tag-preference-panel")
                self.assertIn("card", panel.classes)
                post = document.one("data-tag-preference-form")
                self.assertEqual(post.attrs["method"], "post")
                self.assertIn(panel, post.parents)
                self.assertFalse(any(parent.tag == "form" for parent in post.parents))
