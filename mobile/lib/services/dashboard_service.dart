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
  final bool usedOfflineCache;
  final bool offlineCacheTruncated;
  final DateTime? cachedAt;
  final String? errorMessage;
  final int? statusCode;

  const _FetchResult({
    this.data,
    this.failed = false,
    this.usedOfflineCache = false,
    this.offlineCacheTruncated = false,
    this.cachedAt,
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
  final bool isShowingOfflineSnapshot;
  final DateTime? offlineSnapshotSavedAt;
  final bool offlineRequestsTruncated;
  final bool isShowingOfflineAnnouncements;
  final DateTime? offlineAnnouncementsSavedAt;

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
    this.isShowingOfflineSnapshot = false,
    this.offlineSnapshotSavedAt,
    this.offlineRequestsTruncated = false,
    this.isShowingOfflineAnnouncements = false,
    this.offlineAnnouncementsSavedAt,
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

    final offlineCacheDates = [
      annResult.cachedAt,
      docResult.cachedAt,
    ].whereType<DateTime>().toList()..sort();
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
      isShowingOfflineSnapshot:
          annResult.usedOfflineCache || docResult.usedOfflineCache,
      offlineSnapshotSavedAt: offlineCacheDates.isEmpty
          ? null
          : offlineCacheDates.first,
      offlineRequestsTruncated:
          docResult.usedOfflineCache && docResult.offlineCacheTruncated,
      isShowingOfflineAnnouncements: annResult.usedOfflineCache,
      offlineAnnouncementsSavedAt: annResult.cachedAt,
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
        try {
          await storageService.saveOfflineSnapshot(
            'announcements',
            items
                .map((item) {
                  final record = item.toJson();
                  // Keep text available offline without implying remote images are cached.
                  record['image'] = null;
                  return record;
                })
                .toList(growable: false),
          );
        } catch (_) {
          // A cache write must not turn a successful live request into an error.
        }
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
      if (e is NetworkException) {
        try {
          final snapshot = await storageService.readOfflineSnapshot(
            'announcements',
          );
          if (snapshot != null) {
            return _FetchResult(
              data: snapshot.records
                  .map(AnnouncementModel.fromJson)
                  .toList(growable: false),
              failed: true,
              usedOfflineCache: true,
              cachedAt: snapshot.savedAt,
              errorMessage: 'Offline snapshot',
            );
          }
        } catch (_) {
          // Fall through to the visible load error when secure storage is unavailable.
        }
      }
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
        try {
          await storageService.saveOfflineSnapshot(
            'document_requests',
            items
                .map((item) {
                  final record = item.toJson();
                  record['payment_proof_url'] = null;
                  return record;
                })
                .toList(growable: false),
            mergeWithExisting: true,
          );
        } catch (_) {
          // A cache write must not turn a successful live request into an error.
        }
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
      if (e is NetworkException) {
        try {
          final snapshot = await storageService.readOfflineSnapshot(
            'document_requests',
          );
          if (snapshot != null) {
            return _FetchResult(
              data: snapshot.records
                  .map(DocumentRequestModel.fromJson)
                  .toList(growable: false),
              failed: true,
              usedOfflineCache: true,
              offlineCacheTruncated: snapshot.isTruncated,
              cachedAt: snapshot.savedAt,
              errorMessage: 'Offline snapshot',
            );
          }
        } catch (_) {
          // Fall through to the visible load error when secure storage is unavailable.
        }
      }
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
          isRead: item['is_read'] is bool ? item['is_read'] as bool : null,
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

  /// Marks a persisted resident alert as read. Locally synthesized summaries
  /// do not have a backend read state and are ignored.
  Future<void> markNotificationRead(NotificationItemModel notification) async {
    const prefix = 'resident-';
    if (!notification.isUnread || !notification.id.startsWith(prefix)) return;

    final notificationId = int.tryParse(
      notification.id.substring(prefix.length),
    );
    if (notificationId == null) return;

    final response = await apiClient.patch(
      '/resident-notifications/$notificationId/',
      body: const {'is_read': true},
      requiresAuth: true,
    );
    if (response.statusCode != 200) {
      throw ApiException(
        'Could not mark notification as read (HTTP ${response.statusCode}).',
        statusCode: response.statusCode,
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
