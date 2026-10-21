from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AidRequestViewSet,
    DocumentRequestViewSet,
    QueueTicketViewSet,
    DashboardSummaryView,
    PublicQueueStatusView,
    PaymentRecipientViewSet,
)
from .kiosk import KioskDocumentRequestView, KioskIssueReportView, KioskQueueTicketView

router = DefaultRouter()
router.register(r'document-requests', DocumentRequestViewSet, basename='document-request')
router.register(r'aid-requests', AidRequestViewSet, basename='aid-request')
router.register(r'tickets', QueueTicketViewSet, basename='ticket')
router.register(r'payment-recipients', PaymentRecipientViewSet, basename='payment-recipient')

urlpatterns = [
    path('kiosk/queue/', KioskQueueTicketView.as_view(), name='kiosk-queue-ticket'),
    path('kiosk/documents/', KioskDocumentRequestView.as_view(), name='kiosk-document-request'),
    path('kiosk/reports/', KioskIssueReportView.as_view(), name='kiosk-issue-report'),
    path(
        'documents/<int:pk>/payment-proof/',
        DocumentRequestViewSet.as_view({'get': 'payment_proof'}),
        name='document-payment-proof-alias',
    ),
    path('', include(router.urls)),
    path('public/barangays/<int:barangay_id>/queue-status/', PublicQueueStatusView.as_view(), name='public-queue-status'),
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
]
