import 'dart:convert';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../models/activity_schedule_model.dart';
import '../models/document_request_model.dart';
import '../models/user_model.dart';
import 'storage_service.dart';

/// Aggregated data container for the Resident Community & Appointments Schedule screen
class ScheduleData {
  final UserModel? user;
  final List<ActivityScheduleModel> activities;
  final List<DocumentRequestModel> documentRequests;
  final bool hasActivitiesError;
  final bool hasAppointmentsError;
  final String? errorMessage;
  final bool isShowingOfflineRequestSnapshot;
  final DateTime? offlineRequestSnapshotSavedAt;
  final bool offlineRequestsTruncated;

  const ScheduleData({
    this.user,
    this.activities = const [],
    this.documentRequests = const [],
    this.hasActivitiesError = false,
    this.hasAppointmentsError = false,
    this.errorMessage,
    this.isShowingOfflineRequestSnapshot = false,
    this.offlineRequestSnapshotSavedAt,
    this.offlineRequestsTruncated = false,
  });

  /// Returns activities matching the specific calendar day
  List<ActivityScheduleModel> getActivitiesForDate(DateTime date) {
    return activities.where((a) => a.isSameDay(date)).toList();
  }

  /// Returns user's active document requests / pickup appointments
  List<DocumentRequestModel> get activeAppointments {
    return documentRequests
        .where(
          (doc) => doc.isReadyForPickup || doc.isProcessing || doc.isPending,
        )
        .toList();
  }

  /// Returns user's document requests associated with a specific date
  List<DocumentRequestModel> getAppointmentsForDate(DateTime date) {
    return documentRequests.where((doc) {
      final docDate = doc.createdAt ?? doc.updatedAt;
      if (docDate != null) {
        return docDate.year == date.year &&
            docDate.month == date.month &&
            docDate.day == date.day;
      }
      return false;
    }).toList();
  }
}

/// Custom exception thrown when schedule service fails to fetch critical data
class ScheduleServiceException implements Exception {
  final String message;
  const ScheduleServiceException(this.message);

  @override
  String toString() => message;
}

/// Service coordinating community schedule activities and resident appointment data
class ScheduleService {
  final ApiClient apiClient;
  final StorageService storageService;
  bool _lastRequestsUsedOfflineSnapshot = false;
  DateTime? _lastRequestsSnapshotSavedAt;
  bool _lastRequestsSnapshotTruncated = false;

  ScheduleService({required this.apiClient, required this.storageService});

  /// Fetches schedule activities and user document appointments concurrently
  Future<ScheduleData> fetchScheduleData() async {
    _lastRequestsUsedOfflineSnapshot = false;
    _lastRequestsSnapshotSavedAt = null;
    _lastRequestsSnapshotTruncated = false;
    final cachedUser = storageService.getUser();
    UserModel? currentUser = cachedUser;
    List<ActivityScheduleModel> activities = [];
    List<DocumentRequestModel> documentRequests = [];
    bool hasActivitiesError = false;
    bool hasAppointmentsError = false;

    final results = await Future.wait([
      _fetchUserProfile(),
      _fetchActivities().catchError((_) {
        hasActivitiesError = true;
        return <ActivityScheduleModel>[];
      }),
      _fetchDocumentRequests().catchError((_) {
        hasAppointmentsError = true;
        return <DocumentRequestModel>[];
      }),
    ]);

    if (results[0] != null) currentUser = results[0] as UserModel;
    activities = results[1] as List<ActivityScheduleModel>;
    documentRequests = results[2] as List<DocumentRequestModel>;

    if (hasActivitiesError && hasAppointmentsError) {
      throw const ScheduleServiceException(
        'Unable to load schedule data from server.',
      );
    }

    return ScheduleData(
      user: currentUser,
      activities: activities,
      documentRequests: documentRequests,
      hasActivitiesError: hasActivitiesError,
      hasAppointmentsError: hasAppointmentsError,
      errorMessage: hasActivitiesError || hasAppointmentsError
          ? 'Some schedule details could not be updated.'
          : null,
      isShowingOfflineRequestSnapshot: _lastRequestsUsedOfflineSnapshot,
      offlineRequestSnapshotSavedAt: _lastRequestsSnapshotSavedAt,
      offlineRequestsTruncated: _lastRequestsSnapshotTruncated,
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

  Future<List<ActivityScheduleModel>> _fetchActivities() async {
    final response = await apiClient.get('/activities/', requiresAuth: true);
    if (response.statusCode >= 400) {
      throw Exception('Activities request failed: ${response.statusCode}');
    }
    final dynamic decoded = jsonDecode(utf8.decode(response.bodyBytes));
    final List<dynamic> list = decoded is Map && decoded.containsKey('results')
        ? decoded['results'] as List<dynamic>
        : (decoded is List ? decoded : const []);
    return list
        .map(
          (item) =>
              ActivityScheduleModel.fromJson(item as Map<String, dynamic>),
        )
        .toList();
  }

  Future<List<DocumentRequestModel>> _fetchDocumentRequests() async {
    try {
      final response = await apiClient.get(
        '/document-requests/',
        requiresAuth: true,
      );
      if (response.statusCode >= 400) {
        throw Exception('Document requests failed: ${response.statusCode}');
      }
      final dynamic decoded = jsonDecode(utf8.decode(response.bodyBytes));
      final List<dynamic> list =
          decoded is Map && decoded.containsKey('results')
          ? decoded['results'] as List<dynamic>
          : (decoded is List ? decoded : const []);
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
        // Keep the live schedule even if encrypted storage is unavailable.
      }
      return items;
    } on NetworkException {
      final snapshot = await storageService.readOfflineSnapshot(
        'document_requests',
      );
      if (snapshot == null) rethrow;
      _lastRequestsUsedOfflineSnapshot = true;
      _lastRequestsSnapshotSavedAt = snapshot.savedAt;
      _lastRequestsSnapshotTruncated = snapshot.isTruncated;
      return snapshot.records
          .map(DocumentRequestModel.fromJson)
          .toList(growable: false);
    }
  }
}
