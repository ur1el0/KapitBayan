import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

import '../core/config/app_config.dart';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../models/auth_response.dart';
import '../models/barangay_model.dart';
import '../models/user_model.dart';
import 'storage_service.dart';
import 'push_notification_service.dart';

/// Authentication service coordinating login, session renewal, user profiles,
/// and local storage synchronization.
class AuthService {
  final ApiClient apiClient;
  final StorageService storageService;

  AuthService({required this.apiClient, required this.storageService}) {
    // Synchronize silently rotated tokens into persistent local storage
    apiClient.onTokenRefreshed = (newAccessToken, newCookieHeader) async {
      await storageService.saveTokens(
        accessToken: newAccessToken,
        refreshCookie: newCookieHeader,
      );
    };

    // Restore session credentials into ApiClient on startup
    final token = storageService.getAccessToken();
    final cookie = storageService.getRefreshCookie();
    if (token != null || cookie != null) {
      apiClient.setAuthCredentials(accessToken: token, cookieHeader: cookie);
    }
  }

  /// Authenticate against Django backend `/api/v1/auth/login/`
  Future<AuthResponse> login({
    required String username,
    required String password,
  }) async {
    final response = await apiClient.post(
      AppConfig.loginEndpoint,
      body: {'username': username.trim(), 'password': password},
      requiresAuth: false,
    );

    final Map<String, dynamic> responseData = jsonDecode(
      utf8.decode(response.bodyBytes),
    );

    // Extract cookie from Set-Cookie header (if server returned one)
    final cookieHeader = apiClient.extractSetCookie(response);

    // Construct strongly-typed auth response
    final authResponse = AuthResponse.fromJson(
      responseData,
      refreshCookie: cookieHeader,
    );

    // Persist credentials in local storage
    await storageService.saveTokens(
      accessToken: authResponse.accessToken,
      refreshCookie: cookieHeader,
    );
    await storageService.saveUser(authResponse.user);

    // Update active in-memory headers in ApiClient
    apiClient.setAuthCredentials(
      accessToken: authResponse.accessToken,
      cookieHeader: cookieHeader,
    );

    return authResponse;
  }

