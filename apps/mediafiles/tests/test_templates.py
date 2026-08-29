"""
Template tests for VideoClip, photo, and photo-series functionality.

Tests that the current mediafiles templates render without errors and keep
secure media rendering (FilePond ``serve_file``/``serve_thumbnail`` URLs,
permission-aware action buttons).

Fixtures use the current FilePond models: VideoClip stores ``file_id``
metadata and its original lives under ``videos/YYYY/MM/originals/<file_id>.mp4``.
Hospital was removed in the single-hospital refactor.
"""

from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.mediafiles.templatetags.mediafiles_tags import (
    video_duration,
    video_modal_trigger,
    video_player,
    video_thumbnail,
)

from .factories import (
    create_patient,
    create_photo_on_disk,
    create_user,
    create_videoclip_on_disk,
)

User = get_user_model()


class MediaTemplatePermissionMixin:
    """Grant the events permissions a template view request needs."""

    def grant_event_permissions(self, user):
        from django.contrib.auth.models import Permission

        for codename in ("add_event", "view_event", "change_event", "delete_event"):
            user.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label="events", codename=codename
                )
            )


class VideoClipTemplateTests(MediaTemplatePermissionMixin, TestCase):
    """Test VideoClip template rendering."""

    def setUp(self):
        """Set up test data"""
        self.user = create_user(
            username="testuser", password_change_required=False, terms_accepted=True
        )
        self.grant_event_permissions(self.user)

        self.patient = create_patient(self.user)
        self.videoclip = create_videoclip_on_disk(
            self.patient,
            self.user,
            description="Test video clip",
            caption="Test caption",
        )

        self.client = Client()
        self.client.force_login(self.user)

    def test_videoclip_form_template_renders(self):
        """Test that videoclip_form.html renders without errors"""
        url = reverse(
            "mediafiles:videoclip_create", kwargs={"patient_id": self.patient.id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Novo Vídeo")
        self.assertContains(response, "videoclip.css")
        self.assertContains(response, self.patient.name)

    def test_videoclip_detail_template_renders(self):
        """Test that videoclip_detail.html renders without errors"""
        url = reverse("mediafiles:videoclip_detail", kwargs={"pk": self.videoclip.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test video clip")
        self.assertContains(response, "video-player")
        self.assertContains(response, "fullscreenModal")
        self.assertContains(response, "videoclip.css")
        # Secure rendering: the streaming URL is the FilePond video source
        self.assertContains(
            response,
            reverse(
                "mediafiles:videoclip_stream",
                kwargs={"pk": self.videoclip.pk},
            ),
        )

    def test_videoclip_update_template_renders(self):
        """Test that videoclip_form.html renders for update"""
        url = reverse("mediafiles:videoclip_update", kwargs={"pk": self.videoclip.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editar Vídeo")
        self.assertContains(response, "Vídeo Atual")
        self.assertContains(response, "test.mp4")

    def test_videoclip_delete_template_renders(self):
        """Test that videoclip_confirm_delete.html renders without errors"""
        url = reverse("mediafiles:videoclip_delete", kwargs={"pk": self.videoclip.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirmar Exclusão")
        self.assertContains(response, "Test video clip")
        self.assertContains(response, "confirmDelete")

    def test_event_card_videoclip_template_renders(self):
        """Test that event_card_videoclip.html renders without errors"""
        template_string = """
        {% load mediafiles_tags %}
        {% include "events/partials/event_card_videoclip.html" with event=videoclip event_data=event_data %}
        """

        template = Template(template_string)
        context = Context(
            {
                "videoclip": self.videoclip,
                "event_data": {
                    "event": self.videoclip,
                    "can_edit": True,
                    "can_delete": True,
                    "excerpt": "Test excerpt",
                },
            }
        )

        rendered = template.render(context)

        # Check for key elements of the current card contract
        self.assertIn("videoclip-event-content", rendered)
        self.assertIn("video-preview-card", rendered)
        self.assertIn("Baixar vídeo", rendered)
        self.assertIn("Test video clip", rendered)
        self.assertIn(f"videoModal{self.videoclip.pk}", rendered)
        # Download link points at the current download endpoint
        self.assertIn(
            reverse("mediafiles:videoclip_download", kwargs={"pk": self.videoclip.pk}),
            rendered,
        )

    def test_video_player_partial_renders(self):
        """Test that video_player.html partial renders without errors"""
        template_string = """
        {% include "mediafiles/partials/video_player.html" with videoclip=videoclip controls=True %}
        """

        template = Template(template_string)
        context = Context({"videoclip": self.videoclip})

        rendered = template.render(context)

        # Check for key elements of the current partial
        self.assertIn("video-player-component", rendered)
        self.assertIn("controls", rendered)
        self.assertIn(
            reverse("mediafiles:videoclip_stream", kwargs={"pk": self.videoclip.pk}),
            rendered,
        )
        self.assertIn("Seu navegador não suporta", rendered)
        # The partial still reads the removed ``media_file`` relation for the
        # source ``type`` attribute, so it renders empty under the FilePond
        # model (pinned current rendering; production-gap candidate).
        self.assertIn('type=""', rendered)

    def test_video_modal_partial_renders(self):
        """Test that video_modal.html partial renders without errors"""
        template_string = """
        {% include "mediafiles/partials/video_modal.html" %}
        """

        template = Template(template_string)
        context = Context({})

        rendered = template.render(context)

        # Check for key elements
        self.assertIn("videoModal", rendered)
        self.assertIn("video-modal-player", rendered)
        self.assertIn("videoPlayPause", rendered)

    def test_photo_detail_renders_secure_file_url(self):
        """Photo detail renders the secure FilePond serving URL."""
        photo = create_photo_on_disk(
            self.patient, self.user, description="Template photo"
        )
        url = reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, photo.description)
        self.assertContains(
            response,
            reverse("mediafiles:serve_file", kwargs={"file_id": photo.file_id}),
        )

    def test_photoseries_detail_renders_gallery(self):
        """PhotoSeries detail renders the secure photo gallery."""
        from apps.mediafiles.models import PhotoSeries

        series = PhotoSeries.objects.create(
            caption="Template series",
            description="Series description",
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
        )
        url = reverse("mediafiles:photoseries_detail", kwargs={"pk": series.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Series description")
        self.assertContains(response, "photo-gallery")


class VideoClipTemplateTagTests(TestCase):
    """Test VideoClip template tags.

    The tags guard on ``hasattr(videoclip, 'media_file')``; VideoClip no
    longer carries a ``media_file`` relation after the FilePond migration,
    so the current contract returns ``""`` for FilePond clips and for None
    (the tags are legacy-compat shims; documented production-gap candidate).
    """

    def setUp(self):
        """Set up test data"""
        self.user = create_user(
            username="testuser", password_change_required=False, terms_accepted=True
        )
        self.patient = create_patient(self.user)
        self.videoclip = create_videoclip_on_disk(
            self.patient, self.user, description="Tag test clip"
        )

    def test_video_player_tag(self):
        """video_player returns empty markup for FilePond clips (no media_file)"""
        self.assertEqual(
            video_player(self.videoclip, controls=True, autoplay=False), ""
        )

    def test_video_thumbnail_tag(self):
        """video_thumbnail returns empty markup for FilePond clips"""
        self.assertEqual(video_thumbnail(self.videoclip, size="medium"), "")

    def test_video_duration_tag(self):
        """video_duration returns empty for FilePond clips (no media_file)"""
        self.assertEqual(video_duration(self.videoclip), "")

    def test_video_modal_trigger_tag(self):
        """video_modal_trigger returns empty markup for FilePond clips"""
        self.assertEqual(
            video_modal_trigger(self.videoclip, trigger_text="Play Video"), ""
        )

    def test_template_tags_with_none_videoclip(self):
        """Test template tags handle None videoclip gracefully"""
        self.assertEqual(video_player(None), "")
        self.assertEqual(video_thumbnail(None), "")
        self.assertEqual(video_duration(None), "")
        self.assertEqual(video_modal_trigger(None), "")

    def test_photo_modal_trigger_tag_legacy_shim(self):
        """photo_modal_trigger is a legacy ``media_file`` shim.

        The tag guards on ``hasattr(photo, 'media_file')``; Photo no longer
        carries that relation, so the current contract returns ``""`` for
        FilePond photos (same legacy-compat contract as the video tags).
        """
        photo = create_photo_on_disk(self.patient, self.user)
        from apps.mediafiles.templatetags.mediafiles_tags import (
            photo_modal_trigger,
        )

        self.assertEqual(photo_modal_trigger(photo, trigger_text="Ver foto"), "")


class VideoClipCSSJSTests(MediaTemplatePermissionMixin, TestCase):
    """Test that CSS and JS static assets are available and loaded."""

    def setUp(self):
        """Set up test data"""
        self.user = create_user(
            username="testuser", password_change_required=False, terms_accepted=True
        )
        self.grant_event_permissions(self.user)
        self.patient = create_patient(self.user)

        self.client = Client()
        self.client.force_login(self.user)

    def test_videoclip_css_loaded_in_form(self):
        """Test that videoclip.css is loaded in form template"""
        url = reverse(
            "mediafiles:videoclip_create", kwargs={"patient_id": self.patient.id}
        )
        response = self.client.get(url)

        self.assertContains(response, "videoclip.css")

    def test_static_files_exist(self):
        """Test that static files exist"""
        from django.contrib.staticfiles.finders import find

        # Check CSS file exists
        css_path = find("mediafiles/css/videoclip.css")
        self.assertIsNotNone(css_path, "videoclip.css not found in static files")

        # Check JS file exists
        js_path = find("mediafiles/js/videoclip.js")
        self.assertIsNotNone(js_path, "videoclip.js not found in static files")

    def test_videoclip_assets_render_without_error(self):
        """The form page renders with the video assets without errors."""
        url = reverse(
            "mediafiles:videoclip_create", kwargs={"patient_id": self.patient.id}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_photo_form_template_renders(self):
        """The photo form template renders for a patient."""
        url = reverse("mediafiles:photo_create", kwargs={"patient_id": self.patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nova Foto")
        self.assertContains(response, self.patient.name)

    def test_photo_confirm_delete_template_renders(self):
        """The photo confirm-delete template renders."""
        photo = create_photo_on_disk(self.patient, self.user)
        url = reverse("mediafiles:photo_delete", kwargs={"pk": photo.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirmar Exclusão")

    def test_photoseries_create_template_renders(self):
        """The photo-series create template renders with the patient."""
        url = reverse(
            "mediafiles:photoseries_create",
            kwargs={"patient_id": self.patient.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nova Série de Fotos")
        self.assertContains(response, self.patient.name)


class PhotoCardRenderTests(TestCase):
    """Direct rendering of the photo event card with FilePond photos."""

    def setUp(self):
        """Set up test data"""
        self.user = create_user(
            username="testuser", password_change_required=False, terms_accepted=True
        )
        self.patient = create_patient(self.user)

    def test_photo_event_card_renders_secure_urls(self):
        """The photo event card renders the secure FilePond URLs."""
        photo = create_photo_on_disk(
            self.patient,
            self.user,
            description="Card photo",
            filename="card.jpg",
        )
        photo.thumbnail_path = (
            f"photos/{photo.created_at.strftime('%Y/%m')}/thumbnails/"
            f"{photo.file_id}_thumb.jpg"
        )
        photo.save(update_fields=["thumbnail_path"])

        rendered = render_to_string(
            "events/partials/event_card_photo.html",
            {
                "event": photo,
                "event_data": {
                    "event": photo,
                    "can_edit": False,
                    "can_delete": False,
                    "excerpt": photo.description[:100],
                },
                "user": self.user,
            },
        )

        serve_url = reverse("mediafiles:serve_file", kwargs={"file_id": photo.file_id})
        thumbnail_url = reverse(
            "mediafiles:serve_thumbnail", kwargs={"file_id": photo.file_id}
        )
        self.assertIn(serve_url, rendered)
        self.assertIn(thumbnail_url, rendered)
        self.assertIn("photo-modal-trigger", rendered)
        self.assertNotIn("btn-outline-warning", rendered)  # no edit without can_edit

    def test_photoseries_carousel_partial_renders(self):
        """The series carousel partial renders the loading placeholder.

        Note: rendering the carousel *with photos* raises NoReverseMatch for
        ``mediafiles:media_download`` (a URL that does not exist). The
        current series detail template uses ``photo_gallery`` instead of the
        carousel, so the broken download link is latent; recorded as a
        production-gap candidate for the planner.
        """
        from apps.mediafiles.models import PhotoSeries

        series = PhotoSeries.objects.create(
            caption="",
            description="Carousel series",
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
        )

        rendered = render_to_string(
            "mediafiles/partials/photoseries_carousel.html",
            {
                "series": series,
                "photos": series.get_ordered_photos(),
                "photo_count": series.get_photo_count(),
                "carousel_id": f"photoCarousel_{series.id}",
            },
        )
        self.assertIn("Nenhuma foto encontrada", rendered)

    def test_photoseries_carousel_empty_series_placeholder(self):
        """The carousel partial shows the error placeholder when empty."""
        from apps.mediafiles.models import PhotoSeries

        series = PhotoSeries.objects.create(
            caption="",
            description="Empty series",
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
        )
        rendered = render_to_string(
            "mediafiles/partials/photoseries_carousel.html", {"series": series}
        )
        self.assertIn("Nenhuma foto encontrada", rendered)
