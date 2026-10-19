import 'dart:convert';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../models/activity_schedule_model.dart';
import '../models/announcement_model.dart';
import '../models/document_request_model.dart';
import '../models/notification_item_model.dart';
import '../models/user_model.dart';
import 'storage_service.dart';

class _FetchResult<T> {
  final T? data;
  final bool failed;
  final String? errorMessage;
  final int? statusCode;

  const _FetchResult({
    this.data,
    this.failed = false,
    this.errorMessage,
    this.statusCode,
  });
}

/// Aggregated data container holding all dashboard metrics and schedules
class DashboardData {
  final UserModel? user;
  final List<AnnouncementModel> announcements;
  final List<DocumentRequestModel> documentRequests;
  final List<ActivityScheduleModel> activities;
  final List<NotificationItemModel> notifications;
  final Map<String, dynamic>? queueStatus;
  final bool hasNotificationsError;
  final String? notificationsErrorMessage;
  final bool hasAnnouncementsError;
  final bool hasDocumentRequestsError;

  const DashboardData({
    this.user,
    this.announcements = const [],
    this.documentRequests = const [],
    this.activities = const [],
    this.notifications = const [],
    this.queueStatus,
    this.hasNotificationsError = false,
    this.notificationsErrorMessage,
    this.hasAnnouncementsError = false,
    this.hasDocumentRequestsError = false,
  });

  /// Count of active pending/processing document requests for this resident
  int get pendingRequestsCount {
    return documentRequests
        .where((doc) => doc.isPending || doc.isProcessing)
        .length;
  }
}

/// Service coordinating data fetching for the resident dashboard
class DashboardService {
  final ApiClient apiClient;
  final StorageService storageService;

  DashboardService({required this.apiClient, required this.storageService});

  /// Fetches all dashboard datasets concurrently from the backend APIs
  Future<DashboardData> fetchDashboardData() async {
    final cachedUser = storageService.getUser();

    UserModel? currentUser = cachedUser;
    List<AnnouncementModel> announcements = [];
    List<DocumentRequestModel> documentRequests = [];
    List<ActivityScheduleModel> activities = [];
    Map<String, dynamic>? queueStatus;

    // Run parallel queries with internal fault tolerance
    final results = await Future.wait([
      _fetchUserProfile(),
      _fetchAnnouncements(),
      _fetchDocumentRequests(),
      _fetchActivities(),
      _fetchLiveQueue(),
      _fetchResidentNotifications(),
    ]);

    if (results[0] != null) currentUser = results[0] as UserModel;
    final annResult = results[1] as _FetchResult<List<AnnouncementModel>>;
    final docResult = results[2] as _FetchResult<List<DocumentRequestModel>>;

    announcements = annResult.data ?? [];
    documentRequests = docResult.data ?? [];
    activities = results[3] as List<ActivityScheduleModel>;
    queueStatus = results[4] as Map<String, dynamic>?;
    final residentNotificationResult =
        results[5] as _FetchResult<List<NotificationItemModel>>;

    final bool hasNotificationsError =
        annResult.failed ||
        docResult.failed ||
        residentNotificationResult.failed;
    final List<String> notificationErrors = [];
    if (annResult.failed && docResult.failed) {
      notificationErrors.add(
        'Unable to load announcements (${annResult.errorMessage}) and document updates (${docResult.errorMessage})',
      );
    } else if (annResult.failed) {
      notificationErrors.add(
        'Unable to load announcements (${annResult.errorMessage})',
      );
    } else if (docResult.failed) {
      notificationErrors.add(
        'Unable to load document request updates (${docResult.errorMessage})',
      );
    }
    if (residentNotificationResult.failed) {
      notificationErrors.add(
        'Unable to load saved alerts (${residentNotificationResult.errorMessage})',
      );
    }

    // Keep successful sources visible when another source fails. The error
    // state still lets the resident retry the missing data.
    final notifications = _generateNotifications(
      documentRequests: documentRequests,
      announcements: announcements,
      residentNotifications: residentNotificationResult.data ?? [],
    );

    return DashboardData(
      user: currentUser,
      announcements: announcements,
      documentRequests: documentRequests,
      activities: activities,
      notifications: notifications,
      queueStatus: queueStatus,
      hasNotificationsError: hasNotificationsError,
      notificationsErrorMessage: notificationErrors.isEmpty
          ? null
          : notificationErrors.join('; '),
      hasAnnouncementsError: annResult.failed,
      hasDocumentRequestsError: docResult.failed,
    );
  }

  Future<UserModel?> _fetchUserProfile() async {
    try {
      final response = await apiClient.get('/auth/me/', requiresAuth: true);
      final Map<String, dynamic> data = jsonDecode(
        utf8.decode(response.bodyBytes),
      );
      final user = UserModel.fromJson(data);
      await storageService.saveUser(user);
      return user;
    } catch (_) {
      return null;
    }
  }