  /// Lists approved barangays available for resident registration.
  Future<List<BarangayModel>> fetchBarangays() async {
    final response = await apiClient.get(
      '/auth/public/barangays/',
      requiresAuth: false,
    );
    final decoded = jsonDecode(utf8.decode(response.bodyBytes));
    final List<dynamic> results = decoded is Map<String, dynamic>
        ? (decoded['results'] as List<dynamic>? ?? <dynamic>[])
        : decoded as List<dynamic>;
    return results
        .map((item) => BarangayModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// Register a new resident account against Django backend `/api/v1/auth/register/`
  Future<UserModel> register({
    required String fullName,
    required String username,
    required String email,
    required String password,
    required String birthDate,
    required bool voterStatus,
    required bool privacyConsent,
    required String purok,
    int? barangayId,
    String? contactNumber,
    String? addressDetails,
    String? guardianId,
    String? philsysIdNumber,
    XFile? philsysPhoto,
    String? utilityBillingType,
    XFile? utilityBillingPhoto,
    String? secondaryIdType,
    XFile? secondaryIdPhoto,
  }) async {
    final Map<String, String> fields = {
      'full_name': fullName.trim(),
      'username': username.trim(),
      'email': email.trim().toLowerCase(),
      'password': password,
      'birth_date': birthDate,
      'voter_status': voterStatus.toString(),
      'privacy_consent': privacyConsent.toString(),
      'privacy_consent_version': 'resident-v1',
      'purok': purok.trim(),
      if (barangayId != null) 'barangay_id': barangayId.toString(),
      if (addressDetails != null && addressDetails.trim().isNotEmpty)
        'address_details': addressDetails.trim(),
      if (contactNumber != null && contactNumber.isNotEmpty)
        'contact_number': contactNumber.trim(),
      if (guardianId != null && guardianId.isNotEmpty)
        'guardian_id': guardianId.trim(),
      if (philsysIdNumber != null && philsysIdNumber.trim().isNotEmpty)
        'philsys_id_number': philsysIdNumber.trim(),
      if (utilityBillingType != null && utilityBillingType.trim().isNotEmpty)
        'utility_billing_type': utilityBillingType.trim(),
      if (secondaryIdType != null && secondaryIdType.trim().isNotEmpty)
        'secondary_id_type': secondaryIdType.trim(),
    };

    final List<http.MultipartFile> files = [];

    if (philsysPhoto != null) {
      final bytes = await philsysPhoto.readAsBytes();
      files.add(
        http.MultipartFile.fromBytes(
          'philsys_id_photo',
          bytes,
          filename: philsysPhoto.name.isNotEmpty
              ? philsysPhoto.name
              : 'philsys_id.jpg',
        ),
      );
    }

    if (utilityBillingPhoto != null) {
      final bytes = await utilityBillingPhoto.readAsBytes();
      files.add(
        http.MultipartFile.fromBytes(
          'utility_billing_photo',
          bytes,
          filename: utilityBillingPhoto.name.isNotEmpty
              ? utilityBillingPhoto.name
              : 'utility_bill.jpg',
        ),
      );
    }

    if (secondaryIdPhoto != null) {
      final bytes = await secondaryIdPhoto.readAsBytes();
      files.add(
        http.MultipartFile.fromBytes(
          'secondary_id_photo',
          bytes,
          filename: secondaryIdPhoto.name.isNotEmpty
              ? secondaryIdPhoto.name
              : 'secondary_id.jpg',
        ),
      );
    }

    final response = await apiClient.postMultipart(
      AppConfig.registerEndpoint,
      fields: fields,
      files: files.isNotEmpty ? files : null,
      requiresAuth: false,
    );

    final Map<String, dynamic> responseData = jsonDecode(
      utf8.decode(response.bodyBytes),
    );

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return UserModel.fromJson(responseData);
    } else {
      throw ApiException(
        _extractErrorMessage(responseData, 'Registration failed'),
        statusCode: response.statusCode,
        details: responseData,
      );
    }
  }

  /// Update currently authenticated resident profile `/api/v1/auth/me/`
  Future<UserModel> updateProfile({
    String? fullName,
    String? contactNumber,
    String? birthDate,
    bool? voterStatus,
    String? philsysIdNumber,
    XFile? philsysPhoto,
    bool removePhilsysPhoto = false,
    String? secondaryIdType,
    XFile? secondaryIdPhoto,
    bool removeSecondaryIdPhoto = false,
    String? utilityBillingType,
    XFile? utilityBillingPhoto,
    bool removeUtilityBillingPhoto = false,
  }) async {
    final bool hasFiles = philsysPhoto != null ||
        secondaryIdPhoto != null ||
        utilityBillingPhoto != null;

    final http.Response response;

    if (hasFiles) {
      final Map<String, String> fields = {};
      if (fullName != null) fields['full_name'] = fullName.trim();
      if (contactNumber != null) fields['contact_number'] = contactNumber.trim();
      if (birthDate != null) fields['birth_date'] = birthDate;
      if (voterStatus != null) fields['voter_status'] = voterStatus.toString();
      if (philsysIdNumber != null) fields['philsys_id_number'] = philsysIdNumber.trim();
      if (removePhilsysPhoto) fields['remove_philsys_id_photo'] = 'true';
      if (secondaryIdType != null) fields['secondary_id_type'] = secondaryIdType.trim();
      if (removeSecondaryIdPhoto) fields['remove_secondary_id_photo'] = 'true';
      if (utilityBillingType != null) fields['utility_billing_type'] = utilityBillingType.trim();
      if (removeUtilityBillingPhoto) fields['remove_utility_billing_photo'] = 'true';

      final List<http.MultipartFile> files = [];

      if (philsysPhoto != null) {
        final bytes = await philsysPhoto.readAsBytes();
        files.add(
          http.MultipartFile.fromBytes(
            'philsys_id_photo',
            bytes,
            filename: philsysPhoto.name.isNotEmpty
                ? philsysPhoto.name
                : 'philsys_id.jpg',
          ),
        );
      }

      if (secondaryIdPhoto != null) {
        final bytes = await secondaryIdPhoto.readAsBytes();
        files.add(
          http.MultipartFile.fromBytes(
            'secondary_id_photo',
            bytes,
            filename: secondaryIdPhoto.name.isNotEmpty
                ? secondaryIdPhoto.name
                : 'secondary_id.jpg',
          ),
        );
      }

      if (utilityBillingPhoto != null) {
        final bytes = await utilityBillingPhoto.readAsBytes();
        files.add(
          http.MultipartFile.fromBytes(
            'utility_billing_photo',
            bytes,
            filename: utilityBillingPhoto.name.isNotEmpty
                ? utilityBillingPhoto.name
                : 'utility_bill.jpg',
          ),
        );
      }

      response = await apiClient.patchMultipart(
        AppConfig.userProfileEndpoint,
        fields: fields,
        files: files.isNotEmpty ? files : null,
        requiresAuth: true,
      );
    } else {
      final Map<String, dynamic> profileData = {};
      if (fullName != null) profileData['full_name'] = fullName.trim();
      if (contactNumber != null) profileData['contact_number'] = contactNumber.trim();
      if (birthDate != null) profileData['birth_date'] = birthDate;
      if (voterStatus != null) profileData['voter_status'] = voterStatus;
      if (philsysIdNumber != null) profileData['philsys_id_number'] = philsysIdNumber.trim();
      if (removePhilsysPhoto) profileData['remove_philsys_id_photo'] = true;
      if (secondaryIdType != null) profileData['secondary_id_type'] = secondaryIdType.trim();
      if (removeSecondaryIdPhoto) profileData['remove_secondary_id_photo'] = true;
      if (utilityBillingType != null) profileData['utility_billing_type'] = utilityBillingType.trim();
      if (removeUtilityBillingPhoto) profileData['remove_utility_billing_photo'] = true;

      response = await apiClient.patch(
        AppConfig.userProfileEndpoint,
        body: {'profile': profileData},
        requiresAuth: true,
      );
    }

    final Map<String, dynamic> responseData = jsonDecode(
      utf8.decode(response.bodyBytes),
    );

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final updatedUser = UserModel.fromJson(responseData);
      await storageService.saveUser(updatedUser);
      return updatedUser;
    } else {
      throw ApiException(
        _extractErrorMessage(responseData, 'Failed to update profile'),
        statusCode: response.statusCode,
        details: responseData,
      );
    }
  }

