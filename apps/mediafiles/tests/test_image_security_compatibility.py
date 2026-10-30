"""Pillow major-version compatibility contract for media handling (S3a).

Slice ``eqmd-sec-003a`` moves Pillow from 12 to 13. These tests encode the
behaviour that must survive the major bump, using synthetic in-memory images
only: allowed and denied formats, relevant colour modes, corrupt payloads,
thumbnail generation, and denial of access to protected originals.

The suite is deliberately dual-purpose: it is expected to be GREEN on the
accepted S2 runtime (Pillow 12.0.0) as a behavioural baseline, and must stay
GREEN on the reconstructed runtime (Pillow 13). No production parser, model,
permission, or validation rule is changed here; deeper view-level coverage
already lives in ``test_views.py`` and is not duplicated.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image

from apps.mediafiles.image_processor import ImageProcessor
from apps.mediafiles.security import FileValidator
from apps.mediafiles.validators import validate_media_file

from .factories import create_patient, create_photo_on_disk, create_user

LOGIN_URL = "/accounts/login/"

#: Formats accepted by the production upload gate (``FileValidator``).
ALLOWED_UPLOADS: tuple[tuple[str, str, str, str], ...] = (
    ("JPEG", "RGB", ".jpg", "image/jpeg"),
    ("PNG", "RGB", ".png", "image/png"),
    ("PNG", "RGBA", ".png", "image/png"),
    ("WEBP", "RGB", ".webp", "image/webp"),
)

#: Pillow-decodable formats that the upload gate must keep rejecting.
DENIED_UPLOADS: tuple[tuple[str, str, str], ...] = (
    ("GIF", ".gif", "image/gif"),
    ("BMP", ".bmp", "image/bmp"),
    ("TIFF", ".tiff", "image/tiff"),
    ("ICO", ".ico", "image/x-icon"),
)


def synthetic_image_bytes(
    image_format: str,
    mode: str = "RGB",
    size: tuple[int, int] = (64, 48),
) -> bytes:
    """Render a deterministic in-memory image and return its encoded bytes."""
    buffer = io.BytesIO()
    Image.new(mode, size).save(buffer, format=image_format)
    return buffer.getvalue()


def as_upload(filename: str, content: bytes, content_type: str) -> SimpleUploadedFile:
    """Wrap raw bytes in the Django upload object used by the validators."""
    return SimpleUploadedFile(filename, content, content_type=content_type)


class AllowedImageFormatCompatibilityTests(TestCase):
    """Allowed JPEG/PNG/WebP uploads keep passing the production gate."""

    def test_production_gate_accepts_jpeg_png_and_webp(self) -> None:
        for image_format, mode, extension, content_type in ALLOWED_UPLOADS:
            with self.subTest(format=image_format, mode=mode):
                upload = as_upload(
                    f"foto{extension}",
                    synthetic_image_bytes(image_format, mode),
                    content_type,
                )
                FileValidator.validate_image_file(upload)

    def test_metadata_reports_format_mode_and_dimensions(self) -> None:
        for image_format, mode, extension, content_type in ALLOWED_UPLOADS:
            with self.subTest(format=image_format, mode=mode):
                upload = as_upload(
                    f"foto{extension}",
                    synthetic_image_bytes(image_format, mode, (120, 80)),
                    content_type,
                )
                metadata = validate_media_file(upload, "image")["metadata"]
                self.assertEqual(metadata["format"], image_format)
                self.assertEqual(metadata["mode"], mode)
                self.assertEqual((metadata["width"], metadata["height"]), (120, 80))

    def test_webp_payload_is_identified_as_webp_container(self) -> None:
        payload = synthetic_image_bytes("WEBP", "RGB", (32, 16))
        with Image.open(io.BytesIO(payload)) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(image.size, (32, 16))


class DeniedImageFormatCompatibilityTests(TestCase):
    """Formats outside the allowlist stay rejected after the Pillow bump."""

    def test_non_allowlisted_formats_are_rejected_by_upload_gate(self) -> None:
        for image_format, extension, content_type in DENIED_UPLOADS:
            with self.subTest(format=image_format):
                upload = as_upload(
                    f"arquivo{extension}",
                    synthetic_image_bytes(image_format),
                    content_type,
                )
                with self.assertRaises(ValidationError):
                    FileValidator.validate_image_file(upload)

    def test_gif_payload_renamed_as_png_is_rejected(self) -> None:
        """Pillow can decode GIF, so the magic-number gate must reject it."""
        gif_payload = synthetic_image_bytes("GIF")
        with Image.open(io.BytesIO(gif_payload)) as image:
            self.assertEqual(image.format, "GIF")

        upload = as_upload("disfarcado.png", gif_payload, "image/png")
        with self.assertRaises(ValidationError):
            FileValidator.validate_image_file(upload)

    def test_disallowed_declared_mime_type_is_rejected(self) -> None:
        upload = as_upload("foto.png", synthetic_image_bytes("PNG"), "image/gif")
        with self.assertRaises(ValidationError):
            FileValidator.validate_image_file(upload)


class CorruptImageCompatibilityTests(TestCase):
    """Invalid payloads fail closed through both validation layers."""

    def test_truncated_jpeg_is_rejected_everywhere(self) -> None:
        valid = synthetic_image_bytes("JPEG")
        truncated = valid[: len(valid) // 2]

        with self.assertRaises(ValidationError):
            validate_media_file(
                as_upload("corte.jpg", truncated, "image/jpeg"), "image"
            )

        self.assertFalse(self._processor_validates(truncated, ".jpg", "image/jpeg"))

    def test_empty_and_random_payloads_are_rejected(self) -> None:
        payloads = {
            "empty": (b"", "vazio.jpg", "image/jpeg"),
            "random": (b"not an image at all", "lixo.png", "image/png"),
        }
        for label, (payload, filename, content_type) in payloads.items():
            with self.subTest(payload=label), self.assertRaises(ValidationError):
                validate_media_file(as_upload(filename, payload, content_type), "image")

    def test_oversized_width_is_rejected_by_dimension_guard(self) -> None:
        oversized = synthetic_image_bytes("PNG", "RGB", (10001, 1))
        with self.assertRaises(ValidationError):
            validate_media_file(as_upload("larga.png", oversized, "image/png"), "image")

    def _processor_validates(
        self, payload: bytes, extension: str, content_type: str
    ) -> bool:
        """Run ``ImageProcessor.validate_image`` against a temporary file."""
        upload = as_upload(f"probe{extension}", payload, content_type)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"probe{extension}"
            path.write_bytes(upload.read())
            return ImageProcessor.validate_image(str(path))


class ThumbnailCompatibilityTests(TestCase):
    """Thumbnails stay JPEG, bounded, and mode-safe across Pillow majors."""

    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.directory = Path(self._directory.name)

    def tearDown(self) -> None:
        self._directory.cleanup()

    def test_thumbnail_matrix_covers_allowed_formats_and_modes(self) -> None:
        cases = (
            ("JPEG", "RGB"),
            ("PNG", "RGBA"),
            ("PNG", "LA"),
            ("PNG", "P"),
            ("PNG", "L"),
            ("WEBP", "RGB"),
        )
        for image_format, mode in cases:
            with self.subTest(format=image_format, mode=mode):
                source = self._write_source(image_format, mode)
                target = self.directory / f"{image_format}-{mode}-thumb.jpg"

                self.assertTrue(ImageProcessor.generate_thumbnail(source, target))
                with Image.open(target) as thumbnail:
                    self.assertEqual(thumbnail.format, "JPEG")
                    self.assertIn(thumbnail.mode, {"RGB", "L"})
                    self.assertLessEqual(max(thumbnail.size), 300)

    def test_thumbnail_preserves_aspect_ratio(self) -> None:
        source = self._write_source("JPEG", "RGB", size=(400, 200))
        target = self.directory / "ratio.jpg"

        self.assertTrue(ImageProcessor.generate_thumbnail(source, target))
        with Image.open(target) as thumbnail:
            self.assertEqual(thumbnail.size, (300, 150))

    def test_corrupt_source_fails_closed(self) -> None:
        source = self.directory / "corrupt.jpg"
        source.write_bytes(b"\xff\xd8\xff\xe0truncated")
        target = self.directory / "corrupt-thumb.jpg"

        self.assertFalse(ImageProcessor.generate_thumbnail(source, target))
        self.assertFalse(target.exists())
        self.assertEqual(ImageProcessor.get_image_metadata(str(source)), {})
        self.assertFalse(ImageProcessor.validate_image(str(source)))

    def _write_source(
        self,
        image_format: str,
        mode: str,
        size: tuple[int, int] = (64, 48),
    ) -> str:
        """Persist a synthetic source image and return its path."""
        path = self.directory / f"source-{image_format}-{mode}.bin"
        path.write_bytes(synthetic_image_bytes(image_format, mode, size))
        return str(path)


class ProtectedImageAccessCompatibilityTests(TestCase):
    """Protected originals stay protected for images produced by Pillow."""

    def setUp(self) -> None:
        self.client = Client()
        self.owner = create_user(
            username="owner", password_change_required=False, terms_accepted=True
        )
        self.other = create_user(
            username="other", password_change_required=False, terms_accepted=True
        )
        self.patient = create_patient(self.owner)
        self.photo = create_photo_on_disk(
            self.patient,
            self.owner,
            content=synthetic_image_bytes("JPEG", "RGB", (80, 60)),
        )

    def test_anonymous_access_to_original_is_denied(self) -> None:
        url = reverse("mediafiles:serve_file", kwargs={"file_id": self.photo.file_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(LOGIN_URL, response["Location"])

    def test_authenticated_user_without_event_permission_is_denied(self) -> None:
        self.client.force_login(self.other)
        url = reverse("mediafiles:photo_detail", kwargs={"pk": self.photo.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_unknown_file_id_does_not_leak_existence(self) -> None:
        self.client.force_login(self.owner)
        url = reverse(
            "mediafiles:serve_file",
            kwargs={"file_id": "11111111-1111-1111-1111-111111111111"},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
