from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status

from gridy_auth.models import Barangay, Resident, User
from .base import IsolatedAuthAPITestCase


def create_test_image(name="test_image.png"):
    image_data = BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(image_data, format="PNG")
    return SimpleUploadedFile(name, image_data.getvalue(), content_type="image/png")


class ProfileEvidenceAPITests(IsolatedAuthAPITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Evidence Test Barangay")
        self.user = User.objects.create_user(
            username="evidence_resident",
            password="SecurePassword123!",
            email="resident@evidence.test",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        self.resident = Resident.objects.create(
            user=self.user,
            full_name="Evidence Resident",
            birth_date="1995-03-12",
            contact_number="09123456789",
            is_verified=False,
            philsys_id_number="1234-5678-9012-3456",
        )
        image_content = ContentFile(create_test_image().read(), name="initial_philsys.png")
        self.resident.philsys_id_photo.save("initial_philsys.png", image_content, save=True)

        # Other resident for cross-tenant / isolation checks
        self.other_user = User.objects.create_user(
            username="other_resident",
            password="SecurePassword123!",
            email="other@evidence.test",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        self.other_resident = Resident.objects.create(
            user=self.other_user,
            full_name="Other Resident",
            birth_date="1992-07-21",
            contact_number="09987654321",
            is_verified=True,
            secondary_id_type="Passport",
        )
        other_image = ContentFile(create_test_image().read(), name="other_passport.png")
        self.other_resident.secondary_id_photo.save("other_passport.png", other_image, save=True)

    def test_remove_last_proof_is_rejected_with_400(self):
        """A resident with 1 proof cannot remove their sole proof."""
        self.client.force_authenticate(user=self.user)
        initial_file_name = self.resident.philsys_id_photo.name
        initial_id_number = self.resident.philsys_id_number

        # Attempt to remove via remove_philsys_id_photo flag
        response = self.client.patch(
            "/api/v1/auth/me/",
            {"profile": {"remove_philsys_id_photo": True}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_detail = str(response.data)
        self.assertIn("Cannot remove the only proof document on file", error_detail)

        # Confirm DB state was not mutated
        self.resident.refresh_from_db()
        self.assertTrue(bool(self.resident.philsys_id_photo))
        self.assertEqual(self.resident.philsys_id_photo.name, initial_file_name)
        self.assertEqual(self.resident.philsys_id_number, initial_id_number)

    def test_replace_sole_proof_with_another_valid_upload_succeeds(self):
        """Replacing the only proof with another valid upload succeeds."""
        self.client.force_authenticate(user=self.user)
        new_image = create_test_image("replacement_utility.png")

        # Replace philSys with utility billing in multipart
        response = self.client.patch(
            "/api/v1/auth/me/",
            {
                "remove_philsys_id_photo": "true",
                "utility_billing_type": "Electric / Meralco",
                "utility_billing_photo": new_image,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resident.refresh_from_db()
        self.assertFalse(bool(self.resident.philsys_id_photo))
        self.assertIsNone(self.resident.philsys_id_number)
        self.assertTrue(bool(self.resident.utility_billing_photo))
        self.assertEqual(self.resident.utility_billing_type, "Electric / Meralco")

    def test_remove_proof_when_another_remains_succeeds(self):
        """When a resident has multiple proofs on file, removing one succeeds."""
        # Add a second proof to resident
        second_image = ContentFile(create_test_image().read(), name="second_utility.png")
        self.resident.utility_billing_photo.save("second_utility.png", second_image, save=True)
        self.resident.utility_billing_type = "Water Utility"
        self.resident.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            "/api/v1/auth/me/",
            {"profile": {"remove_philsys_id_photo": True}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resident.refresh_from_db()
        self.assertFalse(bool(self.resident.philsys_id_photo))
        self.assertIsNone(self.resident.philsys_id_number)
        self.assertTrue(bool(self.resident.utility_billing_photo))
        self.assertEqual(self.resident.utility_billing_type, "Water Utility")

    def test_rbi_imported_resident_zero_proofs_can_add_first_proof(self):
        """A legacy RBI-imported resident starting with 0 proofs may upload their first proof."""
        rbi_user = User.objects.create_user(
            username="rbi_resident",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        rbi_profile = Resident.objects.create(
            user=rbi_user,
            full_name="RBI Resident",
            birth_date="1980-01-01",
        )
        self.assertFalse(bool(rbi_profile.philsys_id_photo))
        self.assertFalse(bool(rbi_profile.secondary_id_photo))
        self.assertFalse(bool(rbi_profile.utility_billing_photo))

        self.client.force_authenticate(user=rbi_user)
        first_proof = create_test_image("rbi_first_proof.png")

        response = self.client.patch(
            "/api/v1/auth/me/",
            {
                "secondary_id_type": "Driver's License",
                "secondary_id_photo": first_proof,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rbi_profile.refresh_from_db()
        self.assertTrue(bool(rbi_profile.secondary_id_photo))
        self.assertEqual(rbi_profile.secondary_id_type, "Driver's License")

    def test_rbi_imported_resident_zero_proofs_ordinary_profile_update_succeeds(self):
        """Ordinary profile fields can be updated for a resident with 0 proofs without error."""
        rbi_user = User.objects.create_user(
            username="rbi_no_proofs",
            password="SecurePassword123!",
            role=User.Role.RESIDENT,
            barangay=self.barangay,
        )
        rbi_profile = Resident.objects.create(
            user=rbi_user,
            full_name="Original Name",
            birth_date="1985-05-05",
            contact_number="09111111111",
        )

        self.client.force_authenticate(user=rbi_user)
        response = self.client.patch(
            "/api/v1/auth/me/",
            {
                "profile": {
                    "full_name": "Updated RBI Name",
                    "contact_number": "09222222222",
                    "birth_date": "1990-10-10",
                    "voter_status": True,
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rbi_profile.refresh_from_db()
        self.assertEqual(rbi_profile.full_name, "Updated RBI Name")
        self.assertEqual(rbi_profile.contact_number, "09222222222")
        self.assertEqual(str(rbi_profile.birth_date), "1990-10-10")
        self.assertTrue(rbi_profile.voter_status)
        self.assertFalse(bool(rbi_profile.philsys_id_photo))

    def test_invalid_file_upload_rejected_without_modifying_existing_evidence(self):
        """Uploading a non-image file is rejected and leaves existing evidence untouched."""
        self.client.force_authenticate(user=self.user)
        initial_file_name = self.resident.philsys_id_photo.name
        initial_file_content = self.resident.philsys_id_photo.read()

        invalid_file = SimpleUploadedFile(
            "bad_upload.png",
            b"not a valid image format at all",
            content_type="image/png",
        )

        response = self.client.patch(
            "/api/v1/auth/me/",
            {"philsys_id_photo": invalid_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.resident.refresh_from_db()
        self.assertEqual(self.resident.philsys_id_photo.name, initial_file_name)
        self.assertEqual(self.resident.philsys_id_photo.read(), initial_file_content)

    def test_evidence_update_does_not_alter_is_verified(self):
        """Updating or replacing evidence never changes the resident's is_verified status."""
        self.client.force_authenticate(user=self.user)
        self.assertFalse(self.resident.is_verified)

        new_image = create_test_image("new_philsys.png")
        response = self.client.patch(
            "/api/v1/auth/me/",
            {
                "philsys_id_photo": new_image,
                "is_verified": True,
                "profile.is_verified": True,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resident.refresh_from_db()
        self.assertFalse(self.resident.is_verified)

        # For an already verified resident, updating evidence preserves is_verified=True
        self.other_resident.refresh_from_db()
        self.assertTrue(self.other_resident.is_verified)
        self.client.force_authenticate(user=self.other_user)

        second_proof = create_test_image("other_billing.png")
        response = self.client.patch(
            "/api/v1/auth/me/",
            {
                "utility_billing_type": "Internet / Telecom",
                "utility_billing_photo": second_proof,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.other_resident.refresh_from_db()
        self.assertTrue(self.other_resident.is_verified)

    def test_resident_cannot_access_or_modify_another_residents_evidence(self):
        """A resident cannot access another resident's private media or alter another resident's profile."""
        self.client.force_authenticate(user=self.user)

        # 1. Private media access
        url = reverse(
            "resident_private_media",
            kwargs={
                "resident_id": self.other_resident.pk,
                "field_name": "secondary_id_photo",
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # 2. Patching /auth/me/ only mutates the authenticated user
        other_initial_name = self.other_resident.full_name
        response = self.client.patch(
            "/api/v1/auth/me/",
            {
                "id": self.other_user.id,
                "profile": {
                    "id": self.other_resident.id,
                    "full_name": "Malicious Modification",
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.other_resident.refresh_from_db()
        self.assertEqual(self.other_resident.full_name, other_initial_name)

        self.resident.refresh_from_db()
        self.assertEqual(self.resident.full_name, "Malicious Modification")

    def test_replacing_private_evidence_cleans_up_old_file_post_commit(self):
        old_file_name = self.resident.philsys_id_photo.name
        self.assertTrue(default_storage.exists(old_file_name))

        self.client.force_authenticate(user=self.user)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                "/api/v1/auth/me/",
                {
                    "remove_philsys_id_photo": "true",
                    "utility_billing_type": "Water Utility",
                    "utility_billing_photo": create_test_image("new_billing.png"),
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(default_storage.exists(old_file_name))
