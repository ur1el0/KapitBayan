import 'package:flutter_test/flutter_test.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:mobile/services/hotline_caller.dart';

void main() {
  group('HotlineCaller', () {
    test('launches a formatted number directly in the phone app', () async {
      Uri? launchedUri;
      LaunchMode? launchedMode;
      final caller = HotlineCaller(
        directCaller: (_) async => false, // fallback to url_launcher in unit test
        launch: (uri, {required mode}) async {
          launchedUri = uri;
          launchedMode = mode;
          return true;
        },
      );

      final launched = await caller.call('(042) 710-2345');

      expect(launched, isTrue);
      expect(launchedUri, Uri(scheme: 'tel', path: '0427102345'));
      expect(launchedMode, LaunchMode.externalApplication);
    });

    test('invokes direct caller when supported', () async {
      String? dialedNumber;
      final caller = HotlineCaller(
        directCaller: (number) async {
          dialedNumber = number;
          return true;
        },
        launch: (_, {required mode}) async => false,
      );

      final launched = await caller.call('911');

      expect(launched, isTrue);
      expect(dialedNumber, '911');
    });

    test(
      'does not launch when the number contains no dialable characters',
      () async {
        var launchAttempted = false;
        final caller = HotlineCaller(
          launch: (_, {required mode}) async {
            launchAttempted = true;
            return true;
          },
        );

        final launched = await caller.call('   - / ');

        expect(launched, isFalse);
        expect(launchAttempted, isFalse);
      },
    );
  });
}
