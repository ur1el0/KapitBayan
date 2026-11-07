import 'dart:convert';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../models/hotline_model.dart';
import 'storage_service.dart';

class HotlineService {
  final ApiClient apiClient;
  final StorageService? storageService;
  bool lastFetchUsedOfflineSnapshot = false;
  bool lastFetchFailed = false;
  DateTime? lastSnapshotSavedAt;

  HotlineService({required this.apiClient, this.storageService});

  /// Fetches emergency hotline directory from DRF endpoint /api/v1/hotlines/
  Future<List<HotlineModel>> fetchHotlines() async {
    lastFetchUsedOfflineSnapshot = false;
    lastFetchFailed = false;
    lastSnapshotSavedAt = null;
    try {
      final response = await apiClient.get('/hotlines/', requiresAuth: true);
      final dynamic decoded = jsonDecode(utf8.decode(response.bodyBytes));

      final List<dynamic> list =
          (decoded is Map<String, dynamic>
              ? decoded['results'] as List<dynamic>?
              : decoded as List<dynamic>?) ??
          [];

      final hotlines = list
          .map((item) => HotlineModel.fromJson(item as Map<String, dynamic>))
          .toList();

      try {
        await storageService?.saveOfflineSnapshot(
          'hotlines',
          hotlines.map((hotline) => hotline.toJson()).toList(growable: false),
        );
      } catch (_) {
        // Keep the live result even if secure cache storage is unavailable.
      }
      return hotlines;
    } on NetworkException {
      lastFetchFailed = true;
      try {
        final snapshot = await storageService?.readOfflineSnapshot('hotlines');
        if (snapshot != null) {
          lastFetchUsedOfflineSnapshot = true;
          lastSnapshotSavedAt = snapshot.savedAt;
          return snapshot.records
              .map(HotlineModel.fromJson)
              .where((hotline) => hotline.isActive)
              .toList(growable: false);
        }
      } catch (_) {
        // Use the safe built-in emergency list in the screen if storage fails.
      }
      return const [];
    } catch (_) {
      lastFetchFailed = true;
      return const [];
    }
  }
}
