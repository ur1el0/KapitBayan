from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.test import TestCase


@skipUnless(
    bool(getattr(settings, "CLOUDINARY_STORAGE", None)),
    "Cloudinary storage is not configured in this environment.",
)
class ResidentAwareCloudinaryStorageTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from config.private_media_storage import ResidentAwareCloudinaryStorage

        cls.storage_class = ResidentAwareCloudinaryStorage

    def setUp(self):
        self.storage = self.storage_class()

    def test_new_resident_upload_uses_authenticated_delivery_and_opaque_id(self):
        with patch(
            "config.private_media_storage.cloudinary.uploader.upload",
            return_value={"public_id": "media/resident_ids/random-id"},
        ) as upload:
            self.storage._upload(
                "media/resident_ids/original_resident_filename.png",
                ContentFile(b"test image"),
            )

        upload_options = upload.call_args.kwargs
        self.assertEqual(upload_options["type"], "authenticated")
        self.assertTrue(
            upload_options["public_id"].startswith("media/resident_ids/")
        )
        self.assertNotIn("original_resident_filename", upload_options["public_id"])

    def test_private_read_builds_a_signed_authenticated_url(self):
        with patch.object(
            self.storage,
            "_download",
            return_value=ContentFile(b"test image"),
        ) as download:
            self.storage.open_private_resident_media(
                "media/resident_ids/random-id"
            )

        url = download.call_args.args[0]
        self.assertIn("/image/authenticated/", url)
        self.assertIn("/s--", url)

    def test_extensionless_private_proof_uses_original_cloudinary_format(self):
        with patch(
            "config.private_media_storage.cloudinary.api.resource",
            return_value={"format": "pdf"},
        ) as metadata, patch.object(
            self.storage, "_download", return_value=ContentFile(b"%PDF-1.4")
        ) as download:
            asset_format = self.storage.get_private_media_format(
                "barangay_onboarding/opaque-asset-id"
            )
            self.storage.open_private_media(
                "barangay_onboarding/opaque-asset-id", asset_format=asset_format
            )

        self.assertEqual(asset_format, "pdf")
        self.assertEqual(metadata.call_args.kwargs["type"], "authenticated")
        self.assertEqual(metadata.call_args.kwargs["resource_type"], "image")
        url = download.call_args.args[0]
        self.assertIn("/image/authenticated/", url)
        self.assertIn("/s--", url)
        self.assertIn("opaque-asset-id.pdf", url)

    def test_storage_does_not_expose_private_cloudinary_urls(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "Private evidence must be served through an authorized media endpoint.",
        ):
            self.storage.url("media/resident_ids/random-id")
