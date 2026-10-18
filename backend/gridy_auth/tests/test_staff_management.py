import pytest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.test import APIClient
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from gridy_audit.models import AuditLog
from gridy_auth.models import Barangay, RefreshSession

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def barangay_a(db):
    return Barangay.objects.create(
        name="Barangay San Isidro",
        municipality="Lucena City",
        province="Quezon",
    )


@pytest.fixture
def barangay_b(db):
    return Barangay.objects.create(
        name="Barangay San Antonio",
        municipality="Lucena City",
        province="Quezon",
    )


@pytest.fixture
def admin_a(db, barangay_a):
    user = User.objects.create_user(
        username="admin_isidro",
        email="admin.isidro@example.com",
        password="AdminPassword123!",
        role=User.Role.ADMIN,
        barangay=barangay_a,
        is_staff=True,
    )
    return user


@pytest.fixture
def admin_b(db, barangay_b):
    user = User.objects.create_user(
        username="admin_antonio",
        email="admin.antonio@example.com",
        password="AdminPassword123!",
        role=User.Role.ADMIN,
        barangay=barangay_b,
        is_staff=True,
    )
    return user


@pytest.fixture
def resident_a(db, barangay_a):
    user = User.objects.create_user(
        username="resident_isidro",
        email="resident.isidro@example.com",
        password="ResidentPassword123!",
        role=User.Role.RESIDENT,
        barangay=barangay_a,
        is_staff=False,
    )
    return user


@pytest.fixture
def field_official_a(db, barangay_a):
    user = User.objects.create_user(
        username="tanod_isidro_1",
        email="tanod1.isidro@example.com",
        first_name="Juan",
        last_name="Dela Cruz",
        password="FieldOfficial123!",
        role=User.Role.FIELD_OFFICIAL,
        barangay=barangay_a,
        is_staff=False,
        is_active=True,
    )
    return user


@pytest.fixture
def field_official_b(db, barangay_b):
    user = User.objects.create_user(
        username="tanod_antonio_1",
        email="tanod1.antonio@example.com",
        first_name="Pedro",
        last_name="Penduko",
        password="FieldOfficial123!",
        role=User.Role.FIELD_OFFICIAL,
        barangay=barangay_b,
        is_staff=False,
        is_active=True,
    )
    return user


