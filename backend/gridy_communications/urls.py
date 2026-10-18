from django.urls import path, include
from rest_framework.routers import DefaultRouter
from gridy_communications.views import (
    AnnouncementViewSet,
    PublicAnnouncementListView,
    PublicAnnouncementDetailView,
    ActivityScheduleViewSet, 
    FCMDeviceViewSet, 
    EmergencyHotlineViewSet,
    FAQViewSet,
    AdminNotificationViewSet,
    ResidentNotificationViewSet,
)

router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'activities', ActivityScheduleViewSet, basename='activity')
router.register(r'devices', FCMDeviceViewSet, basename='fcm-device')
router.register(r'hotlines', EmergencyHotlineViewSet, basename='hotline')
router.register(r'faqs', FAQViewSet, basename='faq')
router.register(r'admin-notifications', AdminNotificationViewSet, basename='admin-notification')
router.register(
    r'resident-notifications',
    ResidentNotificationViewSet,
    basename='resident-notification',
)

urlpatterns = [
    path('', include(router.urls)),
    path(
        'public/barangays/<int:barangay_id>/announcements/',
        PublicAnnouncementListView.as_view(),
        name='public-announcements',
    ),
    path(
        'public/announcements/<int:announcement_id>/',
        PublicAnnouncementDetailView.as_view(),
        name='public-announcement-detail',
    ),
]
