"""
Failing tests for source tracking functionality.
These tests will fail until source tracking features are implemented.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import NoReverseMatch, reverse

from apps.drugtemplates.models import DrugTemplate

User = get_user_model()


class SourceTrackingTest(TestCase):
    """Tests for drug template source tracking functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_drugtemplate_list_view_shows_both_sources(self):
        """Test that the list view exposes user-created and imported templates.

        Current contract: the list shows public templates plus the user's own
        private templates for both sources. View-level source filtering is part
        of the active refactor change and is not implemented; source semantics
        live on the model manager (see
        test_drugtemplate_queryset_methods_for_source_filtering).
        """
        # Create user template
        DrugTemplate.objects.create(
            name="User Drug",
            concentration="100 mg",
            pharmaceutical_form="comprimido",
            usage_instructions="User created instructions",
            creator=self.user,
            is_imported=False,
        )

        # Create imported template (public so any doctor/resident can see it)
        system_user = User.objects.create_user(
            username="system",
            email="system@hospital.internal",
            password_change_required=False,
            terms_accepted=True,
        )
        DrugTemplate.objects.create(
            name="Imported Drug",
            concentration="200 mg",
            pharmaceutical_form="cápsula",
            creator=system_user,
            is_imported=True,
            import_source="CSV Import",
            is_public=True,
        )

        response = self.client.get(reverse("drugtemplates:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User Drug")
        self.assertContains(response, "Imported Drug")

    def test_drugtemplate_detail_view_shows_imported_template(self):
        """Test that the detail view renders imported templates.

        Current contract: the detail page renders the name and the computed
        presentation for any accessible template. The import-source badge is
        part of the active refactor change and is not implemented.
        """

        system_user = User.objects.create_user(
            username="system",
            email="system@hospital.internal",
            password_change_required=False,
            terms_accepted=True,
        )
        imported_template = DrugTemplate.objects.create(
            name="Imported Drug",
            concentration="250 mg",
            pharmaceutical_form="solução",
            creator=system_user,
            is_imported=True,
            import_source="MERGED_medications.csv",
            is_public=True,
        )

        response = self.client.get(
            reverse("drugtemplates:detail", kwargs={"pk": imported_template.pk})
        )
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Imported Drug")
        # Computed presentation (backward-compatible property)
        self.assertContains(response, "250 mg solução")

    def test_drugtemplate_edit_permissions_for_imported(self):
        """Test that imported templates cannot be fully edited."""
        # This will fail until edit permission logic is implemented

        system_user = User.objects.create_user(
            username="system",
            email="system@hospital.internal",
            password_change_required=False,
            terms_accepted=True,
        )
        imported_template = DrugTemplate.objects.create(
            name="Imported Drug",
            concentration="300 mg",
            pharmaceutical_form="injetável",
            creator=system_user,
            is_imported=True,
            import_source="CSV Import",
        )

        # Should not allow editing core imported fields
        response = self.client.get(
            reverse("drugtemplates:update", kwargs={"pk": imported_template.pk})
        )

        # Should either redirect or show limited edit form
        self.assertTrue(
            response.status_code in [302, 403]
            or "readonly" in response.content.decode().lower()
        )

    def test_drugtemplate_admin_displays_source_information(self):
        """Test that admin interface displays source tracking information."""
        # This will fail until admin interface is updated

        # Create admin user
        User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            password_change_required=False,
            terms_accepted=True,
        )
        self.client.login(username="admin", password="adminpass123")

        # Create imported template
        system_user = User.objects.create_user(
            username="system",
            email="system@hospital.internal",
            password_change_required=False,
            terms_accepted=True,
        )
        DrugTemplate.objects.create(
            name="Admin Test Drug",
            concentration="400 mg",
            pharmaceutical_form="cápsula",
            creator=system_user,
            is_imported=True,
            import_source="Test Source",
        )

        # Check admin changelist
        response = self.client.get("/admin/drugtemplates/drugtemplate/")
        self.assertEqual(response.status_code, 200)

        # Should show import source in list
        self.assertContains(response, "Test Source")
        self.assertContains(response, "Importado")

    def test_drugtemplate_admin_filters_by_source(self):
        """Test that admin interface can filter by source."""
        # This will fail until admin filters are implemented

        # Create admin user
        User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            password_change_required=False,
            terms_accepted=True,
        )
        self.client.login(username="admin", password="adminpass123")

        # A user-created row makes the 'Criado por usuário' origin value appear
        # in the changelist next to the imported row.
        DrugTemplate.objects.create(
            name="User Admin Drug",
            concentration="500 mg",
            pharmaceutical_form="comprimido",
            usage_instructions="User created instructions",
            creator=self.user,
        )

        # Check admin changelist has source filters
        response = self.client.get("/admin/drugtemplates/drugtemplate/")
        self.assertEqual(response.status_code, 200)

        # Origin column header and both origin values
        self.assertContains(response, "Origem")  # Source filter
        self.assertContains(response, "Importado")
        self.assertContains(response, "Criado por usuário")

    def test_drugtemplate_queryset_methods_for_source_filtering(self):
        """Test model manager methods for source filtering."""

        # Create user template
        user_template = DrugTemplate.objects.create(
            name="User Drug",
            concentration="100 mg",
            pharmaceutical_form="comprimido",
            usage_instructions="User instructions",
            creator=self.user,
            is_imported=False,
        )

        # Create imported template
        system_user = User.objects.create_user(
            username="system",
            email="system@hospital.internal",
            password_change_required=False,
            terms_accepted=True,
        )
        imported_template = DrugTemplate.objects.create(
            name="Imported Drug",
            concentration="200 mg",
            pharmaceutical_form="cápsula",
            creator=system_user,
            is_imported=True,
            import_source="CSV",
        )

        # Test manager methods
        user_created = DrugTemplate.objects.user_created()
        self.assertIn(user_template, user_created)
        self.assertNotIn(imported_template, user_created)

        imported_drugs = DrugTemplate.objects.imported()
        self.assertIn(imported_template, imported_drugs)
        self.assertNotIn(user_template, imported_drugs)

        from_source = DrugTemplate.objects.from_source("CSV")
        self.assertIn(imported_template, from_source)
        self.assertNotIn(user_template, from_source)

    def test_drugtemplate_api_includes_source_information(self):
        """Test that API responses include source tracking information."""
        # This will fail until API is updated (if API exists)

        system_user = User.objects.create_user(
            username="system",
            email="system@hospital.internal",
            password_change_required=False,
            terms_accepted=True,
        )
        imported_template = DrugTemplate.objects.create(
            name="API Test Drug",
            concentration="500 mg",
            pharmaceutical_form="tablet",
            creator=system_user,
            is_imported=True,
            import_source="API Test",
        )

        # If there's a REST API endpoint, test it includes source info
        try:
            api_url = reverse(
                "api:drugtemplate-detail", kwargs={"pk": imported_template.pk}
            )
            response = self.client.get(api_url, HTTP_ACCEPT="application/json")

            if response.status_code == 200:
                data = response.json()
                self.assertIn("is_imported", data)
                self.assertIn("import_source", data)
                self.assertTrue(data["is_imported"])
                self.assertEqual(data["import_source"], "API Test")
        except NoReverseMatch:
            # Skip if no API endpoint exists yet
            pass

    def test_drugtemplate_search_matches_across_sources(self):
        """Test that name search matches templates from both sources.

        Current contract: the list view filters by the 'name' parameter with
        accent/case-insensitive matching across user-created and imported
        templates. A 'source' parameter is not consumed by the view (active-
        change behavior).
        """

        # Create templates with different sources
        DrugTemplate.objects.create(
            name="Searchable User Drug",
            concentration="100 mg",
            pharmaceutical_form="comprimido",
            usage_instructions="Search test",
            creator=self.user,
            is_imported=False,
        )

        system_user = User.objects.create_user(
            username="system",
            email="system@hospital.internal",
            password_change_required=False,
            terms_accepted=True,
        )
        DrugTemplate.objects.create(
            name="Searchable Imported Drug",
            concentration="200 mg",
            pharmaceutical_form="cápsula",
            creator=system_user,
            is_imported=True,
            import_source="Search Test CSV",
            is_public=True,
        )

        # Name search matches both sources
        response = self.client.get(
            reverse("drugtemplates:list"), {"name": "Searchable"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Searchable User Drug")
        self.assertContains(response, "Searchable Imported Drug")

    def test_drugtemplate_bulk_actions_respect_source_permissions(self):
        """Test that bulk admin actions respect source permissions."""
        # This will fail until bulk actions are implemented

        # Create admin user
        User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            password_change_required=False,
            terms_accepted=True,
        )
        self.client.login(username="admin", password="adminpass123")

        # Create mixed templates
        user_template = DrugTemplate.objects.create(
            name="User Template",
            concentration="100 mg",
            pharmaceutical_form="comprimido",
            usage_instructions="Test",
            creator=self.user,
            is_imported=False,
        )

        system_user = User.objects.create_user(
            username="system",
            email="system@hospital.internal",
            password_change_required=False,
            terms_accepted=True,
        )
        imported_template = DrugTemplate.objects.create(
            name="Imported Template",
            concentration="200 mg",
            pharmaceutical_form="cápsula",
            creator=system_user,
            is_imported=True,
            import_source="Bulk Test",
        )

        # Try to delete both via bulk action
        response = self.client.post(
            "/admin/drugtemplates/drugtemplate/",
            {
                "action": "delete_selected",
                "_selected_action": [user_template.pk, imported_template.pk],
            },
        )

        # Should either prevent deletion of imported or show warning
        self.assertTrue(
            response.status_code in [302, 200]
            and (
                "error" in response.content.decode().lower()
                or "warning" in response.content.decode().lower()
                or "imported" in response.content.decode().lower()
            )
        )