@pytest.mark.django_db
class TestStaffManagementPermissions:
    def test_anonymous_caller_receives_401(self, api_client):
        response = api_client.get("/api/v1/auth/staff/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        update_response = api_client.patch(
            "/api/v1/auth/staff/1/",
            {"first_name": "Changed"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_resident_caller_receives_403(self, api_client, resident_a):
        api_client.force_authenticate(user=resident_a)
        response = api_client.get("/api/v1/auth/staff/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        update_response = api_client.patch(
            "/api/v1/auth/staff/1/",
            {"first_name": "Changed"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_403_FORBIDDEN

    def test_field_official_caller_receives_403(self, api_client, field_official_a):
        api_client.force_authenticate(user=field_official_a)
        response = api_client.get("/api/v1/auth/staff/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        update_response = api_client.patch(
            f"/api/v1/auth/staff/{field_official_a.id}/",
            {"first_name": "Changed"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_without_barangay_receives_403(self, api_client):
        unassigned_admin = User.objects.create_user(
            username="unassigned_admin",
            email="unassigned@example.com",
            password="AdminPassword123!",
            role=User.Role.ADMIN,
            barangay=None,
        )
        api_client.force_authenticate(user=unassigned_admin)
        response = api_client.get("/api/v1/auth/staff/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Create attempt fails with 403
        create_resp = api_client.post(
            "/api/v1/auth/staff/",
            {
                "username": "tanod_new",
                "email": "tanod@example.com",
                "first_name": "Test",
                "last_name": "Tanod",
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_403_FORBIDDEN

    def test_dilg_admin_cannot_manage_field_staff(self, api_client):
        dilg_admin = User.objects.create_user(
            username="dilg_admin_staff_test",
            email="dilg.staff.test@example.com",
            password="AdminPassword123!",
            role="DILG_ADMIN",
            barangay=None,
            is_staff=True,
        )
        api_client.force_authenticate(user=dilg_admin)

        assert api_client.get("/api/v1/auth/staff/").status_code == status.HTTP_403_FORBIDDEN
        response = api_client.post(
            "/api/v1/auth/staff/",
            {
                "username": "dilg_created_staff",
                "email": "staff@example.com",
                "first_name": "Dilg",
                "last_name": "Created",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestStaffManagementEndpoints:
    def test_admin_can_list_staff_for_own_barangay_strictly(
        self, api_client, admin_a, field_official_a, field_official_b, resident_a
    ):
        api_client.force_authenticate(user=admin_a)
        response = api_client.get("/api/v1/auth/staff/")
        assert response.status_code == status.HTTP_200_OK

        results = response.data.get("results", response.data)
        assert len(results) == 1
        record = results[0]
        assert record["id"] == field_official_a.id
        assert record["username"] == "tanod_isidro_1"
        assert record["role"] == User.Role.FIELD_OFFICIAL
        assert record["full_name"] == "Juan Dela Cruz"
        assert record["is_active"] is True

        # Ensure no cross-tenant leakage or resident inclusion
        returned_ids = [r["id"] for r in results]
        assert field_official_b.id not in returned_ids
        assert resident_a.id not in returned_ids
        assert admin_a.id not in returned_ids

    @pytest.mark.django_db(transaction=True)
    @patch("gridy_auth.views.staff.send_field_official_setup_email", create=True)
    def test_admin_can_create_field_official_with_private_setup_link(
        self, send_setup_email, api_client, admin_a, barangay_a
    ):
        api_client.force_authenticate(user=admin_a)
        payload = {
            "username": "tanod_carding",
            "email": "carding@isidro.example.gov.ph",
            "first_name": "Ricardo",
            "last_name": "Dalisay",
        }
        response = api_client.post("/api/v1/auth/staff/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["username"] == "tanod_carding"
        assert response.data["email"] == "carding@isidro.example.gov.ph"
        assert response.data["full_name"] == "Ricardo Dalisay"
        assert response.data["role"] == User.Role.FIELD_OFFICIAL
        assert response.data["is_active"] is True

        # Verify database record
        created_user = User.objects.get(username="tanod_carding")
        assert created_user.barangay_id == barangay_a.id
        assert created_user.role == User.Role.FIELD_OFFICIAL
        assert created_user.is_staff is False
        assert created_user.is_active is True
        assert created_user.has_usable_password() is False

        send_setup_email.delay.assert_called_once()
        recipient, full_name, barangay_name, setup_link = send_setup_email.delay.call_args.args
        assert recipient == created_user.email
        assert full_name == "Ricardo Dalisay"
        assert barangay_name == barangay_a.name
        query = parse_qs(urlparse(setup_link).query)
        uidb64 = query["uidb64"][0]
        token = query["token"][0]
        assert force_str(urlsafe_base64_decode(uidb64)) == str(created_user.pk)
        assert default_token_generator.check_token(created_user, token)
        assert token not in response.content.decode()
        assert "password" not in response.data

        # Verify audit log was written
        audit = AuditLog.objects.filter(
            action_by=admin_a,
            action_type=AuditLog.ActionType.USER_ACTION,
        ).latest("timestamp")
        assert "tanod_carding" in audit.description
        assert barangay_a.name in audit.description

    def test_disallowed_extra_fields_are_rejected(self, api_client, admin_a, barangay_b):
        api_client.force_authenticate(user=admin_a)
        payload = {
            "username": "tanod_hacker",
            "email": "hacker@example.com",
            "first_name": "Malicious",
            "last_name": "Actor",
            "password": "SecurePassword2026!",
            "role": User.Role.ADMIN,  # Disallowed
            "barangay": barangay_b.id,
            "barangay_id": barangay_b.id,  # Disallowed
            "is_staff": True,  # Disallowed
            "is_superuser": True,  # Disallowed
        }
        response = api_client.post("/api/v1/auth/staff/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Disallowed fields" in str(response.data)

    def test_duplicate_username_rejected(self, api_client, admin_a, field_official_a):
        api_client.force_authenticate(user=admin_a)
        payload = {
            "username": field_official_a.username,  # Duplicate
            "email": "unique.email@example.com",
            "first_name": "Duplicate",
            "last_name": "User",
        }
        response = api_client.post("/api/v1/auth/staff/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in response.data

    def test_duplicate_email_rejected(self, api_client, admin_a, field_official_a):
        api_client.force_authenticate(user=admin_a)
        payload = {
            "username": "unique_username",
            "email": field_official_a.email.upper(),  # Case-insensitive duplicate
            "first_name": "Duplicate",
            "last_name": "Email",
        }
        response = api_client.post("/api/v1/auth/staff/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_password_field_is_rejected_from_staff_creation_payload(self, api_client, admin_a):
        api_client.force_authenticate(user=admin_a)
        payload = {
            "username": "tanod_weak",
            "email": "field@example.com",
            "first_name": "Field",
            "last_name": "Staff",
            "password": "AdminProvidedPassword123!",
        }
        response = api_client.post("/api/v1/auth/staff/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Disallowed fields" in str(response.data)

    def test_admin_can_toggle_staff_active_status_and_revokes_sessions(
        self, api_client, admin_a, field_official_a
    ):
        # Create an active refresh session for the field official
        session = RefreshSession.objects.create(
            user=field_official_a,
            refresh_token_jti="test-jti-12345",
            ip_address="127.0.0.1",
            user_agent="FieldApp/1.0",
            expires_at="2099-01-01T00:00:00Z",
            is_revoked=False,
        )

        api_client.force_authenticate(user=admin_a)
        toggle_url = f"/api/v1/auth/staff/{field_official_a.id}/toggle-status/"

        # 1. Deactivate
        response = api_client.post(toggle_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_active"] is False

        field_official_a.refresh_from_db()
        assert field_official_a.is_active is False

        # Session must be revoked immediately
        session.refresh_from_db()
        assert session.is_revoked is True

        # Audit log verification
        audit = AuditLog.objects.filter(
            action_by=admin_a,
            action_type=AuditLog.ActionType.USER_ACTION,
        ).latest("timestamp")
        assert "deactivated" in audit.description
        assert field_official_a.username in audit.description

        # 2. Reactivate
        response_reactivate = api_client.post(toggle_url)
        assert response_reactivate.status_code == status.HTTP_200_OK
        assert response_reactivate.data["is_active"] is True

        field_official_a.refresh_from_db()
        assert field_official_a.is_active is True

    def test_admin_cannot_toggle_staff_from_another_barangay(
        self, api_client, admin_a, field_official_b
    ):
        api_client.force_authenticate(user=admin_a)
        toggle_url = f"/api/v1/auth/staff/{field_official_b.id}/toggle-status/"
        response = api_client.post(toggle_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_cannot_toggle_residents_or_admins_via_staff_endpoint(
        self, api_client, admin_a, resident_a
    ):
        api_client.force_authenticate(user=admin_a)
        toggle_url = f"/api/v1/auth/staff/{resident_a.id}/toggle-status/"
        response = api_client.post(toggle_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_can_update_same_barangay_staff_profile_and_audit_field_names_only(
        self, api_client, admin_a, field_official_a
    ):
        api_client.force_authenticate(user=admin_a)
        response = api_client.patch(
            f"/api/v1/auth/staff/{field_official_a.id}/",
            {
                "first_name": "Maria",
                "last_name": "Santos",
                "email": "MARIA.SANTOS@EXAMPLE.COM",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Maria"
        assert response.data["last_name"] == "Santos"
        assert response.data["email"] == "maria.santos@example.com"
        assert response.data["username"] == field_official_a.username
        assert response.data["role"] == User.Role.FIELD_OFFICIAL

        field_official_a.refresh_from_db()
        assert field_official_a.first_name == "Maria"
        assert field_official_a.last_name == "Santos"
        assert field_official_a.email == "maria.santos@example.com"
        assert field_official_a.barangay_id == admin_a.barangay_id

        audit = AuditLog.objects.filter(
            action_by=admin_a,
            action_type=AuditLog.ActionType.USER_ACTION,
        ).latest("timestamp")
        assert field_official_a.username in audit.description
        assert "first_name" in audit.description
        assert "last_name" in audit.description
        assert "email" in audit.description
        assert "Maria" not in audit.description
        assert "Santos" not in audit.description
        assert "maria.santos@example.com" not in audit.description

    def test_admin_can_retain_staff_member_own_email_case_insensitively(
        self, api_client, admin_a, field_official_a
    ):
        api_client.force_authenticate(user=admin_a)
        response = api_client.patch(
            f"/api/v1/auth/staff/{field_official_a.id}/",
            {"email": field_official_a.email.upper()},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == field_official_a.email.lower()

    def test_admin_can_replace_full_editable_profile_with_put(self, api_client, admin_a, field_official_a):
        api_client.force_authenticate(user=admin_a)
        response = api_client.put(
            f"/api/v1/auth/staff/{field_official_a.id}/",
            {
                "first_name": "Updated",
                "last_name": "Official",
                "email": "updated.official@example.com",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Updated"
        assert response.data["last_name"] == "Official"
        assert response.data["email"] == "updated.official@example.com"

    def test_admin_cannot_update_staff_with_duplicate_email(
        self, api_client, admin_a, field_official_a, field_official_b
    ):
        api_client.force_authenticate(user=admin_a)
        response = api_client.patch(
            f"/api/v1/auth/staff/{field_official_a.id}/",
            {"email": field_official_b.email.upper()},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_staff_update_rejects_empty_or_invalid_values(self, api_client, admin_a, field_official_a):
        api_client.force_authenticate(user=admin_a)
        url = f"/api/v1/auth/staff/{field_official_a.id}/"

        empty_response = api_client.patch(url, {}, format="json")
        blank_name_response = api_client.patch(url, {"first_name": "   "}, format="json")
        invalid_email_response = api_client.patch(url, {"email": "not-an-email"}, format="json")

        assert empty_response.status_code == status.HTTP_400_BAD_REQUEST
        assert blank_name_response.status_code == status.HTTP_400_BAD_REQUEST
        assert invalid_email_response.status_code == status.HTTP_400_BAD_REQUEST

        # PUT is a full replacement and therefore requires every editable field.
        incomplete_put = api_client.put(
            url,
            {"first_name": "Replacement"},
            format="json",
        )
        assert incomplete_put.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize(
        "field,value",
        [
            ("username", "new_username"),
            ("role", User.Role.ADMIN),
            ("barangay", 999),
            ("barangay_id", 999),
            ("is_staff", True),
            ("is_superuser", True),
            ("password", "NewPassword123!"),
        ],
    )
    def test_staff_update_rejects_identity_tenant_and_security_fields(
        self, api_client, admin_a, field_official_a, field, value
    ):
        api_client.force_authenticate(user=admin_a)
        response = api_client.patch(
            f"/api/v1/auth/staff/{field_official_a.id}/",
            {"first_name": "Allowed", field: value},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Disallowed fields" in str(response.data)

    def test_admin_cannot_edit_staff_from_another_barangay_or_other_role(
        self, api_client, admin_a, field_official_b, resident_a
    ):
        api_client.force_authenticate(user=admin_a)
        cross_barangay = api_client.patch(
            f"/api/v1/auth/staff/{field_official_b.id}/",
            {"first_name": "Intruded"},
            format="json",
        )
        wrong_role = api_client.patch(
            f"/api/v1/auth/staff/{resident_a.id}/",
            {"first_name": "Intruded"},
            format="json",
        )

        assert cross_barangay.status_code == status.HTTP_404_NOT_FOUND
        assert wrong_role.status_code == status.HTTP_404_NOT_FOUND

    def test_staff_management_does_not_expose_hard_delete(self, api_client, admin_a, field_official_a):
        api_client.force_authenticate(user=admin_a)
        response = api_client.delete(f"/api/v1/auth/staff/{field_official_a.id}/")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
