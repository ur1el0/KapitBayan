from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    SessionViewSet,
    RegisterView, 
    CustomTokenObtainPairView, 
    ResidentImportView, 
    UserProfileView, 
    CustomTokenRefreshView,
    LogoutView,
    PendingResidentsView,
    VerifyResidentView,
    RejectResidentView,
    ResidentViewSet,
    BarangayViewSet,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    PublicBarangayDirectoryView,
    PublicBarangayApplicationCreateView,
    PublicBarangayApplicationEmailVerificationView,
    PublicBarangayApplicationVerificationResendView,
    PlatformBarangayApplicationProofView,
    PlatformBarangayApplicationViewSet,
    StaffManagementViewSet,
    PlatformAccountSupportViewSet,
)
from .views.resident_media import ResidentPrivateMediaView

router = DefaultRouter()
router.register(r'resident', ResidentViewSet, basename='resident')
router.register(r'barangay', BarangayViewSet, basename='barangay')
router.register(r"sessions", SessionViewSet, basename="session")
router.register(r"staff", StaffManagementViewSet, basename="staff")
router.register(r"platform/accounts", PlatformAccountSupportViewSet, basename="platform-account-support")
router.register(
    r"platform/barangay-applications",
    PlatformBarangayApplicationViewSet,
    basename="platform-barangay-application",
)


urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('public/barangays/', PublicBarangayDirectoryView.as_view(), name='public-barangay-list'),
    path(
        'public/barangay-applications/',
        PublicBarangayApplicationCreateView.as_view(),
        name='public-barangay-application-create',
    ),
    path(
        'public/barangay-applications/<int:application_id>/verify-email/',
        PublicBarangayApplicationEmailVerificationView.as_view(),
        name='public-barangay-application-verify-email',
    ),
    path(
        'public/barangay-applications/resend-verification/',
        PublicBarangayApplicationVerificationResendView.as_view(),
        name='public-barangay-application-resend-verification',
    ),
    path(
        'platform/barangay-applications/<int:application_id>/proof/',
        PlatformBarangayApplicationProofView.as_view(),
        name='platform-barangay-application-proof',
    ),
    path('login/', CustomTokenObtainPairView.as_view(), name='auth_login'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='auth_token_refresh'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('me/', UserProfileView.as_view(), name='auth_me'),
    path('import-residents/', ResidentImportView.as_view(), name='import_residents'),
    path('pending-residents/', PendingResidentsView.as_view(), name='pending_residents'),
    path('verify-resident/<int:pk>/', VerifyResidentView.as_view(), name='verify_resident'),
    path('reject-resident/<int:pk>/', RejectResidentView.as_view(), name='reject_resident'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path(
        'resident/<int:resident_id>/media/<str:field_name>/',
        ResidentPrivateMediaView.as_view(),
        name='resident_private_media',
    ),
] + router.urls
