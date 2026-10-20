import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/screens/login_screen.dart';
import 'package:mobile/widgets/kapitbayan_logo.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
  });

  Future<void> pumpLogin(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      MaterialApp(theme: AppTheme.lightTheme, home: const LoginScreen()),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('official mode remains activated by long-pressing the logo', (
    tester,
  ) async {
    await pumpLogin(tester);

    await tester.longPress(find.byType(KapitBayanLogo));
    await tester.pumpAndSettle();

    expect(find.text('Official Sign In'), findsOneWidget);
    expect(find.text('BARANGAY PERSONNEL ACCESS'), findsOneWidget);
  });

  testWidgets('privacy policy sheet shows its content and support link is removed', (
    tester,
  ) async {
    await pumpLogin(tester);

    expect(find.text('SUPPORT'), findsNothing);

    await tester.ensureVisible(find.text('PRIVACY POLICY'));
    await tester.tap(find.text('PRIVACY POLICY'));
    await tester.pumpAndSettle();
    expect(find.text('Privacy Policy & Data Protection'), findsOneWidget);
    await tester.tap(find.text('Close'));
    await tester.pumpAndSettle();
  });
}
