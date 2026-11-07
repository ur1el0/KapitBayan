import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/services/queue_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('ticket request sends no client-selected priority field', () async {
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    Map<String, dynamic>? submittedBody;
    final client = MockClient((request) async {
      submittedBody = jsonDecode(request.body) as Map<String, dynamic>;
      return http.Response(
        jsonEncode({
          'ticket_id': 1,
          'ticket_number': 'T001',
          'service_type': 'Barangay Clearance',
          'status': 'WAITING',
          'is_priority': false,
        }),
        201,
        headers: {'content-type': 'application/json'},
      );
    });
    final service = QueueService(
      apiClient: ApiClient(client: client, baseUrl: 'https://kapitbayan.test'),
      storageService: StorageService(preferences),
    );

    final ticket = await service.requestTicket(
      serviceType: 'Barangay Clearance',
      notes: 'One copy',
    );

    expect(ticket.ticketNumber, 'T001');
    expect(submittedBody, {
      'service_type': 'Barangay Clearance',
      'notes': 'One copy',
    });
    expect(submittedBody!.containsKey('is_priority'), isFalse);
  });

  test('fetchTicket requests an authenticated ticket detail URL', () async {
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    String? requestedPath;
    final client = MockClient((request) async {
      requestedPath = request.url.path;
      return http.Response(
        jsonEncode({
          'ticket_id': 41,
          'ticket_number': 'A-041',
          'service_type': 'Barangay Clearance',
          'status': 'SERVING',
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final service = QueueService(
      apiClient: ApiClient(client: client, baseUrl: 'https://kapitbayan.test'),
      storageService: StorageService(preferences),
    );

    final ticket = await service.fetchTicket(41);

    expect(requestedPath, '/tickets/41/');
    expect(ticket.ticketNumber, 'A-041');
    expect(ticket.status, 'SERVING');
  });

  test(
    'fetchQueueStatus preserves user tickets when live status endpoint fails',
    () async {
      SharedPreferences.setMockInitialValues({});
      final preferences = await SharedPreferences.getInstance();
      final client = MockClient((request) async {
        if (request.url.path == '/tickets/live-status/') {
          return http.Response('Server error', 500);
        }
        return http.Response(
          jsonEncode([
            {
              'ticket_id': 99,
              'ticket_number': 'T-099',
              'service_type': 'Barangay Clearance',
              'status': 'WAITING',
            },
          ]),
          200,
          headers: {'content-type': 'application/json'},
        );
      });
      final service = QueueService(
        apiClient: ApiClient(
          client: client,
          baseUrl: 'https://kapitbayan.test',
        ),
        storageService: StorageService(preferences),
      );

      final status = await service.fetchQueueStatus();
      expect(status.hasLiveStatusError, isTrue);
      expect(status.hasUserTicketsError, isFalse);
      expect(status.userTicket, isNotNull);
      expect(status.userTicket!.ticketNumber, equals('T-099'));
      expect(status.liveStatusErrorMessage, contains('HTTP 500'));
    },
  );

  test(
    'fetchQueueStatus flags partial failure and preserves live status when user tickets endpoint fails',
    () async {
      SharedPreferences.setMockInitialValues({});
      final preferences = await SharedPreferences.getInstance();
      final client = MockClient((request) async {
        if (request.url.path == '/tickets/live-status/') {
          return http.Response(
            jsonEncode({
              'current_ticket': 'B-101',
              'current_service': 'Clearance',
              'total_waiting': 3,
              'avg_wait_mins': 10,
              'recent_completed': [],
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        // User tickets endpoint fails with 503
        return http.Response('Service unavailable', 503);
      });
      final service = QueueService(
        apiClient: ApiClient(
          client: client,
          baseUrl: 'https://kapitbayan.test',
        ),
        storageService: StorageService(preferences),
      );

      final status = await service.fetchQueueStatus();
      expect(status.hasLiveStatusError, isFalse);
      expect(status.currentTicket, 'B-101');
      expect(status.totalWaiting, 3);
      expect(status.userTicket, isNull);
      expect(status.hasUserTicketsError, isTrue);
      expect(status.userTicketsErrorMessage, contains('HTTP 503'));
      expect(status.errorMessage, contains('Unable to load active tickets'));
    },
  );

  test(
    'fetchQueueStatus throws QueueServiceException when both endpoints fail',
    () async {
      SharedPreferences.setMockInitialValues({});
      final preferences = await SharedPreferences.getInstance();
      final client = MockClient((request) async {
        return http.Response('Server error', 500);
      });
      final service = QueueService(
        apiClient: ApiClient(
          client: client,
          baseUrl: 'https://kapitbayan.test',
        ),
        storageService: StorageService(preferences),
      );

      expect(
        () => service.fetchQueueStatus(),
        throwsA(isA<QueueServiceException>()),
      );
    },
  );

  test(
    'fetchQueueStatus returns true empty model without fabricated fallbacks',
    () async {
      SharedPreferences.setMockInitialValues({});
      final preferences = await SharedPreferences.getInstance();
      final client = MockClient((request) async {
        if (request.url.path == '/tickets/live-status/') {
          return http.Response(
            jsonEncode({
              'current_ticket': null,
              'current_service': 'General Service',
              'total_waiting': 0,
              'avg_wait_mins': 0,
              'recent_completed': [],
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response(
          jsonEncode({'results': []}),
          200,
          headers: {'content-type': 'application/json'},
        );
      });
      final service = QueueService(
        apiClient: ApiClient(
          client: client,
          baseUrl: 'https://kapitbayan.test',
        ),
        storageService: StorageService(preferences),
      );

      final status = await service.fetchQueueStatus();
      expect(status.currentTicket, isNull);
      expect(status.totalWaiting, 0);
      expect(status.userTicket, isNull);
      expect(status.recentCompleted, isEmpty);
      expect(status.hasUserTicketsError, isFalse);
      expect(status.hasLiveStatusError, isFalse);
    },
  );
}
