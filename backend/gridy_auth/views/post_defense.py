from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from gridy_audit.models import AuditLog
from gridy_audit.services import log_action
from gridy_auth.models import Barangay, LoginEvent, Resident, ResidentTransferRequest, User
from gridy_auth.serializers.post_defense import (
    LoginEventSerializer,
    ResidentTransferCreateSerializer,
    ResidentTransferRequestSerializer,
    ResidentTransferReviewSerializer,
)


def _resident_has_open_barangay_work(resident, barangay_id):
    """Keep pending services with their current Barangay until staff resolve them."""
    from gridy_services.models import DocumentRequest, QueueTicket

    tenant_scope = Q(barangay_id=barangay_id) | Q(barangay__isnull=True)
    open_documents = DocumentRequest.objects.filter(
        user=resident,
        status__in=(
            DocumentRequest.Status.PENDING,
            DocumentRequest.Status.PROCESSING,
            DocumentRequest.Status.READY_FOR_PICKUP,
        ),
    ).filter(tenant_scope)
    active_tickets = QueueTicket.objects.filter(
        user=resident,
        status__in=(QueueTicket.Status.WAITING, QueueTicket.Status.SERVING),
    ).filter(tenant_scope)
    return open_documents.exists() or active_tickets.exists()


class LoginEventListView(ListAPIView):
    """Show an account's sign-ins and, for admins, their own Field Officials' sign-ins."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LoginEventSerializer

    def get_queryset(self):
        user = self.request.user
        cutoff = timezone.now() - timedelta(days=settings.LOGIN_EVENT_RETENTION_DAYS)
        events = LoginEvent.objects.filter(created_at__gte=cutoff).select_related("user")
        if user.role == User.Role.ADMIN and user.barangay_id:
            events = events.filter(
                Q(user=user)
                | Q(user__role=User.Role.FIELD_OFFICIAL, user__barangay_id=user.barangay_id)
            )
        else:
            events = events.filter(user=user)
        return events.order_by("-created_at", "-pk")[:100]


class ResidentTransferViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """A receiving Barangay Admin reviews resident-initiated account transfers."""

    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        requests = ResidentTransferRequest.objects.select_related(
            "resident__profile", "source_barangay", "destination_barangay", "reviewed_by"
        )
        if user.role == User.Role.ADMIN and user.barangay_id:
            return requests.filter(destination_barangay_id=user.barangay_id)
        if user.role == User.Role.RESIDENT:
            return requests.filter(resident=user)
        return requests.none()

    def get_serializer_class(self):
        if self.action == "create":
            return ResidentTransferCreateSerializer
        if self.action in {"approve", "reject"}:
            return ResidentTransferReviewSerializer
        return ResidentTransferRequestSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.RESIDENT:
            raise PermissionDenied("Only residents can request an account transfer.")
        if request.user.barangay_id is None:
            raise ValidationError({"detail": "Your account has no current Barangay assignment."})
        if not hasattr(request.user, "profile"):
            raise ValidationError({"detail": "A resident profile is required to request a transfer."})
        if not request.user.profile.is_verified:
            raise PermissionDenied("Your resident account must be verified before requesting a transfer.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                source_barangay_id = request.user.barangay_id
                Barangay.objects.select_for_update().get(pk=source_barangay_id)
                locked_user = User.objects.select_for_update().get(pk=request.user.pk)
                if locked_user.barangay_id != source_barangay_id:
                    raise ValidationError({
                        "detail": "Your Barangay assignment changed. Refresh and try again."
                    })
                profile = Resident.objects.select_for_update().filter(
                    user=locked_user
                ).first()
                if profile is None or not profile.is_verified:
                    raise PermissionDenied(
                        "Your resident account must remain verified before requesting a transfer."
                    )
                if _resident_has_open_barangay_work(
                    locked_user,
                    source_barangay_id,
                ):
                    raise ValidationError({
                        "detail": (
                            "Complete or cancel your open document requests and queue tickets "
                            "with your current Barangay before requesting a transfer."
                        )
                    })
                if ResidentTransferRequest.objects.filter(
                    resident=locked_user,
                    status=ResidentTransferRequest.Status.PENDING,
                ).exists():
                    raise ValidationError({
                        "detail": "You already have a Barangay transfer request awaiting review."
                    })
                transfer = serializer.save(
                    resident=locked_user,
                    source_barangay=locked_user.barangay,
                )
                log_action(
                    user=locked_user,
                    action_type=AuditLog.ActionType.USER_ACTION,
                    description=(
                        f"Submitted a resident Barangay transfer request. Resident ID: "
                        f"{locked_user.pk}; from Barangay ID {transfer.source_barangay_id} "
                        f"to Barangay ID {transfer.destination_barangay_id}."
                    ),
                    request=request,
                )
        except User.DoesNotExist:
            raise ValidationError({"detail": "Your account could not be loaded."})
        except IntegrityError:
            raise ValidationError({
                "detail": "You already have a Barangay transfer request awaiting review."
            })

        return Response(
            ResidentTransferRequestSerializer(transfer).data,
            status=status.HTTP_201_CREATED,
        )

    def _get_pending_transfer_for_admin(self, request, pk):
        if request.user.role != User.Role.ADMIN or request.user.barangay_id is None:
            raise PermissionDenied("Only the receiving Barangay Admin can review this request.")
        return get_object_or_404(
            ResidentTransferRequest.objects.select_for_update(of=("self",)).select_related(
                "resident__profile", "source_barangay", "destination_barangay"
            ),
            pk=pk,
            destination_barangay_id=request.user.barangay_id,
            status=ResidentTransferRequest.Status.PENDING,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        review = ResidentTransferReviewSerializer(data=request.data)
        review.is_valid(raise_exception=True)
        if not review.validated_data.get("residency_confirmed"):
            raise ValidationError({
                "residency_confirmed": (
                    "Confirm that you independently verified the resident's identity and residence."
                )
            })

        with transaction.atomic():
            transfer = self._get_pending_transfer_for_admin(request, pk)
            Barangay.objects.select_for_update().get(pk=transfer.source_barangay_id)
            resident_user = User.objects.select_for_update().get(pk=transfer.resident_id)
            profile = get_object_or_404(
                Resident.objects.select_for_update(), user=resident_user
            )
            if not profile.is_verified:
                raise ValidationError({
                    "detail": "The resident's verification must remain active before transfer approval."
                })
            if resident_user.barangay_id != transfer.source_barangay_id:
                raise ValidationError({
                    "detail": "The resident's Barangay changed after this request was submitted."
                })

            if _resident_has_open_barangay_work(
                resident_user,
                transfer.source_barangay_id,
            ):
                raise ValidationError({
                    "detail": (
                        "The resident still has open document requests or queue tickets with "
                        "the source Barangay. Finish or cancel that work before approving the transfer."
                    )
                })

            # Preserve the original tenant for legacy records that predate
            # explicit Barangay snapshots before moving the account.
            from gridy_services.models import DocumentRequest, QueueTicket

            DocumentRequest.objects.filter(
                user=resident_user,
                barangay__isnull=True,
            ).update(barangay_id=transfer.source_barangay_id)
            QueueTicket.objects.filter(
                user=resident_user,
                barangay__isnull=True,
            ).update(barangay_id=transfer.source_barangay_id)

            resident_user.barangay_id = transfer.destination_barangay_id
            resident_user.save(update_fields=["barangay"])
            transfer.status = ResidentTransferRequest.Status.APPROVED
            transfer.reviewed_by = request.user
            transfer.reviewed_at = timezone.now()
            transfer.review_note = review.validated_data.get("review_note", "")
            transfer.residency_confirmed = True
            transfer.save(update_fields=[
                "status", "reviewed_by", "reviewed_at", "review_note",
                "residency_confirmed", "updated_at",
            ])
            log_action(
                user=request.user,
                action_type=AuditLog.ActionType.USER_ACTION,
                description=(
                    f"Approved a resident's Barangay transfer after independently verifying "
                    f"identity and residence. Resident ID: {resident_user.pk}; "
                    f"from Barangay ID {transfer.source_barangay_id} to "
                    f"Barangay ID {transfer.destination_barangay_id}."
                ),
                request=request,
            )

        return Response(ResidentTransferRequestSerializer(transfer).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        review = ResidentTransferReviewSerializer(data=request.data)
        review.is_valid(raise_exception=True)
        note = review.validated_data.get("review_note", "")
        if not note:
            raise ValidationError({"review_note": "Provide a reason for rejecting the transfer."})

        with transaction.atomic():
            transfer = self._get_pending_transfer_for_admin(request, pk)
            transfer.status = ResidentTransferRequest.Status.REJECTED
            transfer.reviewed_by = request.user
            transfer.reviewed_at = timezone.now()
            transfer.review_note = note
            transfer.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])
            log_action(
                user=request.user,
                action_type=AuditLog.ActionType.USER_ACTION,
                description=(
                    f"Rejected a resident's Barangay transfer request. Resident ID: "
                    f"{transfer.resident_id}; destination Barangay ID "
                    f"{transfer.destination_barangay_id}. Reason: {note}"
                ),
                request=request,
            )

        return Response(ResidentTransferRequestSerializer(transfer).data)
