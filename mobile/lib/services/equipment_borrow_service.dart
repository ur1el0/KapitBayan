import 'dart:convert';

import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../models/equipment_borrow_request_model.dart';
import 'storage_service.dart';

class EquipmentBorrowService {
  final ApiClient apiClient;
  final StorageService? storageService;
  bool lastRequestsUsedOfflineSnapshot = false;
  bool lastFetchFailed = false;
  DateTime? lastSnapshotSavedAt;

  EquipmentBorrowService({required this.apiClient, this.storageService});

  Future<List<EquipmentBorrowRequestModel>> fetchRequests() async {
    lastRequestsUsedOfflineSnapshot = false;
    lastFetchFailed = false;
    lastSnapshotSavedAt = null;
    try {
      final response = await apiClient.get(
        '/equipment-requests/',
        requiresAuth: true,
      );
      final dynamic data = jsonDecode(utf8.decode(response.bodyBytes));
      final List<dynamic> rawList;
      if (data is Map<String, dynamic> && data.containsKey('results')) {
        rawList = data['results'] as List<dynamic>;
      } else if (data is List<dynamic>) {
        rawList = data;
      } else {
        rawList = [];
      }

      final maps = rawList
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();
      try {
        await storageService?.saveOfflineSnapshot(
          'equipment_borrow_requests',
          maps,
        );
      } catch (_) {
        // Keep live results available if encrypted storage cannot be written.
      }
      return maps
          .map((item) => EquipmentBorrowRequestModel.fromJson(item))
          .toList();
    } on NetworkException {
      lastFetchFailed = true;
      final snapshot = await storageService?.readOfflineSnapshot(
        'equipment_borrow_requests',
      );
      if (snapshot == null) rethrow;
      lastRequestsUsedOfflineSnapshot = true;
      lastSnapshotSavedAt = snapshot.savedAt;
      return snapshot.records
          .map((item) => EquipmentBorrowRequestModel.fromJson(item))
          .toList();
    }
  }

  Future<EquipmentBorrowRequestModel> createRequest({
    required String itemType,
    required int quantity,
    required String borrowDate,
    required String returnDate,
    String timeSlot = '',
    required String purpose,
  }) async {
    final response = await apiClient.post(
      '/equipment-requests/',
      body: {
        'item_type': itemType,
        'quantity': quantity,
        'borrow_date': borrowDate,
        'return_date': returnDate,
        'time_slot': timeSlot.trim(),
        'purpose': purpose.trim(),
      },
      requiresAuth: true,
    );
    final decoded =
        jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    return EquipmentBorrowRequestModel.fromJson(decoded);
  }

  Future<EquipmentBorrowRequestModel> reviewRequest({
    required int requestId,
    required String status,
    String adminNotes = '',
  }) async {
    final response = await apiClient.patch(
      '/equipment-requests/$requestId/',
      body: {
        'status': status,
        'admin_notes': adminNotes.trim(),
      },
      requiresAuth: true,
    );
    final decoded =
        jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    return EquipmentBorrowRequestModel.fromJson(decoded);
  }
}
