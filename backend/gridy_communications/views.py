import logging
from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from drf_spectacular.utils import extend_schema
from gridy_auth.models import User
from gridy_auth.permissions import IsBarangayOfficial
from gridy_communications.models import (
    Announcement,
    ActivitySchedule,
    FCMDevice,
    EmergencyHotline,
    FAQ,
    AdminNotification,
    ResidentNotification,
)
from gridy_communications.serializers import (
    AnnouncementSerializer,
    PublicAnnouncementSerializer,
    ActivityScheduleSerializer,
    FCMDeviceSerializer,
    EmergencyHotlineSerializer,
    FAQSerializer,
    AdminNotificationSerializer,
    ResidentNotificationSerializer,
)
from gridy_communications.tasks import send_announcement_notification_task

logger = logging.getLogger(__name__)


class PublicAnnouncementListView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=PublicAnnouncementSerializer(many=True))
    def get(self, request, barangay_id):
        announcements = Announcement.objects.select_related("created_by").filter(
            created_by__barangay_id=barangay_id,
        ).order_by("-is_pinned", "-created_at")[:50]
        return Response(
            PublicAnnouncementSerializer(
                announcements,
                many=True,
                context={"request": request},
            ).data
        )


class PublicAnnouncementDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=PublicAnnouncementSerializer)
    def get(self, request, announcement_id):
        try:
            announcement = Announcement.objects.select_related("created_by").get(id=announcement_id)
        except Announcement.DoesNotExist:
            return Response(
                {"detail": "Announcement not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            PublicAnnouncementSerializer(
                announcement,
                context={"request": request},
            ).data
        )


class ActivityScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = ActivityScheduleSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return ActivitySchedule.objects.none()
            
        if user.role == User.Role.DILG_ADMIN:
            return ActivitySchedule.objects.all().order_by('event_datetime', 'created_at')

        if not user.barangay_id:
            return ActivitySchedule.objects.none()
            
        return ActivitySchedule.objects.filter(created_by__barangay_id=user.barangay_id).order_by('event_datetime', 'created_at')

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Anyone logged in (Resident or Official) can read
            return [permissions.IsAuthenticated()]
        # Only officials can write (create, update, delete)
        return [IsBarangayOfficial()]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.barangay_id:
            raise PermissionDenied("A barangay assignment is required to schedule activities.")
        serializer.save(created_by=user)



class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Announcement.objects.none()
            
        if user.role == User.Role.DILG_ADMIN:
            return Announcement.objects.all().order_by('-is_pinned', '-created_at')

        if not user.barangay_id:
            return Announcement.objects.none()
            
        return Announcement.objects.filter(created_by__barangay_id=user.barangay_id).order_by('-is_pinned', '-created_at')

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [IsBarangayOfficial()]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.barangay_id:
            raise PermissionDenied("A barangay assignment is required to publish announcements.")
        instance = serializer.save(created_by=user)
        try:
            # A global topic could reach residents in unrelated barangays. Fan out
            # only to opted-in residents belonging to this announcement's tenant.
            send_announcement_notification_task.delay(
                barangay_id=user.barangay_id,
                announcement_id=instance.id,
                title=instance.title,
            )
        except Exception as e:
            logger.error(
                "Announcement FCM notification failed for record %s (%s).",
                instance.id,
                type(e).__name__,
            )

class FCMDeviceViewSet(viewsets.ModelViewSet):
    serializer_class = FCMDeviceSerializer
    
    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return FCMDevice.objects.none()
            
        # Security: Everyone (even Admins) should only be able to view/manage THEIR OWN mobile devices
        return FCMDevice.objects.filter(user=user)

    # Clean up any existing records matching the token to prevent duplicate key crashes 
    def create(self, request, *args, **kwargs):
        token = request.data.get('token')
        if token:
            FCMDevice.objects.filter(token=token).delete()
        return super().create(request, *args, **kwargs)

    # Security: Force the device to belong to the logged-in user!
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class EmergencyHotlineViewSet(viewsets.ModelViewSet):
    serializer_class = EmergencyHotlineSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return EmergencyHotline.objects.none()
        
        if user.role == User.Role.DILG_ADMIN:
            return EmergencyHotline.objects.all()

        if not user.barangay_id:
            return EmergencyHotline.objects.none()
        
        # Base query: scope to the user's barangay
        qs = EmergencyHotline.objects.filter(created_by__barangay_id=user.barangay_id)

        # Security: Residents only see the active hotlines; Officials see everything (to toggle them)
        if user.role == User.Role.RESIDENT:
            qs = qs.filter(is_active=True)

        return qs

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Residents can read the hotline directory
            return [permissions.IsAuthenticated()]
        # Only Officials can manage (create, edit, delete)
        return [IsBarangayOfficial()]
    
    def perform_create(self, serializer):
        user = self.request.user
        if not user.barangay_id:
            raise PermissionDenied("A barangay assignment is required to create emergency hotlines.")
        serializer.save(created_by=user)

