import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

typedef ExternalUriLauncher =
    Future<bool> Function(Uri uri, {required LaunchMode mode});

typedef DirectCallHandler = Future<bool> Function(String phoneNumber);

class HotlineCaller {
  HotlineCaller({
    ExternalUriLauncher? launch,
    DirectCallHandler? directCaller,
  })  : _launch = launch ?? _launchExternalUri,
        _directCaller = directCaller ?? _callViaPlatformChannel;

  static const MethodChannel _channel =
      MethodChannel('com.kapitbayan.mobile/direct_caller');

  final ExternalUriLauncher _launch;
  final DirectCallHandler _directCaller;

  Future<bool> call(String phoneNumber) async {
    final dialableNumber = phoneNumber.replaceAll(RegExp(r'[^\d+]'), '');
    if (dialableNumber.isEmpty) return false;

    // On Android, attempt direct placement via Intent.ACTION_CALL channel
    try {
      final success = await _directCaller(dialableNumber);
      if (success) return true;
    } catch (_) {
      // Fallback gracefully to url_launcher if channel or permission encounters issue
    }

    return _launch(
      Uri(scheme: 'tel', path: dialableNumber),
      mode: LaunchMode.externalApplication,
    );
  }

  static Future<bool> _callViaPlatformChannel(String phoneNumber) async {
    try {
      final result = await _channel.invokeMethod<bool>('callPhone', {
        'phoneNumber': phoneNumber,
      });
      return result ?? false;
    } catch (_) {
      return false;
    }
  }

  static Future<bool> _launchExternalUri(Uri uri, {required LaunchMode mode}) =>
      launchUrl(uri, mode: mode);
}

