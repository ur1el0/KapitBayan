import 'dart:convert';
import 'dart:typed_data';

import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../models/admin_resident_model.dart';
import 'auth_service.dart';

class AdminResidentService {
  final ApiClient apiClient;
  final AuthService authService;

  const AdminResidentService({
    required this.apiClient,
    required this.authService,
  });

  Future<List<AdminResidentModel>> fetchVerifiedResidents() =>
      _fetchResidents('/auth/resident/');

  Future<List<AdminResidentModel>> fetchPendingResidents() =>
      _fetchResidents('/auth/pending-residents/');

  Future<List<AdminResidentModel>> _fetchResidents(String endpoint) async {
    final items = <AdminResidentModel>[];
    var page = 1;
    while (true) {
      final response = await apiClient.get(
        endpoint,
        queryParams: page == 1 ? null : {'page': '$page'},
        requiresAuth: true,
      );
      if (response.statusCode != 200) {
        throw ApiException(
          'Could not load residents (HTTP ${response.statusCode}).',
          statusCode: response.statusCode,
        );
      }

      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      final rawItems = decoded is Map<String, dynamic>
          ? decoded['results']
          : decoded;
      if (rawItems is! List) {
        throw const FormatException('Resident list response is invalid.');
      }
      items.addAll(
        rawItems.map(
          (item) => AdminResidentModel.fromJson(
            Map<String, dynamic>.from(item as Map),
          ),
        ),
      );

      final hasNextPage = decoded is Map<String, dynamic>
          ? decoded['next'] != null
          : false;
      if (!hasNextPage) break;
      page++;
    }
    return items;
  }

  Future<void> verifyResident(int residentId) async {
    final response = await apiClient.patch(
      '/auth/verify-resident/$residentId/',
      body: const <String, dynamic>{},
      requiresAuth: true,
    );
    if (response.statusCode != 200) {
      throw ApiException(
        'Could not approve resident (HTTP ${response.statusCode}).',
        statusCode: response.statusCode,
      );
    }
  }

  Future<void> rejectResident({
    required int residentId,
    required String reason,
  }) async {
    final response = await apiClient.delete(
      '/auth/reject-resident/$residentId/',
      body: {'rejection_reason': reason.trim()},
      requiresAuth: true,
    );
    if (response.statusCode != 204) {
      throw ApiException(
        'Could not reject resident (HTTP ${response.statusCode}).',
        statusCode: response.statusCode,
      );
    }
  }

  Future<Uint8List> fetchEvidence(int residentId, String fieldName) {
    return authService.fetchPrivateMedia(
      '/auth/resident/$residentId/media/$fieldName/',
    );
  }
}
