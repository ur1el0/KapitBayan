import 'dart:convert';

import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import 'storage_service.dart';

class AidRequestService {
  final ApiClient apiClient;
  final StorageService? storageService;
  bool lastRequestsUsedOfflineSnapshot = false;
  bool lastFetchFailed = false;
  DateTime? lastSnapshotSavedAt;

  AidRequestService({required this.apiClient, this.storageService});

  Future<List<Map<String, dynamic>>> fetchRequests() async {
    lastRequestsUsedOfflineSnapshot = false;
    lastFetchFailed = false;
    lastSnapshotSavedAt = null;
    try {
      final response = await apiClient.get(
        '/aid-requests/',
        requiresAuth: true,
      );
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      final data = decoded is Map<String, dynamic> && decoded['results'] is List
          ? decoded['results'] as List<dynamic>
          : decoded as List<dynamic>;
      final requests = data.cast<Map<String, dynamic>>();
      try {
        await storageService?.saveOfflineSnapshot('aid_requests', requests);
      } catch (_) {
        // Keep live results available if encrypted storage cannot be written.
      }
      return requests;
    } on NetworkException {
      lastFetchFailed = true;
      final snapshot = await storageService?.readOfflineSnapshot(
        'aid_requests',
      );
      if (snapshot == null) rethrow;
      lastRequestsUsedOfflineSnapshot = true;
      lastSnapshotSavedAt = snapshot.savedAt;
      return snapshot.records;
    }
  }

  Future<Map<String, dynamic>> createRequest({
    required String assistanceType,
    required String reason,
  }) async {
    final response = await apiClient.post(
      '/aid-requests/',
      body: {'assistance_type': assistanceType, 'reason': reason.trim()},
      requiresAuth: true,
    );
    return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
  }
}
