import 'dart:convert';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../models/document_request_model.dart';
import 'issue_service.dart';
import 'storage_service.dart';

/// Service coordinating on-site field actions: live queue ticker, clearance QR validation, and incident inspection
class FieldOfficialService {
  final ApiClient apiClient;
  final StorageService storageService;

  FieldOfficialService({
    required this.apiClient,
    required this.storageService,
  });

  /// Advance the live desk queue to the next waiting citizen (POST /tickets/next/)
  Future<Map<String, dynamic>> callNextTicket() async {
    final response = await apiClient.post(
      '/tickets/next/',
      requiresAuth: true,
    );

    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    } else {
      final errorData = jsonDecode(utf8.decode(response.bodyBytes));
      final detail = errorData is Map ? errorData['detail'] ?? 'Failed to advance queue.' : 'Queue error.';
      throw Exception(detail);
    }
  }

  /// Fetches real-time desk counter status
  Future<Map<String, dynamic>> fetchLiveQueueStatus() async {
    final response = await apiClient.get(
      '/tickets/live-status/',
      requiresAuth: true,
    );

    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    }
    return {'current_ticket': null, 'total_waiting': 0};
  }

  /// Finds a physical or digital document by tracking ID or official receipt number.
  Future<DocumentRequestModel?> verifyClearance(String identifier) async {
    try {
      final query = Uri(queryParameters: {'identifier': identifier.trim()}).query;
      final response = await apiClient.get(
        '/document-requests/verify/?$query',
        requiresAuth: true,
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return DocumentRequestModel.fromJson(data);
      }
      return null;
    } on NotFoundException {
      return null;
    }
  }

  /// Fetches all active incident reports within the official's barangay jurisdiction
  Future<List<IssueReport>> fetchBarangayIssues() async {
    try {
      final response = await apiClient.get(
        '/reports/',
        requiresAuth: true,
      );

      final dynamic decoded = jsonDecode(utf8.decode(response.bodyBytes));
      final List<dynamic> list = decoded is Map && decoded.containsKey('results')
          ? decoded['results'] as List<dynamic>
          : (decoded is List ? decoded : const []);

      return list.map((item) => IssueReport.fromJson(item as Map<String, dynamic>)).toList();
    } catch (_) {
      return [];
    }
  }

  /// Updates incident report status on-site (e.g. IN_PROGRESS, RESOLVED)
  Future<void> updateIssueStatus({
    required int reportId,
    required String status,
  }) async {
    await apiClient.patch(
      '/reports/$reportId/',
      body: {'status': status},
      requiresAuth: true,
    );
  }

  /// Updates the triaged urgency of a barangay incident report.
  Future<void> updateIssueUrgency({
    required int reportId,
    required String urgency,
  }) async {
    final response = await apiClient.patch(
      '/reports/$reportId/',
      body: {'urgency': urgency},
      requiresAuth: true,
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to update incident urgency.');
    }
  }
}
