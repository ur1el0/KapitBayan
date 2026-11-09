import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/models/queue_ticket_model.dart';
import 'package:mobile/models/user_model.dart';
import 'package:mobile/screens/queue_screen.dart';
import 'package:mobile/services/queue_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MockQueueService extends QueueService {
  MockQueueService({required StorageService storage})
    : super(apiClient: ApiClient(), storageService: storage);

  QueueTicketModel? notificationTicket;

  @override
  Future<QueueTicketModel> fetchTicket(int ticketId) async {
    if (notificationTicket == null) {
      throw const QueueServiceException('Ticket not found');
    }
    return notificationTicket!;
  }

  @override
  Future<QueueLiveStatusModel> fetchQueueStatus() async {
    final now = DateTime.now();
    return QueueLiveStatusModel(
      currentTicket: 'A-124',
      currentService: 'Document Issuance',
      totalWaiting: 4,
      avgWaitMins: 8,
      userTicket: const QueueTicketModel(
        id: 132,
        ticketNumber: 'A-132',
        serviceType: 'Document Issuance',
        status: 'WAITING',
      ),
      recentCompleted: [
        QueueTicketModel(
          id: 123,
          ticketNumber: 'A-123',
          serviceType: 'Business Permit',
          status: 'COMPLETED',
          updatedAt: now.subtract(const Duration(minutes: 2)),
        ),
        QueueTicketModel(
          id: 98,
          ticketNumber: 'C-098',
          serviceType: 'Tax Clearance',
          status: 'COMPLETED',
          updatedAt: now.subtract(const Duration(minutes: 8)),
        ),
        QueueTicketModel(
          id: 122,
          ticketNumber: 'A-122',
          serviceType: 'ID Verification',
          status: 'COMPLETED',
          updatedAt: now.subtract(const Duration(minutes: 15)),
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
    'QueueScreen renders all queue widgets matching reference UI accurately',
    (WidgetTester tester) async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);
      await storage.saveUser(
        const UserModel(
          id: 1,
          username: 'resident_test',
          email: 'resident@example.com',
          role: 'RESIDENT',
          fullName: 'Juan Dela Cruz',
          isVerified: true,
        ),
      );

      final mockQueueService = MockQueueService(storage: storage);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: QueueScreen(queueService: mockQueueService),
        ),
      );

      // Let async initialization settle
      await tester.pump();
      await tester.pumpAndSettle();

      // 1. Header & Brand Title
      expect(find.text('KapitBayan'), findsOneWidget);
      expect(find.text('LIVE QUEUE STATUS'), findsOneWidget);
      expect(find.text("Today's Queue"), findsOneWidget);

      // 2. Currently At Counter Hero Card
      expect(find.text('CURRENTLY AT COUNTER'), findsOneWidget);
      expect(find.text('A-124'), findsOneWidget);
      expect(find.text('Document Issuance'), findsWidgets);
      expect(find.text('Barangay Office'), findsOneWidget);

      // 3. Your Active Ticket Card
      expect(find.text('YOUR TICKET'), findsOneWidget);
      expect(find.text('A-132'), findsOneWidget);

      // 4. Live Metric Cards
      expect(find.text('ESTIMATED CALL'), findsOneWidget);
      expect(find.text('LIVE CAPACITY'), findsOneWidget);
      expect(find.text('Optimal'), findsOneWidget);

      // 5. Recent Completions Section
      expect(find.text('Recent Completions'), findsOneWidget);
      expect(find.text('VIEW ALL'), findsOneWidget);
      expect(find.text('A-123'), findsOneWidget);
      expect(find.text('Business Permit'), findsOneWidget);
      expect(find.text('C-098'), findsOneWidget);
      expect(find.text('Tax Clearance'), findsOneWidget);
      expect(find.text('A-122'), findsOneWidget);
      expect(find.text('ID Verification'), findsOneWidget);

      // 6. Custom Bottom Navigation Bar Tabs
      expect(find.text('DASHBOARD'), findsOneWidget);
      expect(find.text('QUEUE'), findsOneWidget);
      expect(find.text('DOCUMENTS'), findsOneWidget);
      expect(find.text('SCHEDULE'), findsOneWidget);
    },
  );

  testWidgets('notification ticket ID opens the linked ticket details', (
    WidgetTester tester,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    final queueService = MockQueueService(storage: storage)
      ..notificationTicket = const QueueTicketModel(
        id: 123,
        ticketNumber: 'A-123',
        serviceType: 'Barangay Clearance',
        status: 'COMPLETED',
        documentRequestId: 892,
      );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: QueueScreen(queueService: queueService, initialTicketId: 123),
      ),
    );
    await tester.pump();
    await tester.pumpAndSettle();

    expect(find.text('OPENED FROM NOTIFICATION'), findsOneWidget);
    expect(find.text('A-123'), findsWidgets);
    expect(find.text('Barangay Clearance · COMPLETED'), findsOneWidget);
    expect(find.text('Document request #892'), findsOneWidget);
  });

  testWidgets('ticket request directs priority review to barangay staff', (
    WidgetTester tester,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    await storage.saveUser(
      const UserModel(
        id: 2,
        username: 'queue_resident',
        email: 'queue@example.com',
        role: 'RESIDENT',
        fullName: 'Queue Resident',
        isVerified: true,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: QueueScreen(queueService: MockQueueService(storage: storage)),
      ),
    );
    await tester.pump();
    await tester.pumpAndSettle();

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();

    expect(find.byType(CheckboxListTile), findsNothing);
    expect(
      find.textContaining('Barangay staff verify priority lane eligibility.'),
      findsOneWidget,
    );
  });

  testWidgets(
    'API failure displays visible retry state and recovers on retry',
    (WidgetTester tester) async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);
      await storage.saveUser(
        const UserModel(
          id: 3,
          username: 'retry_resident',
          email: 'retry@example.com',
          role: 'RESIDENT',
          fullName: 'Retry Resident',
          isVerified: true,
        ),
      );

      int fetchCount = 0;
      final recoveringService = _DynamicQueueService(
        storage: storage,
        onFetch: () async {
          fetchCount++;
          if (fetchCount == 1) {
            throw const QueueServiceException('Network connection failed');
          }
          return const QueueLiveStatusModel(
            currentTicket: 'B-201',
            totalWaiting: 1,
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: QueueScreen(queueService: recoveringService),
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      // 1. Verify error state is visible with retry button
      expect(find.text('Live Queue Unavailable'), findsOneWidget);
      expect(find.text('Network connection failed'), findsOneWidget);
      expect(find.text('Try again'), findsOneWidget);
      final unavailableTicketButton = tester.widget<FloatingActionButton>(
        find.byType(FloatingActionButton),
      );
      expect(unavailableTicketButton.onPressed, isNull);
      expect(unavailableTicketButton.backgroundColor, const Color(0xFFE2E8F0));
      expect(unavailableTicketButton.foregroundColor, const Color(0xFF475569));

      // 2. Tap retry
      await tester.tap(find.text('Try again'));
      await tester.pump();
      await tester.pumpAndSettle();

      // 3. Verify recovered state
      expect(find.text('Live Queue Unavailable'), findsNothing);
      expect(find.text('B-201'), findsOneWidget);
      expect(
        tester
            .widget<FloatingActionButton>(find.byType(FloatingActionButton))
            .onPressed,
        isNotNull,
      );
      expect(
        tester
            .widget<FloatingActionButton>(find.byType(FloatingActionButton))
            .backgroundColor,
        const Color(0xFF0047BA),
      );
    },
  );

  testWidgets('partial failure shows inline retry notice in user ticket card', (
    WidgetTester tester,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    await storage.saveUser(
      const UserModel(
        id: 4,
        username: 'partial_resident',
        email: 'partial@example.com',
        role: 'RESIDENT',
        fullName: 'Partial Resident',
        isVerified: true,
      ),
    );

    final partialService = _DynamicQueueService(
      storage: storage,
      onFetch: () async => const QueueLiveStatusModel(
        currentTicket: 'C-301',
        totalWaiting: 2,
        hasUserTicketsError: true,
        errorMessage: 'Unable to load active tickets',
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: QueueScreen(queueService: partialService),
      ),
    );
    await tester.pump();
    await tester.pumpAndSettle();

    // Live status desk is shown
    expect(find.text('C-301'), findsOneWidget);
    // User ticket card shows error notice rather than "No Active Ticket"
    expect(find.text('Unable to Load Ticket'), findsOneWidget);
    expect(find.text('Unable to load active tickets'), findsOneWidget);
    expect(
      tester
          .widget<FloatingActionButton>(find.byType(FloatingActionButton))
          .onPressed,
      isNull,
    );
  });

  testWidgets('offline ticket snapshot disables new ticket requests', (
    WidgetTester tester,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    await storage.saveUser(
      const UserModel(
        id: 5,
        username: 'offline_resident',
        email: 'offline@example.com',
        role: 'RESIDENT',
        fullName: 'Offline Resident',
        isVerified: true,
      ),
    );

    final offlineService = _DynamicQueueService(
      storage: storage,
      onFetch: () async => const QueueLiveStatusModel(
        isShowingOfflineTicketSnapshot: true,
        userTicket: QueueTicketModel(
          id: 77,
          ticketNumber: 'D-077',
          serviceType: 'Barangay Clearance',
          status: 'WAITING',
        ),
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: QueueScreen(queueService: offlineService),
      ),
    );
    await tester.pump();
    await tester.pumpAndSettle();

    expect(find.text('D-077'), findsOneWidget);
    expect(find.textContaining('Offline:'), findsOneWidget);
    expect(
      tester
          .widget<FloatingActionButton>(find.byType(FloatingActionButton))
          .onPressed,
      isNull,
    );
  });

  testWidgets(
    'partial failure preserves user ticket and displays retry notice in live desk section',
    (WidgetTester tester) async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);
      await storage.saveUser(
        const UserModel(
          id: 6,
          username: 'live_fail_resident',
          email: 'livefail@example.com',
          role: 'RESIDENT',
          fullName: 'Live Fail Resident',
          isVerified: true,
        ),
      );

      int fetchCount = 0;
      final partialLiveFailService = _DynamicQueueService(
        storage: storage,
        onFetch: () async {
          fetchCount++;
          if (fetchCount == 1) {
            return const QueueLiveStatusModel(
              hasLiveStatusError: true,
              liveStatusErrorMessage: 'Live broadcast offline',
              hasUserTicketsError: false,
              userTicket: QueueTicketModel(
                id: 99,
                ticketNumber: 'A-199',
                serviceType: 'Barangay Clearance',
                status: 'WAITING',
              ),
            );
          }
          return const QueueLiveStatusModel(
            currentTicket: 'A-124',
            totalWaiting: 1,
            hasLiveStatusError: false,
            hasUserTicketsError: false,
            userTicket: QueueTicketModel(
              id: 99,
              ticketNumber: 'A-199',
              serviceType: 'Barangay Clearance',
              status: 'WAITING',
            ),
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: QueueScreen(queueService: partialLiveFailService),
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      // 1. Live status error card is rendered with retry button
      expect(find.text('Live Queue Unavailable'), findsOneWidget);
      expect(find.text('Live broadcast offline'), findsOneWidget);
      expect(find.byTooltip('Retry loading live queue status'), findsOneWidget);

      // 2. User's active ticket is preserved and clearly visible!
      expect(find.text('YOUR TICKET'), findsOneWidget);
      expect(find.text('A-199'), findsOneWidget);
      expect(find.text('Barangay Clearance'), findsOneWidget);

      // 3. Tap retry on the live status error card
      await tester.tap(find.byTooltip('Retry loading live queue status'));
      await tester.pump();
      await tester.pumpAndSettle();

      // 4. Live status recovered, user ticket remains visible
      expect(find.text('Live Queue Unavailable'), findsNothing);
      expect(find.text('A-124'), findsOneWidget);
      expect(find.text('A-199'), findsOneWidget);
    },
  );

  testWidgets(
    'true empty queue renders honest empty state without fallback tickets',
    (WidgetTester tester) async {
      final prefs = await SharedPreferences.getInstance();
      final storage = StorageService(prefs);
      await storage.saveUser(
        const UserModel(
          id: 5,
          username: 'empty_resident',
          email: 'empty@example.com',
          role: 'RESIDENT',
          fullName: 'Empty Resident',
          isVerified: true,
        ),
      );

      final emptyService = _DynamicQueueService(
        storage: storage,
        onFetch: () async => const QueueLiveStatusModel(
          currentTicket: null,
          currentService: 'General Service',
          totalWaiting: 0,
          avgWaitMins: 0,
          recentCompleted: [],
          userTicket: null,
        ),
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: QueueScreen(queueService: emptyService),
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      // 1. Hero Card displays '---'
      expect(find.text('---'), findsOneWidget);

      // 2. User Ticket displays honest 'No Active Ticket'
      expect(find.text('No Active Ticket'), findsOneWidget);

      // 3. Live Capacity displays 'Optimal'
      expect(find.text('Optimal'), findsOneWidget);

      // Missing server wait data is shown as unavailable, not a fabricated time.
      expect(find.text('Not available'), findsOneWidget);

      // 5. Recent Completions displays honest empty placeholder
      expect(
        find.text('No completed queue tickets yet today', skipOffstage: false),
        findsOneWidget,
      );
    },
  );
}

class _DynamicQueueService extends QueueService {
  final Future<QueueLiveStatusModel> Function() onFetch;

  _DynamicQueueService({required StorageService storage, required this.onFetch})
    : super(apiClient: ApiClient(), storageService: storage);

  @override
  Future<QueueLiveStatusModel> fetchQueueStatus() => onFetch();
}
