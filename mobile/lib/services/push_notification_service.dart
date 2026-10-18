import 'dart:async';
import 'dart:convert';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../core/navigation/app_navigation_keys.dart';
import '../core/network/api_client.dart';

class PushNotificationService {
  static PushNotificationService? _sharedInstance;

  static PushNotificationService shared({required ApiClient apiClient}) {
    return _sharedInstance ??= PushNotificationService(apiClient: apiClient);
  }

  static Future<void> disposeShared() async {
    final service = _sharedInstance;
    _sharedInstance = null;
    await service?.dispose();
  }

  static const String _webVapidKey =
      'BP9uZMIa96hTyaoGPJisSEjRjRM69TOWDQD6TYQCKxE8weHrwVA7Oa85-h6rYu-BPS-A_q287LJ6_CTYqDQcEmY';

  final ApiClient apiClient;
  FirebaseMessaging get _messaging => FirebaseMessaging.instance;

  StreamSubscription<String>? _tokenRefreshSubscription;
  StreamSubscription<RemoteMessage>? _foregroundSubscription;
  StreamSubscription<RemoteMessage>? _openedSubscription;
  bool _initialized = false;
  bool _pushEnabled = false;
  ValueChanged<RemoteMessage>? _onNotificationOpened;

  PushNotificationService({required this.apiClient});

  Future<void> initialize({
    required ValueChanged<RemoteMessage> onNotificationOpened,
  }) async {
    if (_initialized) return;
    _onNotificationOpened = onNotificationOpened;

    try {
      _foregroundSubscription = FirebaseMessaging.onMessage.listen(
        _showForegroundMessage,
      );
      _openedSubscription = FirebaseMessaging.onMessageOpenedApp.listen((
        message,
      ) {
        _onNotificationOpened?.call(message);
      });
      _tokenRefreshSubscription = _messaging.onTokenRefresh.listen((token) {
        if (_pushEnabled) {
          unawaited(registerDeviceToken(token));
        }
      });
      _initialized = true;
    } catch (error) {
      await _cancelSubscriptions();
      _onNotificationOpened = null;
      debugPrint(
        'Push notification listeners unavailable: ${error.runtimeType}',
      );
      return;
    }

    try {
      // Process launch taps even when the profile endpoint is temporarily down.
      final initialMessage = await _messaging.getInitialMessage();
      if (initialMessage != null) {
        _onNotificationOpened?.call(initialMessage);
      }
    } catch (error) {
      debugPrint('Push launch message unavailable: ${error.runtimeType}');
    }

    try {
      final response = await apiClient.get('/auth/me/', requiresAuth: true);
      if (response.statusCode != 200) return;
      final profile =
          jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      if (profile['push_alerts'] == true) {
        _pushEnabled = await requestPermissionAndRegisterDevice();
      }
    } catch (error) {
      debugPrint('Push notification setup failed: ${error.runtimeType}');
    }
  }

  /// Requests OS permission and registers this device after the user opts in.
  Future<bool> requestPermissionAndRegisterDevice() async {
    try {
      final settings = await _messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      final isAllowed =
          settings.authorizationStatus == AuthorizationStatus.authorized ||
          settings.authorizationStatus == AuthorizationStatus.provisional;
      if (!isAllowed) return false;

      final token = await _messaging.getToken(
        vapidKey: kIsWeb ? _webVapidKey : null,
      );
      if (token == null || token.isEmpty) return false;
      return await registerDeviceToken(token);
    } catch (error) {
      debugPrint('Push device registration failed: ${error.runtimeType}');
      return false;
    }
  }

  void setPushEnabled(bool enabled) {
    _pushEnabled = enabled;
  }

  Future<bool> registerDeviceToken(String token) async {
    try {
      final response = await apiClient.post(
        '/devices/',
        body: {'token': token},
        requiresAuth: true,
      );
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return true;
      }
      debugPrint(
        'Push device registration rejected by API '
        '(${response.statusCode}).',
      );
    } catch (error) {
      debugPrint('Push device registration failed: ${error.runtimeType}');
    }
    return false;
  }

  void _showForegroundMessage(RemoteMessage message) {
    if (!_pushEnabled) return;

    final title = message.notification?.title?.trim();
    final body = message.notification?.body?.trim();
    final content = [
      if (title != null && title.isNotEmpty) title,
      if (body != null && body.isNotEmpty) body,
    ].join('\n');
    if (content.isEmpty) return;

    appScaffoldMessengerKey.currentState
      ?..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(content),
          duration: const Duration(seconds: 6),
          behavior: SnackBarBehavior.floating,
          action: _onNotificationOpened == null
              ? null
              : SnackBarAction(
                  label: 'OPEN',
                  onPressed: () => _onNotificationOpened?.call(message),
                ),
        ),
      );
  }

  Future<void> dispose() async {
    _pushEnabled = false;
    await _cancelSubscriptions();
    _onNotificationOpened = null;
    _initialized = false;
  }

  Future<void> _cancelSubscriptions() async {
    await _tokenRefreshSubscription?.cancel();
    await _foregroundSubscription?.cancel();
    await _openedSubscription?.cancel();
    _tokenRefreshSubscription = null;
    _foregroundSubscription = null;
    _openedSubscription = null;
  }
}
