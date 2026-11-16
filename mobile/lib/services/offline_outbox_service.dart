import 'dart:math';

import '../core/network/api_client.dart';
import 'storage_service.dart';

/// Thrown when an action is successfully queued to the offline outbox during a network drop.
class OfflineQueuedException implements Exception {
  final String idempotencyKey;
  final String message;

  const OfflineQueuedException({
    required this.idempotencyKey,
    required this.message,
  });

  @override
  String toString() => message;
}

/// A queued resident submission awaiting network connectivity to upload.
class QueuedDocumentSubmission {
  final String idempotencyKey;
  final String documentType;
  final int? offeringId;
  final String urgencyTag;
  final String? purpose;
  final DateTime createdAt;
  final int retryCount;

  const QueuedDocumentSubmission({
    required this.idempotencyKey,
    required this.documentType,
    this.offeringId,
    required this.urgencyTag,
    this.purpose,
    required this.createdAt,
    this.retryCount = 0,
  });

  Map<String, dynamic> toJson() => {
    'idempotency_key': idempotencyKey,
    'document_type': documentType,
    'offering_id': offeringId,
    'urgency_tag': urgencyTag,
    'purpose': purpose,
    'created_at': createdAt.toIso8601String(),
    'retry_count': retryCount,
  };

  factory QueuedDocumentSubmission.fromJson(Map<String, dynamic> json) =>
      QueuedDocumentSubmission(
        idempotencyKey: json['idempotency_key'] as String,
        documentType: json['document_type'] as String,
        offeringId: json['offering_id'] as int?,
        urgencyTag: (json['urgency_tag'] as String?) ?? 'REGULAR',
        purpose: json['purpose'] as String?,
        createdAt:
            DateTime.tryParse(json['created_at']?.toString() ?? '') ??
            DateTime.now().toUtc(),
        retryCount: (json['retry_count'] as num?)?.toInt() ?? 0,
      );

  QueuedDocumentSubmission incrementRetry() => QueuedDocumentSubmission(
    idempotencyKey: idempotencyKey,
    documentType: documentType,
    offeringId: offeringId,
    urgencyTag: urgencyTag,
    purpose: purpose,
    createdAt: createdAt,
    retryCount: retryCount + 1,
  );
}

/// Result of an outbox processing / flush attempt.
class OutboxFlushResult {
  final int processedCount;
  final int remainingCount;
  final List<String> submittedKeys;

  const OutboxFlushResult({
    required this.processedCount,
    required this.remainingCount,
    required this.submittedKeys,
  });
}

/// Service managing client-side offline queued submissions and automated retries.
class OfflineOutboxService {
  final StorageService storageService;
  final ApiClient apiClient;

  OfflineOutboxService({
    required this.storageService,
    required this.apiClient,
  });

  /// Generates a cryptographically secure RFC 4122 v4 UUID string.
  static String generateIdempotencyKey() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40; // Version 4
    bytes[8] = (bytes[8] & 0x3f) | 0x80; // Variant 10
    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
  }

  /// Enqueues a failed or offline document request into secure local storage.
  Future<String> enqueueDocumentRequest({
    required String documentType,
    int? offeringId,
    String urgencyTag = 'REGULAR',
    String? purpose,
    String? idempotencyKey,
  }) async {
    final key = idempotencyKey ?? generateIdempotencyKey();
    final submission = QueuedDocumentSubmission(
      idempotencyKey: key,
      documentType: documentType,
      offeringId: offeringId,
      urgencyTag: urgencyTag,
      purpose: purpose,
      createdAt: DateTime.now().toUtc(),
    );

    final existing = await getQueuedDocumentSubmissions();
    if (existing.any((e) => e.idempotencyKey == key)) return key;

    final updated = [...existing, submission];
    await storageService.saveOutboxRecords(
      updated.map((e) => e.toJson()).toList(),
    );
    return key;
  }

  /// Lists all document requests currently awaiting connectivity.
  Future<List<QueuedDocumentSubmission>> getQueuedDocumentSubmissions() async {
    final raw = await storageService.readOutboxRecords();
    return raw.map(QueuedDocumentSubmission.fromJson).toList();
  }

  /// Returns the number of items currently pending upload.
  Future<int> getPendingCount() async {
    final items = await getQueuedDocumentSubmissions();
    return items.length;
  }

  /// Clears all queued outbox records.
  Future<void> clearOutbox() async {
    await storageService.saveOutboxRecords(const []);
  }

  /// Flushes the outbox by retrying pending submissions against the backend.
  Future<OutboxFlushResult> flushOutbox() async {
    final queued = await getQueuedDocumentSubmissions();
    if (queued.isEmpty) {
      return const OutboxFlushResult(
        processedCount: 0,
        remainingCount: 0,
        submittedKeys: [],
      );
    }

    final remaining = <QueuedDocumentSubmission>[];
    final submitted = <String>[];

    for (var i = 0; i < queued.length; i++) {
      final item = queued[i];
      try {
        final response = await apiClient.post(
          '/document-requests/',
          body: {
            'document_type': item.documentType,
            if (item.offeringId != null) 'offering_id': item.offeringId,
            'urgency_tag': item.urgencyTag.toUpperCase(),
            if (item.purpose != null) 'purpose': item.purpose,
          },
          headers: {'Idempotency-Key': item.idempotencyKey},
          requiresAuth: true,
        );

        if (response.statusCode == 200 || response.statusCode == 201) {
          submitted.add(item.idempotencyKey);
        } else if (response.statusCode >= 400 && response.statusCode < 500) {
          // Client/validation error (e.g. resident unverified): drop to prevent poison queue.
        } else {
          // 5xx server error: retain for retry.
          remaining.add(item.incrementRetry());
        }
      } catch (_) {
        // Network connection exception / timeout: retain item and remainder of queue.
        remaining.add(item.incrementRetry());
        if (i + 1 < queued.length) {
          remaining.addAll(queued.sublist(i + 1));
        }
        break;
      }
    }

    await storageService.saveOutboxRecords(
      remaining.map((e) => e.toJson()).toList(),
    );

    return OutboxFlushResult(
      processedCount: submitted.length,
      remainingCount: remaining.length,
      submittedKeys: submitted,
    );
  }
}
