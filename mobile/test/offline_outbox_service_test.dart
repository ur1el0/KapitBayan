import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/models/user_model.dart';
import 'package:mobile/services/document_service.dart';
import 'package:mobile/services/offline_outbox_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late StorageService storageService;

  const residentUser = UserModel(
    id: 42,
    username: 'juan_delacruz',
    email: 'juan@example.com',
    fullName: 'Juan Dela Cruz',
    role: 'RESIDENT',
    barangayId: 10,
    isVerified: true,
  );

  setUp(() async {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
    storageService = await StorageService.init();
    await storageService.saveUser(residentUser);
  });

  test('generateIdempotencyKey generates valid RFC 4122 v4 UUID format', () {
    final uuid = OfflineOutboxService.generateIdempotencyKey();
    final uuidRegex = RegExp(
      r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
      caseSensitive: false,
    );
    expect(uuidRegex.hasMatch(uuid), isTrue);
  });

  test('enqueues document requests and tracks pending count', () async {
    final mockClient = MockClient((_) async => http.Response('{}', 200));
    final apiClient = ApiClient(client: mockClient, baseUrl: 'https://test.api');
    final outboxService = OfflineOutboxService(
      storageService: storageService,
      apiClient: apiClient,
    );

    expect(await outboxService.getPendingCount(), 0);

    final key = await outboxService.enqueueDocumentRequest(
      documentType: 'Barangay Clearance',
      urgencyTag: 'REGULAR',
      purpose: 'Employment requirement',
    );

    expect(key.isNotEmpty, isTrue);
    expect(await outboxService.getPendingCount(), 1);

    final pending = await outboxService.getQueuedDocumentSubmissions();
    expect(pending.length, 1);
    expect(pending.first.documentType, 'Barangay Clearance');
    expect(pending.first.purpose, 'Employment requirement');
    expect(pending.first.idempotencyKey, key);
  });

  test('flushOutbox sends request with Idempotency-Key and clears queue on success', () async {
    final sentHeaders = <String, String>{};
    final sentBodies = <String>[];

    final mockClient = MockClient((request) async {
      sentHeaders.addAll(request.headers);
      sentBodies.add(request.body);
      return http.Response(
        jsonEncode({
          'id': 101,
          'document_type': 'Barangay Clearance',
          'status': 'PENDING',
        }),
        201,
      );
    });

    final apiClient = ApiClient(client: mockClient, baseUrl: 'https://test.api');
    apiClient.setAuthCredentials(accessToken: 'test-token');
    final outboxService = OfflineOutboxService(
      storageService: storageService,
      apiClient: apiClient,
    );

    final key = await outboxService.enqueueDocumentRequest(
      documentType: 'Barangay Clearance',
      urgencyTag: 'REGULAR',
      purpose: 'Job application',
    );

    expect(await outboxService.getPendingCount(), 1);

    final result = await outboxService.flushOutbox();

    expect(result.processedCount, 1);
    expect(result.remainingCount, 0);
    expect(result.submittedKeys, [key]);
    final capturedKey =
        sentHeaders['Idempotency-Key'] ?? sentHeaders['idempotency-key'];
    expect(capturedKey, key);

    // Queue is now empty
    expect(await outboxService.getPendingCount(), 0);
  });

  test('flushOutbox retains items when network connection fails (offline mode)', () async {
    final mockClient = MockClient((_) async {
      throw const SocketException('No route to host');
    });

    final apiClient = ApiClient(client: mockClient, baseUrl: 'https://test.api');
    apiClient.setAuthCredentials(accessToken: 'test-token');
    final outboxService = OfflineOutboxService(
      storageService: storageService,
      apiClient: apiClient,
    );

    await outboxService.enqueueDocumentRequest(
      documentType: 'Certificate of Indigency',
      urgencyTag: 'REGULAR',
      purpose: 'Medical subsidy',
    );

    expect(await outboxService.getPendingCount(), 1);

    final result = await outboxService.flushOutbox();

    expect(result.processedCount, 0);
    expect(result.remainingCount, 1);

    // Submission is retained in queue for later retry
    final pending = await outboxService.getQueuedDocumentSubmissions();
    expect(pending.length, 1);
    expect(pending.first.retryCount, 1);
  });

  test('DocumentService automatically enqueues to outbox when network drops during submission', () async {
    final mockClient = MockClient((_) async {
      throw const SocketException('Network is unreachable');
    });
    final apiClient = ApiClient(client: mockClient, baseUrl: 'https://test.api');
    apiClient.setAuthCredentials(accessToken: 'resident-token');

    final documentService = DocumentService(
      apiClient: apiClient,
      storageService: storageService,
    );

    expect(await documentService.outboxService.getPendingCount(), 0);

    await expectLater(
      documentService.createDocumentRequest(
        documentType: 'Barangay Clearance',
        urgencyTag: 'REGULAR',
        purpose: 'Passport requirement',
      ),
      throwsA(isA<OfflineQueuedException>()),
    );

    expect(await documentService.outboxService.getPendingCount(), 1);
    final queued = await documentService.outboxService.getQueuedDocumentSubmissions();
    expect(queued.first.documentType, 'Barangay Clearance');
    expect(queued.first.purpose, 'Passport requirement');
  });

  test('DocumentService flushes outbox on fetchDocumentRequests when network reconnects', () async {
    var outboxSubmissionsReceived = 0;
    String? receivedIdempotencyKey;

    final mockClient = MockClient((request) async {
      if (request.url.path.contains('/document-requests/')) {
        if (request.method == 'POST') {
          outboxSubmissionsReceived++;
          receivedIdempotencyKey =
              request.headers['Idempotency-Key'] ?? request.headers['idempotency-key'];
          return http.Response(
            jsonEncode({
              'id': 202,
              'document_type': 'Barangay Clearance',
              'status': 'PENDING',
            }),
            201,
          );
        } else if (request.method == 'GET') {
          return http.Response(
            jsonEncode({
              'results': [
                {
                  'id': 202,
                  'document_type': 'Barangay Clearance',
                  'status': 'PENDING',
                  'created_at': DateTime.now().toIso8601String(),
                }
              ]
            }),
            200,
          );
        }
      }
      return http.Response('{}', 200);
    });

    final apiClient = ApiClient(client: mockClient, baseUrl: 'https://test.api');
    apiClient.setAuthCredentials(accessToken: 'resident-token');

    final documentService = DocumentService(
      apiClient: apiClient,
      storageService: storageService,
    );

    final key = await documentService.outboxService.enqueueDocumentRequest(
      documentType: 'Barangay Clearance',
      urgencyTag: 'REGULAR',
      purpose: 'Passport requirement',
    );
    expect(await documentService.outboxService.getPendingCount(), 1);

    final docs = await documentService.fetchDocumentRequests();

    expect(outboxSubmissionsReceived, 1);
    expect(receivedIdempotencyKey, key);
    expect(await documentService.outboxService.getPendingCount(), 0);
    expect(docs.length, 1);
    expect(docs.first.id, 202);
  });
}
