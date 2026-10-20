import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/screens/register_screen.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  Widget createRegisterTestWidget() {
    return MaterialApp(
      theme: AppTheme.lightTheme,
      home: const RegisterScreen(),
    );
  }

  testWidgets('RegisterScreen renders all key elements from reference UI correctly', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(createRegisterTestWidget());
    await tester.pumpAndSettle();

    // Verify brand & title headers
    expect(find.text('KapitBayan'), findsOneWidget);
    expect(find.text('Create an Account'), findsOneWidget);
    expect(find.text('Please provide your details to join our\ncommunity.'), findsOneWidget);

    // Verify input field labels
    expect(find.text('FULL NAME'), findsOneWidget);
    expect(find.text('BARANGAY ID / USERNAME'), findsOneWidget);
    expect(find.text('EMAIL ADDRESS'), findsOneWidget);

    // Scroll down to reveal demographic and password fields
    await tester.drag(find.byType(SingleChildScrollView), const Offset(0, -400));
    await tester.pumpAndSettle();

    // Verify new demographic fields
    expect(find.text('CONTACT NUMBER (OPTIONAL)'), findsOneWidget);
    expect(find.text('BIRTH DATE'), findsOneWidget);
    expect(find.text('Registered Voter in this Barangay'), findsOneWidget);

    expect(find.text('PASSWORD'), findsOneWidget);
    expect(find.text('CONFIRM PASSWORD'), findsOneWidget);

    // Verify verification dossier header
    expect(find.text('IDENTITY & RESIDENCY VERIFICATION', skipOffstage: false), findsOneWidget);
    expect(find.text('Required: upload at least one ID or proof of residency', skipOffstage: false), findsOneWidget);

    // Expand the verification accordion to reveal inner dossier fields
    await tester.ensureVisible(find.text('IDENTITY & RESIDENCY VERIFICATION'));
    await tester.tap(find.text('IDENTITY & RESIDENCY VERIFICATION'));
    await tester.pumpAndSettle();

    expect(find.text('PHILSYS NATIONAL ID NUMBER', skipOffstage: false), findsOneWidget);
    expect(find.text('Upload PhilSys ID Photo', skipOffstage: false), findsOneWidget);
    expect(find.text('BILLING STATEMENT TYPE', skipOffstage: false), findsOneWidget);
    expect(find.text('Upload Billing Receipt Photo', skipOffstage: false), findsOneWidget);
    expect(find.text('SECONDARY VALID ID (OPTIONAL)', skipOffstage: false), findsOneWidget);
    expect(find.text('I consent to provide my personal data as a resident for barangay verification, in accordance with the RA 10173 Data Privacy Act.', skipOffstage: false), findsOneWidget);

    // Verify hint placeholders are in the widget tree (even if scrolled off-screen)
    expect(find.text('Johnathan Doe', skipOffstage: false), findsOneWidget);
    expect(find.text('CID-99201', skipOffstage: false), findsOneWidget);
    expect(find.text('name@civic.gov', skipOffstage: false), findsOneWidget);

    // Verify primary action button
    expect(find.text('Register Account', skipOffstage: false), findsOneWidget);

    // Verify alternative login text
    expect(
      find.byWidgetPredicate(
        (widget) => widget is Text && widget.textSpan?.toPlainText().contains('Already have an account? Login here') == true,
      ),
      findsOneWidget,
    );

    // Verify footer disclaimer
    expect(find.text('BY REGISTERING, YOU AGREE TO OUR\nTERMS OF SERVICE & PRIVACY POLICY.', skipOffstage: false), findsOneWidget);
  });

  testWidgets('Submitting empty form triggers validation error messages for all fields', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(createRegisterTestWidget());
    await tester.pumpAndSettle();

    // Tap the register button without entering data
    final registerButton = find.text('Register Account');
    expect(registerButton, findsOneWidget);
    await tester.ensureVisible(registerButton);
    await tester.tap(registerButton);
    await tester.pumpAndSettle();

    // Expect field validation error messages
    expect(find.text('Please enter your full name', skipOffstage: false), findsOneWidget);
    expect(find.text('Please select your barangay', skipOffstage: false), findsOneWidget);
    expect(find.text('Please enter your barangay ID or username', skipOffstage: false), findsOneWidget);
    expect(find.text('Please enter your email address', skipOffstage: false), findsOneWidget);
    expect(find.text('Please enter a password', skipOffstage: false), findsOneWidget);
    expect(find.text('Please confirm your password', skipOffstage: false), findsOneWidget);
  });

  testWidgets('requires an ID or residency proof before sending registration', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    final apiClient = RegistrationGuardApiClient();
    final authService = AuthService(
      apiClient: apiClient,
      storageService: StorageService(preferences),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: RegisterScreen(authService: authService),
      ),
    );
    await tester.pumpAndSettle();

    final textFields = find.byType(TextFormField);
    await tester.enterText(textFields.at(0), 'Test Resident');
    await tester.enterText(textFields.at(1), 'Purok 1');
    await tester.enterText(textFields.at(3), 'test_resident');
    await tester.enterText(textFields.at(4), 'test@example.com');
    await tester.enterText(textFields.at(5), 'Password123!');
    await tester.enterText(textFields.at(6), 'Password123!');

    final barangayDropdown = find.text('Select your Barangay');
    await tester.ensureVisible(barangayDropdown);
    await tester.tap(barangayDropdown);
    await tester.pumpAndSettle();
    final searchField = find.widgetWithText(
      TextField,
      'Search barangay, municipality, or province',
    );
    await tester.enterText(searchField, 'missing barangay');
    await tester.pumpAndSettle();
    expect(find.text('No barangays found.'), findsOneWidget);
    expect(find.text('Test Barangay (Lucena City, Quezon)'), findsNothing);
    await tester.enterText(searchField, '  LUCENA  ');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Test Barangay (Lucena City, Quezon)').last);
    await tester.pumpAndSettle();

    final verificationHeader = find.text('IDENTITY & RESIDENCY VERIFICATION');
    await tester.ensureVisible(verificationHeader);
    await tester.tap(verificationHeader);
    await tester.pumpAndSettle();
    final privacyConsent = find.byType(CheckboxListTile);
    await tester.ensureVisible(privacyConsent);
    await tester.tap(privacyConsent);
    await tester.pumpAndSettle();

    final registerButton = find.text('Register Account');
    await tester.ensureVisible(registerButton);
    await tester.tap(registerButton);
    await tester.pumpAndSettle();

    expect(
      find.text('Upload at least one ID or proof of residency photo to register.'),
      findsOneWidget,
    );
    expect(apiClient.registrationRequestCount, 0);
  });

  testWidgets('Validates email formatting correctly', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(createRegisterTestWidget());
    await tester.pumpAndSettle();

    // Enter full name, purok, username, invalid email, and valid passwords
    final textFields = find.byType(TextFormField);
    await tester.enterText(textFields.at(0), 'Johnathan Doe');
    await tester.enterText(textFields.at(1), 'Purok 1');
    await tester.enterText(textFields.at(3), 'CID-99201');
    await tester.enterText(textFields.at(4), 'invalid-email');
    await tester.enterText(textFields.at(5), 'password123');
    await tester.enterText(textFields.at(6), 'password123');

    final registerButton = find.text('Register Account');
    await tester.ensureVisible(registerButton);
    await tester.tap(registerButton);
    await tester.pumpAndSettle();

    expect(find.text('Please enter a valid email address', skipOffstage: false), findsOneWidget);
  });

  testWidgets('Validates password length and password match confirmation', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(createRegisterTestWidget());
    await tester.pumpAndSettle();

    final textFields = find.byType(TextFormField);
    await tester.enterText(textFields.at(0), 'Johnathan Doe');
    await tester.enterText(textFields.at(1), 'Purok 1');
    await tester.enterText(textFields.at(3), 'CID-99201');
    await tester.enterText(textFields.at(4), 'john@civic.gov');

    // Test short password
    await tester.enterText(textFields.at(5), 'short');
    await tester.enterText(textFields.at(6), 'short');
    final registerButton = find.text('Register Account');
    await tester.ensureVisible(registerButton);
    await tester.tap(registerButton);
    await tester.pumpAndSettle();

    expect(find.text('Password must be at least 8 characters', skipOffstage: false), findsOneWidget);

    // Test password mismatch
    await tester.ensureVisible(textFields.at(5));
    await tester.enterText(textFields.at(5), 'validpassword123');
    await tester.ensureVisible(textFields.at(6));
    await tester.enterText(textFields.at(6), 'differentpassword456');
    await tester.ensureVisible(registerButton);
    await tester.tap(registerButton);
    await tester.pumpAndSettle();

    expect(find.text('Passwords do not match', skipOffstage: false), findsOneWidget);
  });

  testWidgets('Toggling password visibility switches icon', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(createRegisterTestWidget());
    await tester.pumpAndSettle();

    // Initially visibility icon is visibility_outlined
    expect(find.byIcon(Icons.visibility_outlined, skipOffstage: false), findsNWidgets(2));

    // Tap first visibility toggle
    final firstToggle = find.byIcon(Icons.visibility_outlined).first;
    await tester.ensureVisible(firstToggle);
    await tester.tap(firstToggle);
    await tester.pumpAndSettle();

    // Now one is off and one is on
    expect(find.byIcon(Icons.visibility_off_outlined, skipOffstage: false), findsOneWidget);
    expect(find.byIcon(Icons.visibility_outlined, skipOffstage: false), findsOneWidget);
  });

  testWidgets('handles empty approved barangays list gracefully without crashing and disables dropdown', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    final apiClient = EmptyBarangaysApiClient();
    final authService = AuthService(
      apiClient: apiClient,
      storageService: StorageService(preferences),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: RegisterScreen(authService: authService),
      ),
    );
    await tester.pumpAndSettle();

    // Verify empty state messages are rendered
    expect(find.text('No registered barangays are currently available.'), findsAtLeastNWidgets(1));

    // Tap the disabled dropdown - should not open bottom sheet
    await tester.tap(find.text('No registered barangays are currently available.').first);
    await tester.pumpAndSettle();
    expect(find.text('Search barangay, municipality, or province'), findsNothing);
  });
}

