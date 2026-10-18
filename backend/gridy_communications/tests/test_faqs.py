from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from gridy_auth.models import Barangay, User
from gridy_communications.models import FAQ


class FAQAPITests(APITestCase):
    def setUp(self):
        self.barangay_a = Barangay.objects.create(name="Barangay Test A")
        self.barangay_b = Barangay.objects.create(name="Barangay Test B")
        self.legacy_platform_user = User.objects.create_user(
            username="legacy_platform_faq",
            password="SecurePassword123!",
            email="legacy_platform@example.com",
            role="DILG_ADMIN",
            is_active=True,
        )
        self.admin_a = User.objects.create_user(
            username="brgy_admin_faq_a",
            password="SecurePassword123!",
            email="brgy_admin_a@example.com",
            role=User.Role.ADMIN,
            barangay=self.barangay_a,
            is_active=True,
        )
        self.admin_b = User.objects.create_user(
            username="brgy_admin_faq_b",
            password="SecurePassword123!",
            email="brgy_admin_b@example.com",
            role=User.Role.ADMIN,
            barangay=self.barangay_b,
            is_active=True,
        )
        self.resident_a = User.objects.create_user(
            username="resident_faq_a",
            password="SecurePassword123!",
            email="resident_a@example.com",
            role=User.Role.RESIDENT,
            barangay=self.barangay_a,
            is_active=True,
        )
        self.resident_b = User.objects.create_user(
            username="resident_faq_b",
            password="SecurePassword123!",
            email="resident_b@example.com",
            role=User.Role.RESIDENT,
            barangay=self.barangay_b,
            is_active=True,
        )
        self.field_official_a = User.objects.create_user(
            username="field_faq_a",
            password="SecurePassword123!",
            email="field_a@example.com",
            role=User.Role.FIELD_OFFICIAL,
            barangay=self.barangay_a,
            is_active=True,
        )

        self.global_resident = FAQ.objects.create(
            question="Global resident help?",
            answer="A general answer.",
            audience=FAQ.Audience.RESIDENT,
            category=FAQ.Category.GETTING_STARTED,
            is_published=True,
        )
        self.local_resident_a = FAQ.objects.create(
            question="How does Barangay A help?",
            answer="Ask the Barangay A desk.",
            audience=FAQ.Audience.RESIDENT,
            category=FAQ.Category.ASSISTANCE,
            is_published=True,
            barangay=self.barangay_a,
        )
        self.local_draft_a = FAQ.objects.create(
            question="Draft for Barangay A?",
            answer="Not published yet.",
            audience=FAQ.Audience.RESIDENT,
            category=FAQ.Category.OTHER,
            is_published=False,
            barangay=self.barangay_a,
        )
        self.local_resident_b = FAQ.objects.create(
            question="Private Barangay B guidance?",
            answer="Only Barangay B residents should see this.",
            audience=FAQ.Audience.RESIDENT,
            category=FAQ.Category.ASSISTANCE,
            is_published=True,
            barangay=self.barangay_b,
        )
        self.global_staff = FAQ.objects.create(
            question="Staff handling guidance?",
            answer="Internal staff answer.",
            audience=FAQ.Audience.STAFF,
            category=FAQ.Category.OTHER,
            is_published=True,
        )
        self.local_staff_a = FAQ.objects.create(
            question="Barangay A staff guidance?",
            answer="Internal Barangay A guidance.",
            audience=FAQ.Audience.STAFF,
            category=FAQ.Category.OTHER,
            is_published=True,
            barangay=self.barangay_a,
        )
        # This models an existing FAQ row before the audience/publication migration.
        self.legacy_faq = FAQ.objects.create(
            question="Legacy staff FAQ?",
            answer="Existing staff-only guidance.",
        )
        self.list_url = reverse("faq-list")

    @staticmethod
    def _results(response):
        return response.data.get("results", response.data) if isinstance(response.data, dict) else response.data

    def test_resident_sees_only_published_resident_faqs_from_own_barangay(self):
        self.client.force_login(self.resident_a)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        questions = {item["question"] for item in self._results(response)}
        self.assertEqual(
            questions,
            {"How does Barangay A help?"},
        )
        self.assertNotIn("Global resident help?", questions)
        self.assertNotIn("Private Barangay B guidance?", questions)
        self.assertNotIn("Draft for Barangay A?", questions)
        self.assertNotIn("Staff handling guidance?", questions)

    def test_resident_cannot_retrieve_draft_staff_or_other_barangay_faq(self):
        self.client.force_login(self.resident_a)
        for faq in (self.local_draft_a, self.local_resident_b, self.global_staff, self.legacy_faq):
            response = self.client.get(reverse("faq-detail", kwargs={"pk": faq.pk}))
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_resident_of_other_barangay_gets_only_its_own_scope(self):
        self.client.force_login(self.resident_b)
        response = self.client.get(self.list_url)

        questions = {item["question"] for item in self._results(response)}
        self.assertEqual(
            questions,
            {"Private Barangay B guidance?"},
        )
        self.assertNotIn("Global resident help?", questions)
        self.assertNotIn("How does Barangay A help?", questions)
        self.assertNotIn("Draft for Barangay A?", questions)
        self.assertNotIn("Staff handling guidance?", questions)

    def test_unauthenticated_user_cannot_read_faqs(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_barangay_admin_can_manage_only_own_resident_faqs(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(self.list_url)
        questions = {item["question"] for item in self._results(response)}
        self.assertIn("Draft for Barangay A?", questions)
        self.assertNotIn("Global resident help?", questions)
        self.assertNotIn("Private Barangay B guidance?", questions)

        create_response = self.client.post(
            self.list_url,
            {
                "question": "Local question?",
                "answer": "Local answer.",
                "audience": FAQ.Audience.RESIDENT,
                "category": FAQ.Category.OTHER,
                "is_published": False,
                "order": 30,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        created = FAQ.objects.get(pk=create_response.data["id"])
        self.assertEqual(created.barangay_id, self.barangay_a.pk)
        self.assertEqual(created.audience, FAQ.Audience.RESIDENT)

        other_detail_url = reverse("faq-detail", kwargs={"pk": self.local_resident_b.pk})
        cross_tenant_update = self.client.patch(other_detail_url, {"answer": "Tampered."}, format="json")
        self.assertEqual(cross_tenant_update.status_code, status.HTTP_404_NOT_FOUND)
        self.local_resident_b.refresh_from_db()
        self.assertEqual(self.local_resident_b.answer, "Only Barangay B residents should see this.")

    def test_barangay_admin_cannot_create_staff_or_edit_global_faq(self):
        self.client.force_login(self.admin_a)
        create_response = self.client.post(
            self.list_url,
            {
                "question": "Staff question?",
                "answer": "Internal.",
                "audience": FAQ.Audience.STAFF,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)

        detail_url = reverse("faq-detail", kwargs={"pk": self.global_resident.pk})
        update_response = self.client.patch(detail_url, {"answer": "Changed."}, format="json")
        self.assertEqual(update_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_legacy_role_cannot_read_or_manage_global_faqs(self):
        self.client.force_authenticate(user=self.legacy_platform_user)
        create_response = self.client.post(
            self.list_url,
            {
                "question": "Global staff help?",
                "answer": "Global staff answer.",
                "audience": FAQ.Audience.RESIDENT,
                "category": FAQ.Category.OTHER,
                "is_published": True,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(FAQ.objects.filter(question="Global staff help?").exists())

        list_response = self.client.get(self.list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._results(list_response), [])

        local_url = reverse("faq-detail", kwargs={"pk": self.local_resident_a.pk})
        update_response = self.client.patch(local_url, {"answer": "Tampered."}, format="json")
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
        delete_response = self.client.delete(local_url)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)
        self.local_resident_a.refresh_from_db()
        self.assertEqual(self.local_resident_a.answer, "Ask the Barangay A desk.")
        self.assertTrue(FAQ.objects.filter(pk=self.local_resident_a.pk).exists())

    def test_field_official_reads_only_published_staff_faqs_in_scope(self):
        self.client.force_login(self.field_official_a)
        response = self.client.get(self.list_url)

        questions = {item["question"] for item in self._results(response)}
        self.assertEqual(questions, {"Barangay A staff guidance?"})

    def test_barangay_admin_b_cannot_read_barangay_a_drafts_by_id(self):
        self.client.force_login(self.admin_b)
        detail_url = reverse("faq-detail", kwargs={"pk": self.local_draft_a.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
