from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AidRequestViewSet,
    EquipmentBorrowRequestViewSet,
    DocumentRequestViewSet,
    QueueTicketViewSet,
    DashboardSummaryView,
    AccomplishmentReportView,
    AccomplishmentReportExportView,
    PublicQueueStatusView,
    PaymentRecipientViewSet,
    DocumentServiceOfferingViewSet,
    OfficialReceiptSeriesView,
)
from .views.certificate_verification import PublicCertificateVerificationView
from .kiosk import KioskDocumentRequestView, KioskIssueReportView, KioskQueueTicketView

router = DefaultRouter()
router.register(r'document-requests', DocumentRequestViewSet, basename='document-request')
router.register(r'document-catalog', DocumentServiceOfferingViewSet, basename='document-catalog')
router.register(r'aid-requests', AidRequestViewSet, basename='aid-request')
router.register(r'equipment-requests', EquipmentBorrowRequestViewSet, basename='equipment-request')
router.register(r'tickets', QueueTicketViewSet, basename='ticket')
router.register(r'payment-recipients', PaymentRecipientViewSet, basename='payment-recipient')

urlpatterns = [
    path('official-receipt-series/', OfficialReceiptSeriesView.as_view(), name='official-receipt-series'),
    path(
        'public/certificate-verifications/<uuid:token>/',
        PublicCertificateVerificationView.as_view(),
        name='public-certificate-verification',
    ),
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
    path(
        'dashboard/accomplishment-report/',
        AccomplishmentReportView.as_view(),
        name='dashboard-accomplishment-report',
    ),
    path(
        'dashboard/accomplishment-report/export/',
        AccomplishmentReportExportView.as_view(),
        name='dashboard-accomplishment-report-export',
    ),
]
