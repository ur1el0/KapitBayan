import json

from rest_framework import status, permissions, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiTypes

from gridy_auth.models import Barangay, User
from gridy_auth.serializers import UserSerializer, BarangaySerializer
from gridy_auth.permissions import IsBarangayOfficial
from gridy_auth.lifecycle import erase_user_account
from gridy_audit.services import log_action
from gridy_audit.models import AuditLog

@extend_schema(tags=['User Profile'])
class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    PROFILE_FIELD_NAMES = {
        'full_name',
        'birth_date',
        'voter_status',
        'contact_number',
        'purok',
        'philsys_id_number',
        'philsys_id_photo',
        'remove_philsys_id_photo',
        'secondary_id_type',
        'secondary_id_photo',
        'remove_secondary_id_photo',
        'utility_billing_type',
        'utility_billing_photo',
        'remove_utility_billing_photo',
    }

    def _normalize_request_data(self, request):
        raw_data = request.data
        if hasattr(raw_data, 'dict'):
            data = {}
            for key in raw_data.keys():
                if key in request.FILES:
                    data[key] = request.FILES.get(key)
                else:
                    data[key] = raw_data.get(key)
        elif isinstance(raw_data, dict):
            data = dict(raw_data)
            for key, file_obj in request.FILES.items():
                data[key] = file_obj
        else:
            return raw_data

        profile_data = {}
        raw_profile = data.get('profile')
        if isinstance(raw_profile, str):
            try:
                raw_profile = json.loads(raw_profile)
            except Exception:
                raw_profile = {}
        if isinstance(raw_profile, dict):
            profile_data.update(raw_profile)

        keys_to_remove = []
        for key, val in list(data.items()):
            if key == 'profile':
                continue
            if key.startswith('profile.') or key.startswith('profile['):
                clean_key = key.removeprefix('profile.').removeprefix('profile[').rstrip(']')
                profile_data[clean_key] = val
                keys_to_remove.append(key)
            elif key in self.PROFILE_FIELD_NAMES and key not in profile_data:
                profile_data[key] = val
                keys_to_remove.append(key)

        for key in keys_to_remove:
            data.pop(key, None)

        if profile_data or 'profile' in data:
            data['profile'] = profile_data

        return data

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status.HTTP_200_OK)
    
    @extend_schema(
        summary="Update User Profile (Preferences)",
        request=UserSerializer,
        responses={200: UserSerializer, 400:OpenApiTypes.OBJECT}
    )
    def patch(self, request):
        normalized_data = self._normalize_request_data(request)
        serializer = UserSerializer(request.user, data=normalized_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Permanently Erase User Account (Right to Erasure)",
        responses={204: None}
    )
    def delete(self, request):
        user = request.user
        erase_user_account(
            user=user,
            reason=f"User {user.username} (ID: {user.id}) voluntarily exercised their Right to Erasure and permanently deleted their account.",
            request=request,
            actor=user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
    
@extend_schema(tags=['Barangay Settings'])
class BarangayViewSet(viewsets.ModelViewSet):
    """
    Settings endpoint for Barangay Identity.
    Only allows GET and PATCH
    """
    permission_classes = [permissions.IsAuthenticated, IsBarangayOfficial]
    serializer_class = BarangaySerializer
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ['get', 'patch']

    def get_queryset(self):
        user = self.request.user
        # Isolate to the official's own barangay
        if user.barangay:
            return Barangay.objects.filter(id=user.barangay.id)
        return Barangay.objects.none()
