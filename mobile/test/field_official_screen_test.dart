import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/models/document_request_model.dart';
import 'package:mobile/screens/field_official_screen.dart';
import 'package:mobile/services/field_official_service.dart';
import 'package:mobile/services/issue_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MockFieldOfficialService extends FieldOfficialService {
  MockFieldOfficialService({
    required StorageService storage,
    List<IssueReport>? reports,
  }) : reports =
           reports ??
           [
             IssueReport(
               id: 101,
               title: 'Clogged Drainage on Purok 4',
               description:
                   'Heavy rain causes overflow into residential walkways.',
               location: 'Near Purok 4 Chapel',
               status: 'PENDING',
               category: 'ENVIRONMENT',
               urgency: 'HAZARD',
               createdAt: '2026-09-02T10:00:00Z',
             ),
           ],
       super(
         apiClient: ApiClient(),
         storageService: storage,
       );

  final List<IssueReport> reports;
  int? urgencyUpdatedReportId;
  String? updatedUrgency;
  String? lastVerifiedIdentifier;

  @override
  Future<Map<String, dynamic>> fetchLiveQueueStatus() async {
    return {
      'current_ticket': 'T003',
      'total_waiting': 5,
    };
  }

  @override
  Future<Map<String, dynamic>> callNextTicket() async {
    return {
      'current_ticket': 'T004',
      'remaining_waiting': 4,
    };
  }

  @override
  Future<DocumentRequestModel?> verifyClearance(String identifier) async {
    lastVerifiedIdentifier = identifier;
    return DocumentRequestModel(
      id: 15,
      documentType: 'Barangay Clearance',
      status: 'READY_FOR_PICKUP',
      purpose: 'Local Employment Verification',
      createdAt: DateTime(2026, 9, 1),
    );
  }

  @override
  Future<List<IssueReport>> fetchBarangayIssues() async {
    return reports;
  }

  @override
  Future<void> updateIssueUrgency({
    required int reportId,
    required String urgency,
  }) async {
    urgencyUpdatedReportId = reportId;
    updatedUrgency = urgency;
  }
}

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({
      'access_token': 'dummy_official_jwt_token',
      'user_data':
          '{"id": 2, "username": "official_tanod", "email": "tanod@barangay.gov", "full_name": "Chief Tanod Juan", "role": "FIELD_OFFICIAL"}',
    });
  });

  Widget createFieldOfficialScreenTestWidget(FieldOfficialService service) {
    return MaterialApp(
      theme: AppTheme.lightTheme,
      home: FieldOfficialScreen(
        fieldOfficialService: service,
      ),
    );
  }

  testWidgets('FieldOfficialScreen renders all 3 field tabs and interacts with queue & clearance validator',
      (WidgetTester tester) async {
    final storage = await StorageService.init();
    final mockService = MockFieldOfficialService(storage: storage);

    await tester.pumpWidget(createFieldOfficialScreenTestWidget(mockService));
    await tester.pumpAndSettle();

    // 1. Verify Top Bar & Role Badge
    expect(find.text('Field Operations'), findsOneWidget);
    expect(find.text('Resident View'), findsNothing);
    expect(find.byTooltip('Log out'), findsOneWidget);
    expect(find.text('Queue Ticker'), findsOneWidget);
    expect(find.text('Verify Clearance'), findsOneWidget);
    expect(find.text('Field Reports'), findsOneWidget);

    // 2. Verify Tab 1 (Queue Ticker) initial state
    expect(find.text('CURRENTLY SERVING'), findsOneWidget);
    expect(find.text('T003'), findsOneWidget);
    expect(find.text('Waiting in queue: 5'), findsOneWidget);
    expect(find.text('Call Next Ticket'), findsOneWidget);

    // Test calling the next ticket
    await tester.tap(find.text('Call Next Ticket'));
    await tester.pumpAndSettle();
    expect(find.text('T004'), findsOneWidget);
    expect(find.text('Waiting in queue: 4'), findsOneWidget);

    // 3. Switch to Tab 2 (Verify Clearance)
    await tester.tap(find.text('Verify Clearance'));
    await tester.pumpAndSettle();

    expect(find.text('Clearance & Receipt Validator'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);

    // Enter tracking ID and tap Verify
    await tester.enterText(find.byType(TextField), 'REQ-15');
    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();

    // Verify Clearance Card Details
    expect(find.text('VALID IN SYSTEM'), findsOneWidget);
    expect(find.text('Barangay Clearance'), findsOneWidget);
    expect(find.text('Purpose: Local Employment Verification'), findsOneWidget);
    expect(mockService.lastVerifiedIdentifier, 'REQ-15');

    await tester.enterText(find.byType(TextField), 'OR-2026-0099');
    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();
    expect(mockService.lastVerifiedIdentifier, 'OR-2026-0099');
    expect(find.text('VALID IN SYSTEM'), findsOneWidget);

    // 4. Switch to Tab 3 (Field Reports)
    await tester.tap(find.text('Field Reports'));
    await tester.pumpAndSettle();

    expect(find.text('Clogged Drainage on Purok 4'), findsOneWidget);
    expect(find.text('ENVIRONMENT'), findsOneWidget);
    expect(find.text('In-Progress'), findsOneWidget);
    expect(find.text('Resolve'), findsOneWidget);
  });

  testWidgets(
    'Field reports show urgency and put emergencies first',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 1600);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final storage = await StorageService.init();
      final mockService = MockFieldOfficialService(
        storage: storage,
        reports: [
          IssueReport(
            id: 201,
            title: 'Minor noise complaint',
            description: 'A resident reported loud noise.',
            location: 'Purok 1',
            status: 'PENDING',
            urgency: 'MINOR',
            createdAt: '2026-10-07T08:00:00Z',
          ),
          IssueReport(
            id: 202,
            title: 'Emergency electrical wire',
            description: 'A live wire is hanging near homes.',
            location: 'Purok 3',
            status: 'PENDING',
            urgency: 'EMERGENCY',
            createdAt: '2026-10-07T09:00:00Z',
          ),
          IssueReport(
            id: 203,
            title: 'Hazardous flooded road',
            description: 'Flood water is blocking the road.',
            location: 'Purok 4',
            status: 'PENDING',
            urgency: 'HAZARD',
            createdAt: '2026-10-07T07:00:00Z',
          ),
          IssueReport(
            id: 204,
            title: 'Older minor obstruction',
            description: 'A minor obstruction was reported earlier.',
            location: 'Purok 2',
            status: 'PENDING',
            urgency: 'MINOR',
            createdAt: '2026-10-07T06:00:00Z',
          ),
        ],
      );

      await tester.pumpWidget(createFieldOfficialScreenTestWidget(mockService));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Field Reports'));
      await tester.pumpAndSettle();

      final emergencyTop =
          tester.getTopLeft(find.text('Emergency electrical wire')).dy;
      final hazardTop =
          tester.getTopLeft(find.text('Hazardous flooded road')).dy;
      final olderMinorTop =
          tester.getTopLeft(find.text('Older minor obstruction')).dy;
      final minorTop =
          tester.getTopLeft(find.text('Minor noise complaint')).dy;

      expect(emergencyTop, lessThan(hazardTop));
      expect(hazardTop, lessThan(minorTop));
      expect(olderMinorTop, lessThan(minorTop));
      expect(find.text('EMERGENCY'), findsOneWidget);
      expect(find.text('HAZARD'), findsOneWidget);
      expect(find.text('MINOR'), findsNWidgets(2));
    },
  );

  testWidgets(
    'Field staff can change an incident urgency',
    (WidgetTester tester) async {
      final storage = await StorageService.init();
      final mockService = MockFieldOfficialService(storage: storage);

      await tester.pumpWidget(createFieldOfficialScreenTestWidget(mockService));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Field Reports'));
      await tester.pumpAndSettle();

      final urgencyControl = find.byTooltip('Change urgency');
      expect(urgencyControl, findsOneWidget);
      await tester.tap(urgencyControl);
      await tester.pumpAndSettle();

      expect(find.text('Emergency'), findsOneWidget);
      expect(find.text('Hazard'), findsOneWidget);
      expect(find.text('Moderate'), findsOneWidget);
      expect(find.text('Minor'), findsOneWidget);

      await tester.tap(find.text('Emergency'));
      await tester.pumpAndSettle();

      expect(mockService.urgencyUpdatedReportId, 101);
      expect(mockService.updatedUrgency, 'EMERGENCY');
      expect(
        find.text('Report #101 urgency updated to EMERGENCY.'),
        findsOneWidget,
      );
    },
  );
}
