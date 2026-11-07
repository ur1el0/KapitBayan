import 'dart:convert';

import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../models/queue_ticket_model.dart';
import 'storage_service.dart';

/// Exception thrown when queue service operations fail
class QueueServiceException implements Exception {
  final String message;
  final int? statusCode;

  const QueueServiceException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

/// Service managing queue ticketing, live desk broadcast status, and queue history
class QueueService {
  final ApiClient apiClient;
  final StorageService storageService;
  bool _lastTicketsUsedOfflineSnapshot = false;
  DateTime? _lastTicketsSnapshotSavedAt;
  bool _lastTicketsSnapshotTruncated = false;

  QueueService({required this.apiClient, required this.storageService});

  /// Loads one of the authenticated resident's tickets for a push notification.
  /// The API scopes this detail lookup to the signed-in resident.
  Future<QueueTicketModel> fetchTicket(int ticketId) async {
    final response = await apiClient.get(
      '/tickets/$ticketId/',
      requiresAuth: true,
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw QueueServiceException(
        'Unable to load this queue ticket (HTTP ${response.statusCode}).',
        statusCode: response.statusCode,
      );
    }

    final data = jsonDecode(utf8.decode(response.bodyBytes));
    if (data is! Map<String, dynamic>) {
      throw const QueueServiceException(
        'The queue ticket response was invalid.',
      );
    }
    return QueueTicketModel.fromJson(data);
  }

  /// Fetches real-time queue live status and user active tickets concurrently
  Future<QueueLiveStatusModel> fetchQueueStatus() async {
    _lastTicketsUsedOfflineSnapshot = false;
    _lastTicketsSnapshotSavedAt = null;
    _lastTicketsSnapshotTruncated = false;
    Map<String, dynamic>? liveStatusJson;
    List<QueueTicketModel> userTickets = [];
    bool liveStatusFailed = false;
    bool userTicketsFailed = false;
    String? liveStatusErrorMessage;
    int? liveStatusStatusCode;
    String? userTicketsErrorMessage;
    int? userTicketsStatusCode;

    Future<void> fetchLiveStatus() async {
      try {
        final liveStatusRes = await apiClient.get(
          '/tickets/live-status/',
          requiresAuth: true,
        );
        if (liveStatusRes.statusCode == 200) {
          liveStatusJson =
              jsonDecode(utf8.decode(liveStatusRes.bodyBytes))
                  as Map<String, dynamic>;
        } else {
          liveStatusFailed = true;
          liveStatusStatusCode = liveStatusRes.statusCode;
          liveStatusErrorMessage = 'HTTP ${liveStatusRes.statusCode}';
        }
      } catch (e) {
        liveStatusFailed = true;
        if (e is ApiException) {
          liveStatusStatusCode = e.statusCode;
          liveStatusErrorMessage = e.statusCode != null
              ? 'HTTP ${e.statusCode}'
              : e.message;
        } else {
          liveStatusErrorMessage = e.toString();
        }
      }
    }

    Future<void> fetchUserTickets() async {
      try {
        final userTicketsRes = await apiClient.get(
          '/tickets/',
          requiresAuth: true,
        );
        if (userTicketsRes.statusCode == 200) {
          final data = jsonDecode(utf8.decode(userTicketsRes.bodyBytes));
          final list =
              (data is Map<String, dynamic>
                  ? data['results'] as List<dynamic>?
                  : data as List<dynamic>?) ??
              [];
          userTickets = list
              .map(
                (item) =>
                    QueueTicketModel.fromJson(item as Map<String, dynamic>),
              )
              .toList();
          try {
            await storageService.saveOfflineSnapshot(
              'queue_tickets',
              userTickets
                  .map((ticket) {
                    final record = ticket.toJson();
                    record['resident_name'] = null;
                    return record;
                  })
                  .toList(growable: false),
            );
          } catch (_) {
            // Keep the live queue usable if encrypted storage cannot be written.
          }
        } else {
          userTicketsFailed = true;
          userTicketsStatusCode = userTicketsRes.statusCode;
          userTicketsErrorMessage = 'HTTP ${userTicketsRes.statusCode}';
        }
      } on NetworkException catch (e) {
        userTicketsFailed = true;
        userTicketsErrorMessage = e.message;
        try {
          final snapshot = await storageService.readOfflineSnapshot(
            'queue_tickets',
          );
          if (snapshot != null) {
            userTickets = snapshot.records
                .map(QueueTicketModel.fromJson)
                .toList(growable: false);
            userTicketsFailed = false;
            userTicketsErrorMessage = null;
            _lastTicketsUsedOfflineSnapshot = true;
            _lastTicketsSnapshotSavedAt = snapshot.savedAt;
            _lastTicketsSnapshotTruncated = snapshot.isTruncated;
          }
        } catch (_) {
          // Keep the normal retryable error if encrypted storage is unavailable.
        }
      } catch (e) {
        userTicketsFailed = true;
        if (e is ApiException) {
          userTicketsStatusCode = e.statusCode;
          userTicketsErrorMessage = e.statusCode != null
              ? 'HTTP ${e.statusCode}'
              : e.message;
        } else {
          userTicketsErrorMessage = e.toString();
        }
      }
    }

    // Run both independent queries concurrently
    await Future.wait([fetchLiveStatus(), fetchUserTickets()]);

    // If both endpoints fail, throw service exception for full-screen retryable error
    if (liveStatusFailed && userTicketsFailed) {
      throw QueueServiceException(
        'Unable to load queue data: live status ($liveStatusErrorMessage), tickets ($userTicketsErrorMessage)',
        statusCode: liveStatusStatusCode ?? userTicketsStatusCode,
      );
    }

    return QueueLiveStatusModel.fromJson(
      liveStatusJson: liveStatusJson ?? {},
      userTickets: userTickets,
      hasLiveStatusError: liveStatusFailed,
      hasUserTicketsError: userTicketsFailed,
      liveStatusErrorMessage: liveStatusFailed ? liveStatusErrorMessage : null,
      userTicketsErrorMessage: userTicketsFailed
          ? userTicketsErrorMessage
          : null,
      isShowingOfflineTicketSnapshot: _lastTicketsUsedOfflineSnapshot,
      offlineTicketSnapshotSavedAt: _lastTicketsSnapshotSavedAt,
      offlineTicketsTruncated: _lastTicketsSnapshotTruncated,
      errorMessage: userTicketsFailed
          ? 'Unable to load active tickets ($userTicketsErrorMessage)'
          : (liveStatusFailed
                ? 'Unable to load live queue status ($liveStatusErrorMessage)'
                : null),
    );
  }

  /// Creates a new queue ticket for the active resident
  Future<QueueTicketModel> requestTicket({
    required String serviceType,
    String? notes,
    int? documentRequestId,
  }) async {
    final response = await apiClient.post(
      '/tickets/',
      requiresAuth: true,
      body: {
        'service_type': serviceType,
        'notes': ?notes,
        'document_request_id': ?documentRequestId,
      },
    );

    final data =
        jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    return QueueTicketModel.fromJson(data);
  }
}
