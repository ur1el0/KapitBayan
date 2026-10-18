import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/models/notification_item_model.dart';
import 'package:mobile/models/user_model.dart';
import 'package:mobile/services/dashboard_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'fetchDashboardData returns empty notifications when backend data is empty',
    () async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);
      await storage.saveUser(
        const UserModel(
          id: 1,
          username: 'resident_test',
          email: 'test@example.com',
          role: 'RESIDENT',
          fullName: 'Test User',
          isVerified: true,
        ),
      );

      final client = MockClient((request) async {
        final path = request.url.path;
        if (path.contains('/resident-notifications/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/auth/me/')) {
          return http.Response(
            jsonEncode({
              'id': 1,
              'username': 'resident_test',
              'email': 'test@example.com',
              'role': 'RESIDENT',
              'full_name': 'Test User',
              'is_verified': true,
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/announcements/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/document-requests/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/activities/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/tickets/live-status/')) {
          return http.Response(
            jsonEncode({
              'serving': null,
              'wait_time': '0 mins',
              'recent_completed': [],
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('Not found', 404);
      });

      final service = DashboardService(
        apiClient: ApiClient(
          client: client,
          baseUrl: 'https://kapitbayan.test',
        ),
        storageService: storage,
      );

      final data = await service.fetchDashboardData();

      // Verify notifications is strictly empty - no sample-1 or sample-2 injected
      expect(data.notifications, isEmpty);
      expect(data.announcements, isEmpty);
      expect(data.documentRequests, isEmpty);
      expect(data.pendingRequestsCount, 0);
    },
  );

  test(
    'fetchDashboardData synthesizes notifications from real data only and sorts newest first',
    () async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);

      final client = MockClient((request) async {
        final path = request.url.path;
        if (path.contains('/resident-notifications/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/auth/me/')) {
          return http.Response(
            jsonEncode({
              'id': 1,
              'username': 'resident_test',
              'email': 'test@example.com',
              'role': 'RESIDENT',
              'full_name': 'Test User',
              'is_verified': true,
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/announcements/')) {
          return http.Response(
            jsonEncode([
              {
                'id': 10,
                'title': 'Typhoon Alert',
                'content': 'Stay indoors',
                'is_pinned': true,
                'created_at': '2026-10-12T08:00:00Z',
              },
            ]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/document-requests/')) {
          return http.Response(
            jsonEncode([
              {
                'id': 20,
                'document_type': 'Barangay Clearance',
                'status': 'READY_FOR_PICKUP',
                'updated_at': '2026-10-12T09:00:00Z',
              },
              {
                'id': 21,
                'document_type': 'Certificate of Residency',
                'status': 'PENDING',
                'created_at': '2026-10-12T07:00:00Z',
              },
            ]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/activities/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/tickets/live-status/')) {
          return http.Response(
            jsonEncode({
              'serving': null,
              'wait_time': '0 mins',
              'recent_completed': [],
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('Not found', 404);
      });

      final service = DashboardService(
        apiClient: ApiClient(
          client: client,
          baseUrl: 'https://kapitbayan.test',
        ),
        storageService: storage,
      );

      final data = await service.fetchDashboardData();

      expect(data.notifications.length, 2);
      // Newest is doc-20 (updated at 09:00), followed by ann-10 (created at 08:00)
      expect(data.notifications[0].id, 'doc-20');
      expect(data.notifications[0].title, 'Barangay Clearance Approved');
      expect(data.notifications[0].type, NotificationType.approved);

      expect(data.notifications[1].id, 'ann-10');
      expect(data.notifications[1].title, 'Typhoon Alert');
      expect(data.notifications[1].type, NotificationType.warning);
    },
  );

  test(
    'fetchDashboardData flags hasNotificationsError when announcements endpoint fails',
    () async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);

      final client = MockClient((request) async {
        final path = request.url.path;
        if (path.contains('/resident-notifications/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/auth/me/')) {
          return http.Response(
            jsonEncode({
              'id': 1,
              'username': 'user',
              'email': 'u@e.c',
              'role': 'RESIDENT',
              'full_name': 'User',
            }),
            200,
          );
        }
        if (path.contains('/announcements/')) {
          return http.Response('Internal Server Error', 500);
        }
        if (path.contains('/document-requests/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/activities/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/tickets/live-status/')) {
          return http.Response(
            jsonEncode({'serving': null, 'recent_completed': []}),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('Not found', 404);
      });

      final service = DashboardService(
        apiClient: ApiClient(
          client: client,
          baseUrl: 'https://kapitbayan.test',
        ),
        storageService: storage,
      );

      final data = await service.fetchDashboardData();
      expect(data.hasNotificationsError, isTrue);
      expect(data.hasAnnouncementsError, isTrue);
      expect(
        data.notificationsErrorMessage,
        contains('Unable to load announcements'),
      );
      expect(data.notifications, isEmpty);
    },
  );

  test(
    'fetchDashboardData flags hasNotificationsError when document-requests endpoint fails',
    () async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);

      final client = MockClient((request) async {
        final path = request.url.path;
        if (path.contains('/resident-notifications/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/auth/me/')) {
          return http.Response(
            jsonEncode({
              'id': 1,
              'username': 'user',
              'email': 'u@e.c',
              'role': 'RESIDENT',
              'full_name': 'User',
            }),
            200,
          );
        }
        if (path.contains('/announcements/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/document-requests/')) {
          return http.Response('Service Unavailable', 503);
        }
        if (path.contains('/activities/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/tickets/live-status/')) {
          return http.Response(
            jsonEncode({'serving': null, 'recent_completed': []}),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('Not found', 404);
      });

      final service = DashboardService(
        apiClient: ApiClient(
          client: client,
          baseUrl: 'https://kapitbayan.test',
        ),
        storageService: storage,
      );

      final data = await service.fetchDashboardData();
      expect(data.hasNotificationsError, isTrue);
      expect(data.hasDocumentRequestsError, isTrue);
      expect(
        data.notificationsErrorMessage,
        contains('Unable to load document request updates'),
      );
      expect(data.notifications, isEmpty);
    },
  );

  test(
    'includes persistent queue paging alerts in dashboard notifications',
    () async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);

      final client = MockClient((request) async {
        final path = request.url.path;
        if (path.contains('/auth/me/')) {
          return http.Response(
            jsonEncode({
              'id': 1,
              'username': 'user',
              'email': 'u@e.c',
              'role': 'RESIDENT',
              'full_name': 'User',
            }),
            200,
          );
        }
        if (path.contains('/resident-notifications/')) {
          return http.Response(
            jsonEncode({
              'results': [
                {
                  'id': 72,
                  'notification_type': 'queue',
                  'title': 'Queue ticket T-014 is still being served',
                  'message': 'Please proceed to the service counter.',
                  'data': {'type': 'queue', 'ticket_id': '14'},
                  'is_read': false,
                  'created_at': '2026-10-18T06:07:20Z',
                },
              ],
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/announcements/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/document-requests/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/activities/')) {
          return http.Response(
            jsonEncode([]),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path.contains('/tickets/live-status/')) {
          return http.Response(
            jsonEncode({'serving': null, 'recent_completed': []}),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('Not found', 404);
      });

      final service = DashboardService(
        apiClient: ApiClient(
          client: client,
          baseUrl: 'https://kapitbayan.test',
        ),
        storageService: storage,
      );

      final data = await service.fetchDashboardData();

      expect(data.hasNotificationsError, isFalse);
      expect(data.notifications, hasLength(1));
      expect(data.notifications.single.id, 'resident-72');
      expect(data.notifications.single.type, NotificationType.queue);
      expect(data.notifications.single.category, 'Queue Alert');
      expect(
        data.notifications.single.description,
        'Please proceed to the service counter.',
      );
      expect(data.notifications.single.actionRoute, 'queue');
    },
  );
}
