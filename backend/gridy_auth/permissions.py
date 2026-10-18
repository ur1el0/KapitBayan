from rest_framework.permissions import BasePermission
from .models import User

class IsBarangayOfficial(BasePermission):
    """Barangay Executive Admin (Captain, Secretary, Desk Supervisor)."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.ADMIN
        )

class IsResidentOrBarangayOfficial(BasePermission):
    """Residents create personal requests; barangay admins create walk-ins."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (User.Role.RESIDENT, User.Role.ADMIN)
        )

class IsBarangayExecutive(BasePermission):
    """Strictly for Executive Admins authorized for high-privilege operations."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.ADMIN
        )

class IsFieldOfficial(BasePermission):
    """Field Personnel, Tanod, and Dispatched Inspectors."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.FIELD_OFFICIAL
        )

class IsBarangayOfficialOrField(BasePermission):
    """Both Executive Admins and Field Personnel (e.g. for queue calls and issue reports)."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in [User.Role.ADMIN, User.Role.FIELD_OFFICIAL]
        )

class IsResident(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.RESIDENT
        )


class IsDjangoSuperuser(BasePermission):
    """Limit platform-wide operational support to controlled Django superusers."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_superuser
        )
