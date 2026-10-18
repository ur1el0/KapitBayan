from django.contrib import admin

from gridy_auth.models import BarangayApplication


@admin.register(BarangayApplication)
class BarangayApplicationAdmin(admin.ModelAdmin):
    """Preserve old application records for read-only superuser inspection."""

    list_display = (
        "id",
        "name",
        "municipality",
        "province",
        "applicant_name",
        "applicant_email",
        "status",
        "created_at",
    )
    list_filter = ("status", "province", "municipality")
    search_fields = ("name", "applicant_name", "applicant_email", "applicant_phone")
    readonly_fields = tuple(field.name for field in BarangayApplication._meta.fields)
    ordering = ("-created_at",)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
