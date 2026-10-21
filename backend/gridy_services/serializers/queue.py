from rest_framework import serializers
from gridy_auth.models import User
from ..models import DocumentRequest, QueueTicket


class QueueTicketSerializer(serializers.ModelSerializer):
    ticket_id = serializers.IntegerField(source='id', read_only=True)
    resident_name = serializers.SerializerMethodField()
    document_request_id = serializers.PrimaryKeyRelatedField(
        source='document_request',
        queryset=DocumentRequest.objects.select_related('user').all(),
        required=False,
        allow_null=True,
    )
    document_request_type = serializers.CharField(
        source='document_request.document_type',
        read_only=True,
        allow_null=True,
    )
    priority_reason = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        max_length=500,
    )

    class Meta:
        model = QueueTicket
        fields = [
            'ticket_id',
            'ticket_number',
            'resident_name',
            'walkin_name',
            'service_type',
            'document_request_id',
            'document_request_type',
            'priority_status',
            'is_priority',
            'priority_reason',
            'notes',
            'status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['status', 'ticket_number', 'created_at', 'updated_at']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get('request')
        action = getattr(self.context.get('view'), 'action', None)
        submitted = getattr(self, 'initial_data', {})
        priority_fields = {'priority_status', 'is_priority', 'priority_reason'}

        if self.instance is not None and priority_fields.intersection(submitted):
            raise serializers.ValidationError({
                'priority_status': (
                    'Use the dedicated priority endpoint to change a ticket priority.'
                )
            })

        document_request = attrs.get('document_request')
        if document_request is not None:
            user = getattr(request, 'user', None)
            user_barangay_id = getattr(user, 'barangay_id', None)
            document_barangay_id = document_request.barangay_id
            if document_barangay_id is None and document_request.user_id:
                document_barangay_id = document_request.user.barangay_id

            if (
                not user
                or not user.is_authenticated
                or user_barangay_id is None
                or document_barangay_id != user_barangay_id
            ):
                raise serializers.ValidationError({
                    'document_request_id': (
                        'Choose a document request from your assigned Barangay.'
                    )
                })

            if (
                user.role == User.Role.RESIDENT
                and document_request.user_id != user.id
            ):
                raise serializers.ValidationError({
                    'document_request_id': (
                        'You can only create a queue ticket for your own document request.'
                    )
                })

            attrs['service_type'] = document_request.document_type

        if self.instance is None and action == 'create':
            status_supplied = 'priority_status' in submitted
            flag_supplied = 'is_priority' in submitted
            requested_status = attrs.get('priority_status')
            requested_flag = attrs.get('is_priority')

            if not status_supplied and not flag_supplied:
                requested_status = QueueTicket.Priority.REGULAR
                requested_flag = False
            elif status_supplied and not flag_supplied:
                requested_flag = (
                    requested_status == QueueTicket.Priority.PRIORITY
                )
            elif flag_supplied and not status_supplied:
                requested_status = (
                    QueueTicket.Priority.PRIORITY
                    if requested_flag
                    else QueueTicket.Priority.REGULAR
                )

            if requested_flag != (
                requested_status == QueueTicket.Priority.PRIORITY
            ):
                raise serializers.ValidationError({
                    'priority_status': 'Priority fields must describe the same state.'
                })

            is_priority = requested_status == QueueTicket.Priority.PRIORITY
            user = getattr(request, 'user', None)

            if user and user.role == User.Role.RESIDENT and is_priority:
                raise serializers.ValidationError({
                    'is_priority': (
                        'Priority lane access must be verified by barangay staff.'
                    )
                })

            if is_priority:
                if not user or user.role != User.Role.ADMIN:
                    raise serializers.ValidationError({
                        'is_priority': 'Only a barangay admin can assign priority.'
                    })
                if not attrs.get('priority_reason'):
                    raise serializers.ValidationError({
                        'priority_reason': (
                            'A reason is required when assigning a priority ticket.'
                        )
                    })
            elif attrs.get('priority_reason'):
                raise serializers.ValidationError({
                    'priority_reason': (
                        'A reason is only accepted when assigning priority.'
                    )
                })

            attrs['priority_status'] = requested_status
            attrs['is_priority'] = requested_flag

        return attrs

    def create(self, validated_data):
        validated_data.pop('priority_reason', None)
        return super().create(validated_data)

    def get_resident_name(self, obj) -> str:
        if obj.user:
            return getattr(obj.user.profile, 'full_name', obj.user.username) if hasattr(obj.user, 'profile') else obj.user.username
        return obj.walkin_name if obj.walkin_name else "Walk-in Resident"


class QueueTicketPrioritySerializer(serializers.Serializer):
    priority_status = serializers.ChoiceField(choices=QueueTicket.Priority.choices)
    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=500,
    )


class PublicQueueStatusSerializer(serializers.Serializer):
    barangay_name = serializers.CharField(read_only=True)
    primary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        read_only=True,
    )
    current_ticket = serializers.CharField(
        allow_null=True,
        read_only=True,
    )
    total_waiting = serializers.IntegerField(
        min_value=0,
        read_only=True,
    )
