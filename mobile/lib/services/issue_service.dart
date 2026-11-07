import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import 'storage_service.dart';

class IssueService {
  final ApiClient apiClient;
  final StorageService? storageService;
  bool lastIssuesUsedOfflineSnapshot = false;
  bool lastFetchFailed = false;
  DateTime? lastSnapshotSavedAt;

  IssueService({required this.apiClient, this.storageService});

  /// Submits a new issue report to the Django backend
  Future<void> submitIssue({
    required String title,
    required String description,
    required String location,
    required String category,
    required String urgency,
    XFile? imageFile,
  }) async {
    final fields = {
      'title': title.trim(),
      'description': description.trim(),
      'location': location.trim(),
      'category': category,
      'urgency': urgency,
    };

    List<http.MultipartFile>? files;

    if (imageFile != null) {
      final bytes = await imageFile.readAsBytes();
      final multipartFile = http.MultipartFile.fromBytes(
        'image',
        bytes,
        filename: imageFile.name,
      );
      files = [multipartFile];
    }

    await apiClient.postMultipart(
      '/reports/',
      fields: fields,
      files: files,
      requiresAuth: true,
    );
  }

  /// Fetches the resident's historical issue reports
  Future<List<IssueReport>> getMyIssues() async {
    lastIssuesUsedOfflineSnapshot = false;
    lastFetchFailed = false;
    lastSnapshotSavedAt = null;
    try {
      final response = await apiClient.get('/reports/');
      final Map<String, dynamic> data = jsonDecode(response.body);
      final List<dynamic> results = data['results'] ?? [];
      final issues = results
          .map((item) => IssueReport.fromJson(item as Map<String, dynamic>))
          .toList(growable: false);
      try {
        await storageService?.saveOfflineSnapshot(
          'issue_reports',
          issues
              .map((issue) {
                final record = issue.toJson();
                record['image'] = null;
                return record;
              })
              .toList(growable: false),
        );
      } catch (_) {
        // Keep live results available if encrypted storage cannot be written.
      }
      return issues;
    } on NetworkException {
      lastFetchFailed = true;
      final snapshot = await storageService?.readOfflineSnapshot(
        'issue_reports',
      );
      if (snapshot == null) rethrow;
      lastIssuesUsedOfflineSnapshot = true;
      lastSnapshotSavedAt = snapshot.savedAt;
      return snapshot.records.map(IssueReport.fromJson).toList(growable: false);
    }
  }
}

/// A clean Dart model to represent the Django IssueReport JSON
class IssueReport {
  final int id;
  final String title;
  final String description;
  final String location;
  final String status;
  final String category;
  final String urgency;
  final String? imageUrl;
  final String createdAt;

  IssueReport({
    required this.id,
    required this.title,
    required this.description,
    required this.location,
    required this.status,
    this.category = 'OTHER',
    this.urgency = 'MINOR',
    this.imageUrl,
    required this.createdAt,
  });

  factory IssueReport.fromJson(Map<String, dynamic> json) {
    return IssueReport(
      id: json['id'] as int? ?? 0,
      title: json['title'] as String? ?? 'Unknown Issue',
      description: json['description'] as String? ?? '',
      location: json['location'] as String? ?? '',
      status: json['status'] as String? ?? 'PENDING',
      category: json['category'] as String? ?? 'OTHER',
      urgency: json['urgency'] as String? ?? 'MINOR',
      imageUrl: json['image'] as String?,
      createdAt: json['created_at'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'description': description,
    'location': location,
    'status': status,
    'category': category,
    'urgency': urgency,
    'image': imageUrl,
    'created_at': createdAt,
  };
}