  Future<_FetchResult<List<AnnouncementModel>>> _fetchAnnouncements() async {
    try {
      final response = await apiClient.get(
        '/announcements/',
        requiresAuth: true,
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final List<dynamic> list =
            (data is Map<String, dynamic> ? data['results'] : data) ?? [];
        final items = list
            .map(
              (item) =>
                  AnnouncementModel.fromJson(item as Map<String, dynamic>),
            )
            .toList();
        return _FetchResult(data: items);
      } else {
        return _FetchResult(
          data: [],
          failed: true,
          statusCode: response.statusCode,
          errorMessage: 'HTTP ${response.statusCode}',
        );
      }
    } catch (e) {
      final int? statusCode = e is ApiException ? e.statusCode : null;
      final String msg = e is ApiException && e.statusCode != null
          ? 'HTTP ${e.statusCode}'
          : e.toString();
      return _FetchResult(
        data: [],
        failed: true,
        statusCode: statusCode,
        errorMessage: msg,
      );
    }
  }

  Future<_FetchResult<List<DocumentRequestModel>>>
  _fetchDocumentRequests() async {
    try {
      final response = await apiClient.get(
        '/document-requests/',
        requiresAuth: true,
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final List<dynamic> list =
            (data is Map<String, dynamic> ? data['results'] : data) ?? [];
        final items = list
            .map(
              (item) =>
                  DocumentRequestModel.fromJson(item as Map<String, dynamic>),
            )
            .toList();
        return _FetchResult(data: items);
      } else {
        return _FetchResult(
          data: [],
          failed: true,
          statusCode: response.statusCode,
          errorMessage: 'HTTP ${response.statusCode}',
        );
      }
    } catch (e) {
      final int? statusCode = e is ApiException ? e.statusCode : null;
      final String msg = e is ApiException && e.statusCode != null
          ? 'HTTP ${e.statusCode}'
          : e.toString();
      return _FetchResult(
        data: [],
        failed: true,
        statusCode: statusCode,
        errorMessage: msg,
      );
    }
  }

  Future<_FetchResult<List<NotificationItemModel>>>
  _fetchResidentNotifications() async {
    try {
      final response = await apiClient.get(
        '/resident-notifications/',
        requiresAuth: true,
      );
      if (response.statusCode != 200) {
        return _FetchResult(
          data: [],
          failed: true,
          statusCode: response.statusCode,
          errorMessage: 'HTTP ${response.statusCode}',
        );
      }

      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      final List<dynamic> results =
          (decoded is Map<String, dynamic> ? decoded['results'] : decoded) ??
          [];
      final items = results.map((raw) {
        final item = raw as Map<String, dynamic>;
        final createdAt = DateTime.tryParse(
          item['created_at'] as String? ?? '',
        );
        final type = item['notification_type'] == 'queue'
            ? NotificationType.queue
            : NotificationType.info;
        return NotificationItemModel(
          id: 'resident-${item['id']}',
          title: item['title'] as String? ?? 'KapitBayan update',
          category: type == NotificationType.queue
              ? 'Queue Alert'
              : 'Service Update',
          description: item['message'] as String?,
          timestamp: createdAt ?? DateTime.now(),
          type: type,
          actionRoute: type == NotificationType.queue ? 'queue' : null,
        );
      }).toList();
      return _FetchResult(data: items);
    } catch (error) {
      final int? statusCode = error is ApiException ? error.statusCode : null;
      final String message = error is ApiException && error.statusCode != null
          ? 'HTTP ${error.statusCode}'
          : error.runtimeType.toString();
      return _FetchResult(
        data: [],
        failed: true,
        statusCode: statusCode,
        errorMessage: message,
      );
    }
  }

  Future<List<ActivityScheduleModel>> _fetchActivities() async {
    try {
      final response = await apiClient.get('/activities/', requiresAuth: true);
      final data = jsonDecode(utf8.decode(response.bodyBytes));
      final List<dynamic> list =
          (data is Map<String, dynamic> ? data['results'] : data) ?? [];
      return list
          .map(
            (item) =>
                ActivityScheduleModel.fromJson(item as Map<String, dynamic>),
          )
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>?> _fetchLiveQueue() async {
    try {
      final response = await apiClient.get(
        '/tickets/live-status/',
        requiresAuth: true,
      );
      return jsonDecode(utf8.decode(response.bodyBytes))
          as Map<String, dynamic>?;
    } catch (_) {
      return null;
    }
  }

  /// Synthesizes recent notifications list from live requests and announcements
  List<NotificationItemModel> _generateNotifications({
    required List<DocumentRequestModel> documentRequests,
    required List<AnnouncementModel> announcements,
    required List<NotificationItemModel> residentNotifications,
  }) {
    final List<NotificationItemModel> list = [...residentNotifications];

    // Map document status updates
    for (final doc in documentRequests) {
      if (doc.isReadyForPickup || doc.isReleased) {
        list.add(
          NotificationItemModel(
            id: 'doc-${doc.id}',
            title: '${doc.documentType} Approved',
            category: 'Document Services',
            timestamp: doc.updatedAt ?? doc.createdAt ?? DateTime.now(),
            type: NotificationType.approved,
          ),
        );
      }
    }

    // Map announcements as community alerts
    for (final ann in announcements) {
      list.add(
        NotificationItemModel(
          id: 'ann-${ann.id}',
          title: ann.title,
          category: 'Community Alert',
          timestamp: ann.createdAt ?? DateTime.now(),
          type: ann.isPinned ? NotificationType.warning : NotificationType.info,
        ),
      );
    }

    // Sort by most recent timestamp descending and limit to top 5
    list.sort((a, b) => b.timestamp.compareTo(a.timestamp));
    return list.take(5).toList();
  }
}
