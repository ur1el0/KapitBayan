import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/models/activity_schedule_model.dart';
import 'package:mobile/models/announcement_model.dart';
import 'package:mobile/models/document_request_model.dart';
import 'package:mobile/models/notification_item_model.dart';
import 'package:mobile/models/user_model.dart';
import 'package:mobile/screens/dashboard_screen.dart';
import 'package:mobile/services/dashboard_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MockDashboardService extends DashboardService {
  MockDashboardService({required StorageService storage})
    : super(apiClient: ApiClient(), storageService: storage);

  @override
  Future<DashboardData> fetchDashboardData() async {
    return DashboardData(
      user: const UserModel(
        id: 1,
        username: 'resident_juan',
        email: 'juan@example.com',
        role: 'RESIDENT',
        fullName: 'Juan Dela Cruz',
        isVerified: true,
      ),
      announcements: const [
        AnnouncementModel(
          id: 1,
          title: 'Vaccination Drive Reminder',
          content: 'Free vaccine at health center',
        ),
      ],
      documentRequests: const [
        DocumentRequestModel(
          id: 1,
          documentType: 'Barangay Clearance',
          status: 'PENDING',
        ),
        DocumentRequestModel(
          id: 2,
          documentType: 'Certificate of Indigency',
          status: 'PROCESSING',
        ),
      ],
      activities: [
        ActivityScheduleModel(
          id: 1,
          title: 'Vaccination Drive',
          description: 'Basic immunization',
          eventDatetime: DateTime.now(),
          location: 'Barangay Center',
        ),
      ],
      notifications: [
        NotificationItemModel(
          id: '1',
          title: 'Tax Clearance Approved',
          category: 'Document Services',
          timestamp: DateTime.now().subtract(const Duration(hours: 2)),
          type: NotificationType.approved,
        ),
      ],
    );
  }
}

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'DashboardScreen renders all sections from reference UI correctly',
    (WidgetTester tester) async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);
      final mockService = MockDashboardService(storage: storage);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: DashboardScreen(dashboardService: mockService),
        ),
      );

      // Initial frame processing
      await tester.pump();
      await tester.pumpAndSettle();

      // 1. App Bar Header & Brand
      expect(find.text('KapitBayan', skipOffstage: false), findsWidgets);

      // 2. Hero Card
      expect(
        find.text('VERIFIED RESIDENT', skipOffstage: false),
        findsOneWidget,
      );
      expect(
        find.text('Welcome back, Juan', skipOffstage: false),
        findsOneWidget,
      );

      // 3. Metric Summary Cards
      expect(find.text('ANNOUNCEMENTS', skipOffstage: false), findsOneWidget);
      expect(
        find.text('MY PENDING\nREQUESTS', skipOffstage: false),
        findsOneWidget,
      );

      // 4. Recent Notifications
      expect(
        find.text('Recent Notifications', skipOffstage: false),
        findsOneWidget,
      );
      expect(find.text('View all', skipOffstage: false), findsOneWidget);
      expect(
        find.text('Tax Clearance Approved', skipOffstage: false),
        findsOneWidget,
      );

      // 5. Quick Services Action Cards
      expect(find.text('Quick Services', skipOffstage: false), findsOneWidget);
      expect(
        find.text('Request Document', skipOffstage: false),
        findsOneWidget,
      );
      expect(find.text('Report Issue', skipOffstage: false), findsOneWidget);
      expect(
        find.text('Barangay Hotline', skipOffstage: false),
        findsOneWidget,
      );
      expect(find.text('My Reports', skipOffstage: false), findsOneWidget);

      // 6. Community Schedule Timeline
      expect(
        find.text('Community Schedule', skipOffstage: false),
        findsOneWidget,
      );
      expect(
        find.text('Vaccination Drive', skipOffstage: false),
        findsOneWidget,
      );
      expect(find.text('Barangay Center', skipOffstage: false), findsOneWidget);

      // 7. Bottom Navigation Bar Tabs
      expect(find.text('DASHBOARD', skipOffstage: false), findsOneWidget);
      expect(find.text('QUEUE', skipOffstage: false), findsOneWidget);
      expect(find.text('DOCUMENTS', skipOffstage: false), findsOneWidget);
      expect(find.text('SCHEDULE', skipOffstage: false), findsOneWidget);
    },
  );

  testWidgets('opening a recent notification shows its detail sheet', (
    WidgetTester tester,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    final mockService = MockDashboardService(storage: storage);

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: DashboardScreen(dashboardService: mockService),
      ),
    );
    await tester.pump();
    await tester.pumpAndSettle();

    final notification = find.text('Tax Clearance Approved');
    await tester.ensureVisible(notification);
    await tester.tap(notification);
    await tester.pumpAndSettle();

    expect(
      find.textContaining('Advisory Category: Document Services'),
      findsOneWidget,
    );
    expect(find.text('Dismiss'), findsOneWidget);
    await tester.tap(find.text('Dismiss'));
    await tester.pumpAndSettle();
    expect(find.text('Recent Notifications'), findsOneWidget);
  });

  testWidgets(
    'empty notifications displays honest empty state without sample notifications',
    (WidgetTester tester) async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);
      final emptyService = _EmptyNotificationsDashboardService(storage: storage);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: DashboardScreen(dashboardService: emptyService),
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      expect(
        find.text('No new notifications at this time.', skipOffstage: false),
        findsOneWidget,
      );
      expect(find.text('Tax Clearance Approved'), findsNothing);
      expect(find.text('Utility Maintenance Notice'), findsNothing);
    },
  );

  testWidgets(
    'notifications fetch failure renders explicit retryable error instead of successful empty state',
    (WidgetTester tester) async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);

      int fetchCount = 0;
      final dynamicService = _DynamicDashboardService(
        storage: storage,
        onFetch: () async {
          fetchCount++;
          if (fetchCount == 1) {
            return const DashboardData(
              user: UserModel(
                id: 1,
                username: 'resident_juan',
                email: 'juan@example.com',
                role: 'RESIDENT',
                fullName: 'Juan Dela Cruz',
                isVerified: true,
              ),
              hasNotificationsError: true,
              notificationsErrorMessage: 'Failed to retrieve announcements',
            );
          }
          return DashboardData(
            user: const UserModel(
              id: 1,
              username: 'resident_juan',
              email: 'juan@example.com',
              role: 'RESIDENT',
              fullName: 'Juan Dela Cruz',
              isVerified: true,
            ),
            notifications: [
              NotificationItemModel(
                id: '1',
                title: 'Clearance Ready',
                category: 'Document Services',
                timestamp: DateTime.now(),
                type: NotificationType.approved,
              ),
            ],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: DashboardScreen(dashboardService: dynamicService),
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      // 1. Verify visible error state in Recent Notifications section
      expect(find.text('Unable to load notifications'), findsOneWidget);
      expect(find.text('Failed to retrieve announcements'), findsOneWidget);
      expect(find.text('No new notifications at this time.'), findsNothing);
      expect(find.byTooltip('Retry loading notifications'), findsOneWidget);

      // 2. Open Notification Center Sheet and verify it also displays error state
      final viewAll = find.text('View all');
      await tester.ensureVisible(viewAll);
      await tester.tap(viewAll);
      await tester.pumpAndSettle();

      expect(find.text('Notification Center'), findsOneWidget);
      expect(find.text('Error'), findsOneWidget);
      expect(find.text('No recent notifications'), findsNothing);

      // Close modal and retry
      await tester.tap(find.text('Try again'));
      await tester.pump();
      await tester.pumpAndSettle();

      // 3. Verify recovered state after retry
      expect(find.text('Unable to load notifications'), findsNothing);
      expect(find.text('Clearance Ready'), findsOneWidget);
    },
  );

  testWidgets(
    'document request fetch failure does not present a zero count or current status',
    (WidgetTester tester) async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);
      final unavailableService = _DynamicDashboardService(
        storage: storage,
        onFetch: () async => const DashboardData(
          user: UserModel(
            id: 1,
            username: 'resident_juan',
            email: 'juan@example.com',
            role: 'RESIDENT',
            fullName: 'Juan Dela Cruz',
            isVerified: true,
          ),
          hasDocumentRequestsError: true,
          hasNotificationsError: true,
          notificationsErrorMessage:
              'Unable to load document request updates (HTTP 500)',
        ),
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: DashboardScreen(dashboardService: unavailableService),
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      expect(
        find.text(
          'We could not refresh your document requests. Open Documents to try again.',
        ),
        findsOneWidget,
      );
      expect(find.text('\u2014'), findsOneWidget);
      expect(
        find.textContaining('All your records are up to date.'),
        findsNothing,
      );
      // Announcements remain available at zero; pending requests are unknown.
      expect(find.text('00'), findsOneWidget);
    },
  );
}

class _DynamicDashboardService extends DashboardService {
  final Future<DashboardData> Function() onFetch;

  _DynamicDashboardService({
    required StorageService storage,
    required this.onFetch,
  }) : super(apiClient: ApiClient(), storageService: storage);

  @override
  Future<DashboardData> fetchDashboardData() => onFetch();
}

class _EmptyNotificationsDashboardService extends DashboardService {
  _EmptyNotificationsDashboardService({required StorageService storage})
      : super(apiClient: ApiClient(), storageService: storage);

  @override
  Future<DashboardData> fetchDashboardData() async {
    return const DashboardData(
      user: UserModel(
        id: 1,
        username: 'resident_juan',
        email: 'juan@example.com',
        role: 'RESIDENT',
        fullName: 'Juan Dela Cruz',
        isVerified: true,
      ),
      announcements: [],
      documentRequests: [],
      activities: [],
      notifications: [],
    );
  }
}
