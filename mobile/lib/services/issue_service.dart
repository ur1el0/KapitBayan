import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import 'storage_service.dart';

class PaginatedIssueResult {
  final List<IssueReport> items;
  final int totalCount;
  final int page;
  final int pageSize;
  final bool hasNext;
  final bool hasPrevious;
  final bool usedOfflineSnapshot;
  final DateTime? snapshotSavedAt;

  const PaginatedIssueResult({
    required this.items,
    required this.totalCount,
    required this.page,
    required this.pageSize,
    required this.hasNext,
    required this.hasPrevious,
    this.usedOfflineSnapshot = false,
    this.snapshotSavedAt,
  });

  int get totalPages =>
      totalCount == 0 ? 1 : ((totalCount + pageSize - 1) ~/ pageSize);
}

class IssueService {
  static const int defaultPageSize = 5;

  final ApiClient apiClient;
  final StorageService? storageService;
  bool lastIssuesUsedOfflineSnapshot = false;
  bool lastFetchFailed = false;
  DateTime? lastSnapshotSavedAt;

  IssueService({required this.apiClient, this.storageService});

  static List<IssueReport> _sortNewestFirst(List<IssueReport> reports) {
    final sorted = List<IssueReport>.of(reports);
    sorted.sort((a, b) {
      final aDate = DateTime.tryParse(a.createdAt);
      final bDate = DateTime.tryParse(b.createdAt);
      if (aDate != null && bDate != null) {
        final cmp = bDate.compareTo(aDate);
        if (cmp != 0) return cmp;
      } else if (bDate != null) {
        return 1;
      } else if (aDate != null) {
        return -1;
      }
      return b.id.compareTo(a.id);
    });
    return sorted;
  }

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

  /// Fetches a filtered, newest-first page of the resident's issue reports.
  Future<PaginatedIssueResult> getMyIssuesPage({
    int page = 1,
    int pageSize = defaultPageSize,
    String? statusFilter,
    String? categoryFilter,
    String? search,
  }) async {
    lastIssuesUsedOfflineSnapshot = false;
    lastFetchFailed = false;
    lastSnapshotSavedAt = null;

    final queryParams = <String, String>{
      'page': '$page',
      'page_size': '$pageSize',
    };
    if (statusFilter != null && statusFilter.isNotEmpty && statusFilter != 'ALL') {
      queryParams['status'] = statusFilter;
    }
    if (categoryFilter != null &&
        categoryFilter.isNotEmpty &&
        categoryFilter != 'ALL') {
      queryParams['category'] = categoryFilter;
    }
    final trimmedSearch = (search ?? '').trim();
    if (trimmedSearch.isNotEmpty) {
      queryParams['search'] = trimmedSearch;
    }

    final bool isDefaultUnfilteredPage =
        page == 1 &&
        queryParams.length == 2;

    try {
      final response = await apiClient.get(
        '/reports/',
        queryParams: queryParams,
      );
      final Map<String, dynamic> data = jsonDecode(response.body);
      final List<dynamic> results = data['results'] ?? [];
      final issues = _sortNewestFirst(
        results
            .map((item) => IssueReport.fromJson(item as Map<String, dynamic>))
            .toList(growable: false),
      );
      final int totalCount = (data['count'] as num?)?.toInt() ?? issues.length;
      final bool hasNext = data['next'] != null;
      final bool hasPrevious = data['previous'] != null || page > 1;

      if (isDefaultUnfilteredPage) {
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
      }

      return PaginatedIssueResult(
        items: issues,
        totalCount: totalCount,
        page: page,
        pageSize: pageSize,
        hasNext: hasNext,
        hasPrevious: hasPrevious,
      );
    } on NetworkException {
      lastFetchFailed = true;
      final snapshot = await storageService?.readOfflineSnapshot(
        'issue_reports',
      );
      if (snapshot == null) rethrow;
      lastIssuesUsedOfflineSnapshot = true;
      lastSnapshotSavedAt = snapshot.savedAt;

      var cached = _sortNewestFirst(
        snapshot.records.map(IssueReport.fromJson).toList(growable: false),
      );
      if (statusFilter != null && statusFilter.isNotEmpty && statusFilter != 'ALL') {
        cached = cached
            .where((item) => item.status.toUpperCase() == statusFilter.toUpperCase())
            .toList(growable: false);
      }
      if (categoryFilter != null &&
          categoryFilter.isNotEmpty &&
          categoryFilter != 'ALL') {
        cached = cached
            .where((item) => item.category.toUpperCase() == categoryFilter.toUpperCase())
            .toList(growable: false);
      }
      if (trimmedSearch.isNotEmpty) {
        final needle = trimmedSearch.toLowerCase();
        cached = cached
            .where(
              (item) =>
                  item.title.toLowerCase().contains(needle) ||
                  item.location.toLowerCase().contains(needle) ||
                  item.description.toLowerCase().contains(needle),
            )
            .toList(growable: false);
      }

      final startIndex = (page - 1) * pageSize;
      final paged = startIndex >= cached.length
          ? const <IssueReport>[]
          : cached.sublist(
              startIndex,
              (startIndex + pageSize).clamp(0, cached.length),
            );

      return PaginatedIssueResult(
        items: paged,
        totalCount: cached.length,
        page: page,
        pageSize: pageSize,
        hasNext: startIndex + pageSize < cached.length,
        hasPrevious: page > 1,
        usedOfflineSnapshot: true,
        snapshotSavedAt: snapshot.savedAt,
      );
    }
  }

  /// Fetches the resident's historical issue reports (newest first).
  Future<List<IssueReport>> getMyIssues() async {
    final result = await getMyIssuesPage(page: 1, pageSize: defaultPageSize);
    return result.items;
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
