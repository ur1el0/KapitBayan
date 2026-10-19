import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/screens/forgot_password_screen.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('uses the emailed reset link without manual token entry', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2200);
    tester.view.devicePixelRatio = 2;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final preferences = await SharedPreferences.getInstance();
    final authService = RecordingAuthService(preferences);
    await tester.pumpWidget(
      MaterialApp(home: ForgotPasswordScreen(authService: authService)),
    );

    await tester.enterText(
      find.byType(TextFormField).first,
      'resident@example.com',
    );
    await tester.tap(find.text('Send Reset Link'));
    await tester.pumpAndSettle();

    expect(authService.requestedEmail, 'resident@example.com');
    expect(find.text('USER ID (UIDB64)'), findsNothing);
    expect(find.text('RESET TOKEN'), findsNothing);
    expect(find.text('RESET LINK FROM EMAIL'), findsOneWidget);

    await tester.enterText(
      find.byType(TextFormField).at(0),
      'https://kapitbayan-ph.vercel.app/reset-password'
      '?uidb64=MzY&token=abc-123_def',
    );
    await tester.enterText(find.byType(TextFormField).at(1), 'StrongPass123!');
    await tester.enterText(find.byType(TextFormField).at(2), 'StrongPass123!');
    await tester.tap(find.text('Reset Password'));
    await tester.pumpAndSettle();

    expect(authService.confirmedUid, 'MzY');
    expect(authService.confirmedToken, 'abc-123_def');
    expect(authService.confirmedPassword, 'StrongPass123!');
  });
}

class RecordingAuthService extends AuthService {
  RecordingAuthService(SharedPreferences preferences)
    : super(
        apiClient: ApiClient(baseUrl: 'https://kapitbayan.test/api/v1'),
        storageService: StorageService(preferences),
      );

  String? requestedEmail;
  String? confirmedUid;
  String? confirmedToken;
  String? confirmedPassword;

  @override
  Future<void> requestPasswordReset(String email) async {
    requestedEmail = email;
  }

  @override
  Future<void> confirmPasswordReset({
    required String newPassword,
    required String uidb64,
    required String token,
  }) async {
    confirmedPassword = newPassword;
    confirmedUid = uidb64;
    confirmedToken = token;
  }
}
