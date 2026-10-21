import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/models/document_request_model.dart';
import 'package:mobile/models/user_model.dart';
import 'package:mobile/screens/documents_screen.dart';
import 'package:mobile/services/document_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MockDocumentService extends DocumentService {
  MockDocumentService({required StorageService storage})
      : super(
          apiClient: ApiClient(),
          storageService: storage,
        );

  Future<List<DocumentRequestModel>> Function()? fetchHandler;

  @override
  Future<List<DocumentRequestModel>> fetchDocumentRequests() async {
    if (fetchHandler != null) return fetchHandler!();

    return [
      DocumentRequestModel(
        id: 892,
        documentType: 'Barangay Clearance',
        urgencyTag: 'REGULAR',
        status: 'PROCESSING',
        createdAt: DateTime(2026, 10, 24),
      ),
      DocumentRequestModel(
        id: 441,
        documentType: 'Business Permit',
        urgencyTag: 'REGULAR',
        status: 'READY_FOR_PICKUP',
        createdAt: DateTime(2026, 10, 20),
      ),
      DocumentRequestModel(
        id: 112,
        documentType: 'Residency Certificate',
        urgencyTag: 'REGULAR',
        status: 'RELEASED',
        createdAt: DateTime(2026, 10, 12),
      ),
    ];
  }

  @override
  Future<DocumentRequestModel> createDocumentRequest({
    required String documentType,
    String urgencyTag = 'REGULAR',
    String? purpose,
  }) async {
    return DocumentRequestModel(
      id: 999,
      documentType: documentType,
      urgencyTag: urgencyTag,
      status: 'PENDING',
      createdAt: DateTime.now(),
    );
  }
}

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('DocumentsScreen renders all UI elements matching reference design accurately', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    await storage.saveUser(const UserModel(
      id: 1,
      username: 'resident_test',
      email: 'resident@example.com',
      role: 'RESIDENT',
      fullName: 'Juan Dela Cruz',
      isVerified: true,
    ));

    final mockService = MockDocumentService(storage: storage);

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: DocumentsScreen(documentService: mockService),
      ),
    );

    // Initial render & wait for async fetch
    await tester.pump();
    await tester.pumpAndSettle();

    // 1. Header & Brand Title
    expect(find.text('KapitBayan'), findsOneWidget);
    expect(find.text('CENTRAL REGISTRY'), findsOneWidget);
    expect(find.text('Documents'), findsOneWidget);

    // 2. Search Field
    expect(find.text('Search for certificates or permits...'), findsOneWidget);

    // 3. "Request New" Section & 4 Catalog Cards
    expect(find.text('Request New'), findsOneWidget);
    expect(find.text('View All'), findsOneWidget);
    expect(find.text('Barangay\nClearance'), findsOneWidget);
    expect(find.text('Standard residency proof'), findsOneWidget);
    expect(find.text('Certificate of\nIndigency'), findsOneWidget);
    expect(find.text('For social service aid'), findsOneWidget);
    expect(find.text('Certificate of\nResidency'), findsOneWidget);
    expect(find.text('Address verification'), findsOneWidget);
    expect(find.text('Barangay Business\nClearance'), findsOneWidget);
    expect(find.text('Local business clearance'), findsOneWidget);
    expect(find.text('Business Permit'), findsOneWidget); // Existing request fixture

    // 4. "My Document Requests" Section & Cards
    expect(find.text('My Document Requests'), findsOneWidget);
    expect(find.text('ID: #BC-2026-0892'), findsOneWidget);
    expect(find.text('Requested Oct 24, 2026'), findsOneWidget);
    expect(find.text('PROCESSING'), findsOneWidget);

    expect(find.text('ID: #BP-2026-0441'), findsOneWidget);
    expect(find.text('Requested Oct 20, 2026'), findsOneWidget);
    expect(find.text('READY FOR PICKUP'), findsOneWidget);

    expect(find.text('ID: #RC-2026-0112'), findsOneWidget);
    expect(find.text('Requested Oct 12, 2026'), findsOneWidget);
    expect(find.text('COMPLETED'), findsOneWidget);

    // 5. Bottom Navigation Bar Tabs
    expect(find.text('DASHBOARD'), findsOneWidget);
    expect(find.text('QUEUE'), findsOneWidget);
    expect(find.text('DOCUMENTS'), findsOneWidget);
    expect(find.text('SCHEDULE'), findsOneWidget);
  });

  testWidgets('DocumentsScreen search field filters requests and catalog live', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    await storage.saveUser(const UserModel(
      id: 1,
      username: 'resident_test',
      email: 'resident@example.com',
      role: 'RESIDENT',
      fullName: 'Juan Dela Cruz',
    ));

    final mockService = MockDocumentService(storage: storage);

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: DocumentsScreen(documentService: mockService),
      ),
    );

    await tester.pumpAndSettle();

    // Type "Clearance" in the search field
    await tester.enterText(find.byType(TextField), 'Clearance');
    await tester.pumpAndSettle();

    // Barangay Clearance should be visible
    expect(find.text('Barangay\nClearance'), findsOneWidget);
    expect(find.text('ID: #BC-2026-0892'), findsOneWidget);

    // Other requests should be filtered out
    expect(find.text('ID: #BP-2026-0441'), findsNothing);
    expect(find.text('ID: #RC-2026-0112'), findsNothing);
  });

  testWidgets('Tapping request card opens details modal', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    final mockService = MockDocumentService(storage: storage);

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: DocumentsScreen(documentService: mockService),
      ),
    );

    await tester.pumpAndSettle();

    // Tap on request card
    final targetFinder = find.text('ID: #BC-2026-0892');
    await tester.tap(targetFinder);
    await tester.pumpAndSettle();

    // Details modal should open
    expect(find.text('Current Status'), findsOneWidget);
    expect(find.text('Urgency Priority'), findsOneWidget);
    expect(find.text('Submission Date'), findsOneWidget);
    expect(find.text('Close'), findsOneWidget);
  });

  testWidgets('Tapping request catalog card opens RequestDocumentDialog modal', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    final mockService = MockDocumentService(storage: storage);

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: DocumentsScreen(documentService: mockService),
      ),
    );

    await tester.pumpAndSettle();

    // Tap on Certificate of Indigency catalog card
    await tester.tap(find.text('Certificate of\nIndigency'));
    await tester.pumpAndSettle();

    // Request Document modal should open
    expect(find.text('New Document Request'), findsOneWidget);
    expect(find.text('DOCUMENT TYPE'), findsOneWidget);
    expect(find.text('PROCESSING SPEED'), findsOneWidget);
    expect(find.text('Regular'), findsOneWidget);
    expect(find.text('Urgent'), findsOneWidget);
    expect(find.text('Submit Request'), findsOneWidget);
  });

  testWidgets('failed document load shows a retryable error instead of an empty state', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    final mockService = MockDocumentService(storage: storage);
    var fetchAttempts = 0;
    mockService.fetchHandler = () async {
      fetchAttempts++;
      if (fetchAttempts == 1) throw Exception('Network unavailable');
      return [];
    };

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: DocumentsScreen(documentService: mockService),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text("We couldn't load your document requests."), findsOneWidget);
    expect(find.text('No active document requests'), findsNothing);
    expect(find.text('Try again'), findsOneWidget);

    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();

    expect(find.text('No active document requests'), findsOneWidget);
    expect(fetchAttempts, 2);
  });

  testWidgets('failed document refresh keeps loaded requests visible', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    final mockService = MockDocumentService(storage: storage);
    var fetchAttempts = 0;
    mockService.fetchHandler = () async {
      fetchAttempts++;
      if (fetchAttempts == 2) throw Exception('Network unavailable');
      return [
        DocumentRequestModel(
          id: 892,
          documentType: 'Barangay Clearance',
          urgencyTag: 'REGULAR',
          status: 'PROCESSING',
          createdAt: DateTime(2026, 10, 24),
        ),
      ];
    };

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: DocumentsScreen(documentService: mockService),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('ID: #BC-2026-0892'), findsOneWidget);
    await tester.drag(find.byType(SingleChildScrollView), const Offset(0, 500));
    await tester.pumpAndSettle();

    expect(find.text("We couldn't refresh your document requests."), findsOneWidget);
    expect(find.text('ID: #BC-2026-0892'), findsOneWidget);
    expect(fetchAttempts, 2);

    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();

    expect(find.text("We couldn't refresh your document requests."), findsNothing);
    expect(find.text('ID: #BC-2026-0892'), findsOneWidget);
    expect(fetchAttempts, 3);
  });
}
