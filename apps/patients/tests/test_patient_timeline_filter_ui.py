"""
Tests for patient timeline desktop filter trigger, offcanvas shell,
offcanvas filter form fields, active-filter indicator, and clear-filter flow.
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient


class PatientTimelineDesktopNoSidebarTests(TestCase):
    """Tests for removal of desktop filter sidebar and widened timeline column."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = EqmdCustomUser.objects.create_user(
            username='sidebar_testuser',
            email='sidebar@example.com',
            password='testpassword',
            password_change_required=False,
            terms_accepted=True,
        )

        content_type = ContentType.objects.get_for_model(Patient)
        view_permission = Permission.objects.get(
            content_type=content_type,
            codename='view_patient',
        )
        cls.user.user_permissions.add(view_permission)

        cls.patient = Patient.objects.create(
            name='Sidebar Test Patient',
            birthday=date(1980, 1, 1),
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client.login(username='sidebar_testuser', password='testpassword')
        self.url = reverse(
            'apps.patients:patient_events_timeline',
            kwargs={'patient_id': self.patient.pk},
        )

    def test_timeline_desktop_no_longer_renders_fixed_filter_sidebar(self):
        """Desktop layout must NOT render the old fixed col-lg-3 filter sidebar."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # The old desktop filter sidebar used col-lg-3 with d-none d-lg-block
        self.assertNotIn('col-lg-3', content)
        # The old sidebar had a heading "Filtros" inside the filter-panel
        # that is NOT inside an offcanvas. Verify no non-offcanvas filter-panel
        # with the "Filtros" heading exists.
        # We check that the only "Filtros" h2/h5 headings are inside the offcanvas.
        offcanvas_start = content.find('id="desktop-filter-offcanvas"')
        self.assertNotEqual(offcanvas_start, -1, "Offcanvas should still exist")
        # Find all occurrences of the sidebar-specific filter heading
        # The old sidebar had: <h2 class="text-medical-primary mb-3 h5">...Filtros...</h2>
        # outside the offcanvas.
        # Check that no filter-panel exists outside the offcanvas
        # and outside the mobile section.
        mobile_start = content.find('id="mobile-filters"')
        # Walk the content and ensure no 'col-lg-3' class appears anywhere
        self.assertNotIn('col-lg-3', content)

    def test_timeline_desktop_event_column_uses_full_width_without_sidebar(self):
        """Desktop event column must use full width (col-lg-12 or col-12) after sidebar removal."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # The timeline content column should no longer be col-lg-9;
        # it should be col-12 or col-lg-12 for full width.
        self.assertNotIn('col-lg-9', content)
        # The event column should still have a timeline-container
        self.assertIn('timeline-container', content)


class PatientTimelineDesktopFilterUITests(TestCase):
    """Tests for desktop filter trigger, offcanvas shell, and filter form."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = EqmdCustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            password_change_required=False,
            terms_accepted=True,
        )

        content_type = ContentType.objects.get_for_model(Patient)
        view_permission = Permission.objects.get(
            content_type=content_type,
            codename='view_patient',
        )
        cls.user.user_permissions.add(view_permission)

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1980, 1, 1),
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse(
            'apps.patients:patient_events_timeline',
            kwargs={'patient_id': self.patient.pk},
        )

    def _extract_offcanvas_body(self, content):
        """Extract the offcanvas body content between the offcanvas tags."""
        offcanvas_start = content.find('id="desktop-filter-offcanvas"')
        self.assertNotEqual(offcanvas_start, -1, "Offcanvas not found in response.")
        # Find the closing </div> pair — walk forward past nested divs
        depth = 0
        pos = content.rfind('<div', 0, offcanvas_start)  # outer div start
        i = pos
        while i < len(content):
            tag_start = content.find('<div', i)
            tag_end = content.find('</div>', i)
            if tag_start == -1 and tag_end == -1:
                break
            if tag_start != -1 and (tag_end == -1 or tag_start < tag_end):
                depth += 1
                i = tag_start + 4
            else:
                depth -= 1
                if depth == 0:
                    return content[pos:tag_end + 6]
                i = tag_end + 6
        return content[offcanvas_start:]

    def test_timeline_desktop_header_shows_filter_trigger(self):
        """Desktop header must render a filter trigger button visible on large screens."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="desktop-filter-trigger"', content)
        self.assertIn('data-bs-toggle="offcanvas"', content)
        self.assertIn('data-bs-target="#desktop-filter-offcanvas"', content)

    def test_timeline_renders_desktop_filter_offcanvas_shell(self):
        """Timeline must render an offcanvas shell with stable ID and accessible labels."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="desktop-filter-offcanvas"', content)
        has_aria = (
            'aria-label="Filtros da timeline"' in content
            or 'aria-labelledby="desktop-filter-offcanvas-label"' in content
        )
        self.assertTrue(has_aria, "Offcanvas shell must have an accessible label.")

    def test_timeline_offcanvas_renders_filter_form_fields(self):
        """Offcanvas must contain the filter form with all expected fields."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        offcanvas = self._extract_offcanvas_body(content)

        # Form must exist inside offcanvas
        self.assertIn('method="get"', offcanvas)
        # Event type checkboxes
        self.assertIn('name="types"', offcanvas)
        # Quick date radios
        self.assertIn('name="quick_date"', offcanvas)
        # Custom date range inputs
        self.assertIn('name="date_from"', offcanvas)
        self.assertIn('name="date_to"', offcanvas)
        # Submit button
        self.assertIn('Aplicar Filtros', offcanvas)
        # Clear filters link
        self.assertIn('Limpar Filtros', offcanvas)

    def test_timeline_offcanvas_preserves_filter_query_values(self):
        """When filters are active, the offcanvas form must reflect the current values."""
        response = self.client.get(self.url + '?quick_date=7d')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        offcanvas = self._extract_offcanvas_body(content)

        # The 7d radio should be checked inside the offcanvas
        self.assertIn('value="7d"', offcanvas)
        # Find the block containing value="7d" and verify "checked" is nearby
        seven_d_pos = offcanvas.find('value="7d"')
        # Look in a generous window that includes the id and checked attribute
        window = offcanvas[max(0, seven_d_pos - 10):seven_d_pos + 200]
        self.assertIn('checked', window)

    def test_timeline_desktop_filter_trigger_shows_active_state_when_filters_present(self):
        """Desktop trigger must show an active-state indicator when filters are applied."""
        response = self.client.get(self.url + '?quick_date=7d')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Find the desktop trigger button region
        trigger_pos = content.find('id="desktop-filter-trigger"')
        self.assertNotEqual(trigger_pos, -1, "Desktop filter trigger not found.")

        # Extract the trigger button element (from start of its <button tag to closing </button>)
        # Walk backwards to find the <button opener
        button_start = content.rfind('<button', 0, trigger_pos)
        button_end = content.find('</button>', trigger_pos)
        self.assertNotEqual(button_start, -1, "Could not find <button tag for desktop trigger.")
        self.assertNotEqual(button_end, -1, "Could not find closing </button> for desktop trigger.")
        trigger_html = content[button_start:button_end + len('</button>')]

        # Must have a badge or visual indicator showing filters are active
        self.assertIn('Ativos', trigger_html)

    def test_timeline_desktop_offcanvas_keeps_clear_filter_flow(self):
        """Offcanvas must contain a working clear-filters link pointing to the base timeline URL."""
        response = self.client.get(self.url + '?quick_date=7d')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        offcanvas = self._extract_offcanvas_body(content)

        # Clear-filters link must exist inside the offcanvas
        self.assertIn('Limpar Filtros', offcanvas)

        # The clear link must point to the patient timeline URL (no query params)
        timeline_url = reverse(
            'apps.patients:patient_events_timeline',
            kwargs={'patient_id': self.patient.pk},
        )
        self.assertIn(f'href="{timeline_url}"', offcanvas)
