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
    BarangayApplicationViewSet,
    PublicBarangayDirectoryView,
    StaffManagementViewSet,
    DILGAccountSupportViewSet,
)
from .views.resident_media import ResidentPrivateMediaView

router = DefaultRouter()
router.register(r'resident', ResidentViewSet, basename='resident')
router.register(r'barangay', BarangayViewSet, basename='barangay')
router.register(r"sessions", SessionViewSet, basename="session")
router.register(r"barangay-applications", BarangayApplicationViewSet, basename="barangay-application")
router.register(r"staff", StaffManagementViewSet, basename="staff")
router.register(r"dilg/accounts", DILGAccountSupportViewSet, basename="dilg-account-support")


urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('public/barangays/', PublicBarangayDirectoryView.as_view(), name='public-barangay-list'),
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
