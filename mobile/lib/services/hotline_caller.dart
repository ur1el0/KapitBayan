import 'package:url_launcher/url_launcher.dart';

typedef ExternalUriLauncher =
    Future<bool> Function(Uri uri, {required LaunchMode mode});

class HotlineCaller {
  HotlineCaller({ExternalUriLauncher? launch})
    : _launch = launch ?? _launchExternalUri;

  final ExternalUriLauncher _launch;

  Future<bool> call(String phoneNumber) {
    final dialableNumber = phoneNumber.replaceAll(RegExp(r'[^\d+]'), '');
    if (dialableNumber.isEmpty) return Future.value(false);

    return _launch(
      Uri(scheme: 'tel', path: dialableNumber),
      mode: LaunchMode.externalApplication,
    );
  }

  static Future<bool> _launchExternalUri(Uri uri, {required LaunchMode mode}) =>
      launchUrl(uri, mode: mode);
}