  /// Extracts readable error message from DRF validation responses
  String _extractErrorMessage(Map<String, dynamic> details, String fallback) {
    if (details.containsKey('verification_documents')) {
      final v = details['verification_documents'];
      if (v is List && v.isNotEmpty) return v.first.toString();
      if (v is String) return v;
    }
    if (details.containsKey('profile') && details['profile'] is Map) {
      final p = details['profile'] as Map<String, dynamic>;
      if (p.containsKey('verification_documents')) {
        final v = p['verification_documents'];
        if (v is List && v.isNotEmpty) return v.first.toString();
        if (v is String) return v;
      }
      for (final val in p.values) {
        if (val is List && val.isNotEmpty) return val.first.toString();
        if (val is String) return val;
      }
    }
    if (details.containsKey('detail')) return details['detail'].toString();
    if (details.containsKey('error')) return details['error'].toString();
    for (final val in details.values) {
      if (val is List && val.isNotEmpty) return val.first.toString();
      if (val is String) return val;
    }
    return fallback;
  }

  /// Construct an absolute media URL for private resident media
  String getAuthenticatedMediaUrl(String relativePath) {
    final cleanBase = AppConfig.baseUrl.replaceAll(RegExp(r'/+$'), '');
    final cleanPath = relativePath.replaceAll(RegExp(r'^/+'), '');
    return '$cleanBase/$cleanPath';
  }

  /// Downloads private resident evidence through the authenticated API client.
  ///
  /// Using ApiClient preserves the normal Bearer header and refresh-and-retry
  /// behavior for expired access tokens.
  Future<Uint8List> fetchPrivateMedia(String relativePath) async {
    final response = await apiClient.get(
      relativePath,
      // DRF rejects `image/*` during renderer negotiation before the view
      // can return its private FileResponse.
      headers: const {'Accept': '*/*'},
      requiresAuth: true,
    );
    final contentType = response.headers['content-type']
        ?.split(';')
        .first
        .trim()
        .toLowerCase();
    if (contentType == null || !contentType.startsWith('image/')) {
      throw ApiException(
        'The server did not return an image.',
        statusCode: response.statusCode,
      );
    }
    return response.bodyBytes;
  }

  /// Renew expired JWT access token using the backend refresh endpoint
  Future<String?> refreshToken() async {
    final refreshCookie = storageService.getRefreshCookie();
    if (refreshCookie == null || refreshCookie.isEmpty) {
      return null;
    }

    try {
      final response = await apiClient.post(
        AppConfig.tokenRefreshEndpoint,
        headers: {'Cookie': refreshCookie},
        requiresAuth: false,
      );

      final Map<String, dynamic> responseData = jsonDecode(
        utf8.decode(response.bodyBytes),
      );

      final newAccessToken = responseData['access'] as String?;
      final newCookieHeader =
          apiClient.extractSetCookie(response) ?? refreshCookie;

      if (newAccessToken != null) {
        await storageService.saveTokens(
          accessToken: newAccessToken,
          refreshCookie: newCookieHeader,
        );
        apiClient.setAuthCredentials(
          accessToken: newAccessToken,
          cookieHeader: newCookieHeader,
        );
        return newAccessToken;
      }
    } catch (_) {
      // Refresh failed (cookie expired or revoked)
      await logout();
    }
    return null;
  }

  /// Terminate the active session on both the backend and local storage
  Future<void> logout() async {
    try {
      final cookie = storageService.getRefreshCookie();
      if (cookie != null && cookie.isNotEmpty) {
        await apiClient.post(
          AppConfig.logoutEndpoint,
          headers: {'Cookie': cookie},
          requiresAuth: false,
        );
      }
    } catch (_) {
      // Silently proceed with local cleanup even if network fails
    } finally {
      await PushNotificationService.disposeShared();
      apiClient.clearAuthCredentials();
      await storageService.clearSession();
    }
  }

  /// Check if user has an active stored token
  bool isAuthenticated() {
    final token = storageService.getAccessToken();
    return token != null && token.isNotEmpty;
  }

  /// Retrieve cached user profile
  UserModel? getCurrentUser() {
    return storageService.getUser();
  }

  /// Request a password reset email/token for the given registered email
  Future<void> requestPasswordReset(String email) async {
    await apiClient.post(
      '/auth/password-reset/',
      body: {'email': email.trim().toLowerCase()},
      requiresAuth: false,
    );
  }

  /// Confirm password reset using the token, UID, and new password
  Future<void> confirmPasswordReset({
    required String newPassword,
    required String uidb64,
    required String token,
  }) async {
    await apiClient.post(
      '/auth/password-reset/confirm/',
      body: {'new_password': newPassword, 'uidb64': uidb64, 'token': token},
      requiresAuth: false,
    );
  }
}