class FAQManagerPermission(permissions.BasePermission):
    """Barangay admins manage local resident FAQs; DILG manages global FAQs."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.role == User.Role.DILG_ADMIN
                or (user.role == User.Role.ADMIN and user.barangay_id)
            )
        )


class FAQViewSet(viewsets.ModelViewSet):
    serializer_class = FAQSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return FAQ.objects.none()

        faqs = FAQ.objects.select_related('barangay').all()
        if user.role == User.Role.DILG_ADMIN:
            return faqs.filter(barangay__isnull=True)

        in_scope = Q(barangay__isnull=True)
        if user.barangay_id:
            in_scope |= Q(barangay_id=user.barangay_id)

        if user.role == User.Role.RESIDENT:
            return faqs.filter(
                audience=FAQ.Audience.RESIDENT,
                is_published=True,
            ).filter(in_scope)

        if user.role == User.Role.ADMIN:
            local_resident_faqs = Q(
                barangay_id=user.barangay_id,
                audience=FAQ.Audience.RESIDENT,
            ) if user.barangay_id else Q(pk__in=[])
            published_global_faqs = Q(
                barangay__isnull=True,
                audience=FAQ.Audience.RESIDENT,
                is_published=True,
            )
            return faqs.filter(local_resident_faqs | published_global_faqs)

        if user.role == User.Role.FIELD_OFFICIAL:
            return faqs.filter(
                audience=FAQ.Audience.STAFF,
                is_published=True,
            ).filter(in_scope)

        return FAQ.objects.none()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [FAQManagerPermission()]

    def perform_create(self, serializer):
        user = self.request.user
        audience = serializer.validated_data.get('audience', FAQ.Audience.STAFF)
        if user.role == User.Role.ADMIN:
            if not user.barangay_id:
                raise PermissionDenied("A Barangay assignment is required to manage local FAQs.")
            if audience != FAQ.Audience.RESIDENT:
                raise PermissionDenied("Barangay admins can create resident FAQs only.")
            serializer.save(barangay_id=user.barangay_id, audience=FAQ.Audience.RESIDENT)
            return
        if user.role == User.Role.DILG_ADMIN:
            serializer.save(barangay=None)
            return
        raise PermissionDenied("You cannot manage FAQs.")

    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.instance
        audience = serializer.validated_data.get('audience', instance.audience)
        if user.role == User.Role.ADMIN:
            if instance.barangay_id != user.barangay_id or instance.audience != FAQ.Audience.RESIDENT:
                raise PermissionDenied("You can manage only resident FAQs for your Barangay.")
            if audience != FAQ.Audience.RESIDENT:
                raise PermissionDenied("Barangay admins can manage resident FAQs only.")
            serializer.save(barangay_id=user.barangay_id)
            return
        if user.role == User.Role.DILG_ADMIN:
            if instance.barangay_id is not None:
                raise PermissionDenied("DILG admins can manage global FAQs only.")
            serializer.save(barangay=None)
            return
        raise PermissionDenied("You cannot manage FAQs.")

    def perform_destroy(self, instance):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            if instance.barangay_id != user.barangay_id or instance.audience != FAQ.Audience.RESIDENT:
                raise PermissionDenied("You can manage only resident FAQs for your Barangay.")
        elif user.role == User.Role.DILG_ADMIN:
            if instance.barangay_id is not None:
                raise PermissionDenied("DILG admins can manage global FAQs only.")
        else:
            raise PermissionDenied("You cannot manage FAQs.")
        instance.delete()
    
class IsAdminNotificationRecipient(permissions.BasePermission):
    """Allow Barangay and DILG admins to access their own notifications."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role in (User.Role.ADMIN, User.Role.DILG_ADMIN)
        )


class AdminNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = AdminNotificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminNotificationRecipient]

    def get_queryset(self):
        # Keep this endpoint owner-scoped for both Barangay and DILG admins.
        return AdminNotification.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        # Custom endpoint to clear the notification bell badge
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"status": "success", "message": "All notifications marked as read."})


class ResidentNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose only the authenticated user's persisted resident alerts."""

    serializer_class = ResidentNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return ResidentNotification.objects.filter(
            user=self.request.user,
        ).order_by('-created_at', '-id')[:100]
