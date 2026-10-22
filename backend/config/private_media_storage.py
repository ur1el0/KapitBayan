from pathlib import PurePosixPath
from uuid import uuid4

import cloudinary
import cloudinary.api
from cloudinary.exceptions import NotFound
from cloudinary_storage.storage import MediaCloudinaryStorage
from django.core.exceptions import ImproperlyConfigured


class ResidentAwareCloudinaryStorage(MediaCloudinaryStorage):
    """Store private resident and onboarding evidence as authenticated assets."""

    PRIVATE_DIRECTORIES = {
        "resident_ids", "resident_billings", "payment_proofs", "barangay_onboarding",
    }

    @classmethod
    def is_private_media(cls, name):
        return bool(cls.PRIVATE_DIRECTORIES.intersection(PurePosixPath(name).parts))

    @classmethod
    def is_private_resident_media(cls, name):
        """Backward-compatible name used by resident profile media code."""
        return cls.is_private_media(name)

    def _upload(self, name, content):
        resource_type = self._get_resource_type(name)
        if self.is_private_resident_media(name):
            public_id = (PurePosixPath(name).parent / uuid4().hex).as_posix()
            return cloudinary.uploader.upload(
                content,
                public_id=public_id,
                resource_type=resource_type,
                tags=self.TAG,
                type="authenticated",
            )

        options = {
            "use_filename": True,
            "resource_type": resource_type,
            "tags": self.TAG,
        }
        folder = PurePosixPath(name).parent.as_posix()
        if folder != ".":
            options["folder"] = folder
        return cloudinary.uploader.upload(content, **options)

    def get_private_media_format(self, name):
        """Resolve the original format when Cloudinary stores an extensionless public ID."""
        try:
            metadata = cloudinary.api.resource(
                self._prepend_prefix(name),
                resource_type=self._get_resource_type(name),
                type="authenticated",
            )
        except NotFound as exc:
            raise FileNotFoundError("Private media not found.") from exc
        return str(metadata.get("format") or "").lower()

    def open_private_media(self, name, mode="rb", *, asset_format=None):
        resource = cloudinary.CloudinaryResource(
            self._prepend_prefix(name),
            type="authenticated",
            default_resource_type=self._get_resource_type(name),
        )
        options = {"sign_url": True, "secure": True}
        if asset_format:
            options["format"] = asset_format
        return self._download(resource.build_url(**options), name, mode)

    def open_private_resident_media(self, name, mode="rb"):
        return self.open_private_media(name, mode)

    def _get_url(self, name):
        if not self.is_private_media(name):
            return super()._get_url(name)

        resource = cloudinary.CloudinaryResource(
            self._prepend_prefix(name),
            type="authenticated",
            default_resource_type=self._get_resource_type(name),
        )
        return resource.build_url(sign_url=True, secure=True)

    @staticmethod
    def _download(url, name, mode):
        import requests
        from django.core.files.base import ContentFile

        response = requests.get(url, timeout=15)
        if response.status_code == 404:
            raise IOError("Resident media not found.")
        response.raise_for_status()
        file_obj = ContentFile(response.content)
        file_obj.name = name
        file_obj.mode = mode
        return file_obj

    def url(self, name):
        if self.is_private_media(name):
            raise ImproperlyConfigured(
                "Private evidence must be served through an authorized media endpoint."
            )
        return super().url(name)
