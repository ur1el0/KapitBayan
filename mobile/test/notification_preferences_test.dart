import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/models/user_model.dart';
import 'package:mobile/screens/profile_screen.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/push_notification_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class PreferenceApiClient extends ApiClient {
  PreferenceApiClient() : super(baseUrl: 'https://example.test/api/v1');

  Map<String, dynamic> profile = {'email_alerts': true, 'push_alerts': false};
  Map<String, dynamic>? lastPatch;

  @override
  Future<http.Response> get(
    String endpoint, {
    Map<String, String>? queryParams,
    Map<String, String>? headers,
    bool requiresAuth = true,
  }) async {
    return http.Response(jsonEncode(profile), 200);
  }

  @override
  Future<http.Response> patch(
    String endpoint, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
    bool requiresAuth = true,
  }) async {
    lastPatch = body;
    profile = {...profile, ...?body};
    return http.Response(jsonEncode(profile), 200);
  }
}

class FakePushNotificationService extends PushNotificationService {
  FakePushNotificationService({required super.apiClient});

  bool? lastEnabledState;

  @override
  Future<bool> requestPermissionAndRegisterDevice() async => true;

  @override
  void setPushEnabled(bool enabled) {
    lastEnabledState = enabled;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('resident notification settings load and persist independently', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final preferences = await SharedPreferences.getInstance();
    final apiClient = PreferenceApiClient();
    final authService = AuthService(
      apiClient: apiClient,
      storageService: StorageService(preferences),
    );
    final pushService = FakePushNotificationService(apiClient: apiClient);
    final user = UserModel(
      id: 1,
      username: 'resident',
      email: 'resident@example.test',
      role: 'RESIDENT',
      fullName: 'Resident Test',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: ProfileScreen(
          user: user,
          authService: authService,
          pushNotificationService: pushService,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Notification Preferences'), findsOneWidget);
    expect(
      tester
          .widget<SwitchListTile>(
            find.widgetWithText(SwitchListTile, 'Email updates'),
          )
          .value,
      isTrue,
    );
    expect(
      tester
          .widget<SwitchListTile>(
            find.widgetWithText(SwitchListTile, 'Push notifications'),
          )
          .value,
      isFalse,
    );

    final emailSwitch = find.descendant(
      of: find.widgetWithText(SwitchListTile, 'Email updates'),
      matching: find.byType(Switch),
    );
    await tester.ensureVisible(emailSwitch);
    await tester.tap(emailSwitch);
    await tester.pumpAndSettle();
    expect(apiClient.lastPatch, {'email_alerts': false});
    expect(pushService.lastEnabledState, isNull);

    final pushSwitch = find.descendant(
      of: find.widgetWithText(SwitchListTile, 'Push notifications'),
      matching: find.byType(Switch),
    );
    await tester.ensureVisible(pushSwitch);
    await tester.tap(pushSwitch);
    await tester.pumpAndSettle();
    expect(apiClient.lastPatch, {'push_alerts': true});
    expect(pushService.lastEnabledState, isTrue);
  });
}
