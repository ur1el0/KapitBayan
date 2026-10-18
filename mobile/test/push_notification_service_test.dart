import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/services/push_notification_service.dart';

class DeviceRegistrationApiClient extends ApiClient {
  DeviceRegistrationApiClient({this.statusCode = 201, this.error})
    : super(baseUrl: 'https://example.test/api/v1');

  final int statusCode;
  final Object? error;
  String? lastEndpoint;
  Map<String, dynamic>? lastBody;
  bool? lastRequiresAuth;

  @override
  Future<http.Response> post(
    String endpoint, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
    bool requiresAuth = false,
  }) async {
    lastEndpoint = endpoint;
    lastBody = body;
    lastRequiresAuth = requiresAuth;
    if (error case final exception?) throw exception;
    return http.Response('{}', statusCode);
  }
}

void main() {
  test(
    'registers the device token with the authenticated device endpoint',
    () async {
      final apiClient = DeviceRegistrationApiClient();
      final service = PushNotificationService(apiClient: apiClient);

      final registered = await service.registerDeviceToken('fresh-fcm-token');

      expect(registered, isTrue);
      expect(apiClient.lastEndpoint, '/devices/');
      expect(apiClient.lastBody, {'token': 'fresh-fcm-token'});
      expect(apiClient.lastRequiresAuth, isTrue);
    },
  );

  test(
    'does not report registration success when the API rejects the token',
    () async {
      for (final statusCode in [401, 500]) {
        final service = PushNotificationService(
          apiClient: DeviceRegistrationApiClient(statusCode: statusCode),
        );

        expect(await service.registerDeviceToken('fresh-fcm-token'), isFalse);
      }
    },
  );

  test(
    'does not report registration success when the API request throws',
    () async {
      final service = PushNotificationService(
        apiClient: DeviceRegistrationApiClient(
          error: Exception('network error'),
        ),
      );

      expect(await service.registerDeviceToken('fresh-fcm-token'), isFalse);
    },
  );
}