class EmptyBarangaysApiClient extends ApiClient {
  EmptyBarangaysApiClient() : super(baseUrl: 'https://kapitbayan.test');

  @override
  Future<http.Response> get(
    String endpoint, {
    Map<String, String>? queryParams,
    Map<String, String>? headers,
    bool requiresAuth = true,
  }) async {
    return http.Response('[]', 200, headers: {'content-type': 'application/json'});
  }
}


class RegistrationGuardApiClient extends ApiClient {
  int registrationRequestCount = 0;

  RegistrationGuardApiClient() : super(baseUrl: 'https://kapitbayan.test');

  @override
  Future<http.Response> get(
    String endpoint, {
    Map<String, String>? queryParams,
    Map<String, String>? headers,
    bool requiresAuth = true,
  }) async {
    return http.Response(
      '[{"id":1,"name":"Test Barangay","municipality":"Lucena City","province":"Quezon"}]',
      200,
      headers: {'content-type': 'application/json'},
    );
  }

  @override
  Future<http.Response> postMultipart(
    String endpoint, {
    Map<String, String>? fields,
    List<http.MultipartFile>? files,
    bool requiresAuth = true,
  }) async {
    registrationRequestCount++;
    return http.Response('{}', 201, headers: {'content-type': 'application/json'});
  }
}
