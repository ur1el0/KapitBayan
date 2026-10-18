from rest_framework import serializers
from gridy_auth.models import User
from ..fee_policy import enforce_fee_policy
from ..models import DocumentRequest


class FeePolicyValidationMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        document_type = attrs.get("document_type")

        if document_type is None and self.instance is not None:
            document_type = self.instance.document_type

        return enforce_fee_policy(document_type, attrs)


class DocumentRequestSerializer(FeePolicyValidationMixin, serializers.ModelSerializer):
    request_id = serializers.IntegerField(source='id', read_only=True)
    requester_name = serializers.SerializerMethodField()
    purok = serializers.SerializerMethodField()
    payment_recipient = serializers.SerializerMethodField()
    payment_recipient_name_snapshot = serializers.SerializerMethodField()
    payment_recipient_identifier_snapshot = serializers.SerializerMethodField()
    payment_instructions_snapshot = serializers.SerializerMethodField()
    payment_proof_url = serializers.SerializerMethodField()
    payment_transacted_at = serializers.DateTimeField(read_only=True)
    fee_assessed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DocumentRequest
        fields = [
            'id',
            'request_id',
            'requester_name',
            'purok',
            'is_walkin',
            'walkin_name',
            'walkin_purok',
            'document_type',
            'purpose',
            'urgency_tag',
            'status',
            'admin_notes',
            'or_number',
            'fee_amount',
            'fee_assessment_status',
            'fee_assessed_at',
            'fee_waiver_reason',
            'fee_assessed_by_name',
            'payment_method',
            'payment_recipient',
            'payment_recipient_name_snapshot',
            'payment_recipient_identifier_snapshot',
            'payment_instructions_snapshot',
            'payment_reference',
            'payment_status',
            'payment_review_note',
            'payment_proof_url',
            'payment_transacted_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'is_walkin',
            'status',
            'admin_notes',
            'or_number',
            'fee_amount',
            'fee_assessment_status',
            'fee_assessed_at',
            'fee_waiver_reason',
            'fee_assessed_by_name',
            'payment_method',
            'payment_recipient',
            'payment_recipient_name_snapshot',
            'payment_recipient_identifier_snapshot',
            'payment_instructions_snapshot',
            'payment_reference',
            'payment_status',
            'payment_review_note',
            'payment_proof_url',
            'payment_transacted_at',
            'created_at',
            'updated_at',
        ]

    def get_requester_name(self, obj) -> str:
        if obj.user:
            return getattr(obj.user.profile, 'full_name', obj.user.username) if hasattr(obj.user,'profile') else obj.user.username
        return obj.walkin_name if obj.walkin_name else "Walk-in Resident"

    def get_purok(self, obj) -> str:
        if obj.user and hasattr(obj.user, 'profile') and obj.user.profile.purok:
            return str(obj.user.profile.purok)
        return str(obj.walkin_purok) if obj.walkin_purok else "N/A"

    def get_fee_assessed_by_name(self, obj) -> str | None:
        if not obj.fee_assessed_by:
            return None
        profile = getattr(obj.fee_assessed_by, 'profile', None)
        full_name = getattr(profile, 'full_name', None)
        return full_name if full_name else obj.fee_assessed_by.username

    def _can_view_payment_recipient_snapshot(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return bool(
            user
            and user.is_authenticated
            and user.barangay_id == obj.barangay_id
        )

    def get_payment_recipient(self, obj) -> int | None:
        return obj.payment_recipient_id if self._can_view_payment_recipient_snapshot(obj) else None

    def get_payment_recipient_name_snapshot(self, obj) -> str | None:
        return obj.payment_recipient_name_snapshot if self._can_view_payment_recipient_snapshot(obj) else None

    def get_payment_recipient_identifier_snapshot(self, obj) -> str | None:
        return obj.payment_recipient_identifier_snapshot if self._can_view_payment_recipient_snapshot(obj) else None

    def get_payment_instructions_snapshot(self, obj) -> str | None:
        return obj.payment_instructions_snapshot if self._can_view_payment_recipient_snapshot(obj) else None

    def get_payment_proof_url(self, obj) -> str | None:
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return None
        if not obj.payment_proof_image or not obj.payment_proof_image.name:
            return None
        user = request.user
        doc_barangay_id = obj.barangay_id or (obj.user.barangay_id if obj.user else None)
        is_owner = bool(obj.user_id is not None and user.id == obj.user_id)
        is_same_barangay_staff = bool(
            user.role in (User.Role.ADMIN, User.Role.FIELD_OFFICIAL)
            and user.barangay_id is not None
            and doc_barangay_id is not None
            and user.barangay_id == doc_barangay_id
        )
        if is_owner or is_same_barangay_staff:
            return f"/api/v1/document-requests/{obj.id}/payment-proof/"
        return None


class DocumentRequestReviewSerializer(FeePolicyValidationMixin, serializers.ModelSerializer):
    fee_waiver_reason = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    fee_assessment_status = serializers.ChoiceField(
        choices=DocumentRequest.FeeAssessmentStatus.choices,
        required=False,
        read_only=True,
    )

    class Meta:
        model = DocumentRequest
        fields = [
            "status",
            "admin_notes",
            "or_number",
            "fee_amount",
            "payment_method",
            "fee_waiver_reason",
            "fee_assessment_status",
        ]

    def validate_status(self, value):
        allowed_statuses = {
            DocumentRequest.Status.PROCESSING,
            DocumentRequest.Status.READY_FOR_PICKUP,
            DocumentRequest.Status.RELEASED,
            DocumentRequest.Status.REJECTED,
        }
        if value not in allowed_statuses:
            raise serializers.ValidationError("Invalid status transition")

        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        document_status = attrs.get(
            "status",
            self.instance.status if self.instance is not None else None,
        )
        fee_amount = attrs.get(
            "fee_amount",
            self.instance.fee_amount if self.instance is not None else 0,
        )
        or_number = attrs.get(
            "or_number",
            self.instance.or_number if self.instance is not None else None,
        )
        if (
            document_status == DocumentRequest.Status.RELEASED
            and fee_amount > 0
            and not (or_number or "").strip()
        ):
            raise serializers.ValidationError({
                "or_number": (
                    "An Official Receipt (O.R.) number is required before releasing a document with a fee."
                )
            })
        return attrs
