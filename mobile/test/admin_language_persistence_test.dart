import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/localization/app_language.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/main.dart';
import 'package:mobile/models/auth_response.dart';
import 'package:mobile/models/user_model.dart';
import 'package:mobile/screens/login_screen.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:mobile/widgets/kapitbayan_logo.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _SuccessfulAdminAuthService extends AuthService {
  _SuccessfulAdminAuthService(StorageService storageService)
    : super(apiClient: ApiClient(), storageService: storageService);

  @override
  Future<AuthResponse> login({
    required String username,
    required String password,
  }) async {
    const admin = UserModel(
      id: 1,
      username: 'admin@example.test',
      email: 'admin@example.test',
      role: 'ADMIN',
      fullName: 'Barangay Admin',
    );
    await storageService.saveTokens(accessToken: 'test-access-token');
    await storageService.saveUser(admin);
    return const AuthResponse(accessToken: 'test-access-token', user: admin);
  }

  @override
  Future<void> logout() async {}
}

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('Filipino remains selected after an official signs in', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final storage = await StorageService.init();
    final language = await AppLanguageController.load();
    await tester.pumpWidget(
      KapitBayanApp(
        home: LoginScreen(authService: _SuccessfulAdminAuthService(storage)),
        languageController: language,
      ),
    );
    await tester.pumpAndSettle();

    await tester.longPress(find.byType(KapitBayanLogo));
    await tester.pumpAndSettle();
    expect(find.text('Official Sign In'), findsOneWidget);

    final languageDropdown = find.byType(DropdownButton<String>);
    expect(languageDropdown, findsOneWidget);
    await tester.tap(languageDropdown);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Filipino (Tagalog)').last);
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byType(TextFormField).at(0),
      'admin@example.test',
    );
    await tester.enterText(find.byType(TextFormField).at(1), 'test-password');
    await tester.tap(find.text('Mag-sign in bilang Kawani'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(language.languageCode, 'fil');
    expect(find.text('Konsol ng Barangay'), findsOneWidget);
    expect(find.text('FIL'), findsOneWidget);

    final preferences = await SharedPreferences.getInstance();
    expect(preferences.getString('gridy_resident_language'), 'fil');
  });
}
