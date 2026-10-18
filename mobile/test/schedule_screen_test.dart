import 'package:add_2_calendar/add_2_calendar.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/models/activity_schedule_model.dart';
import 'package:mobile/models/document_request_model.dart';
import 'package:mobile/models/user_model.dart';
import 'package:mobile/screens/schedule_screen.dart';
import 'package:mobile/services/activity_calendar_service.dart';
import 'package:mobile/services/schedule_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:mobile/widgets/appointment_schedule_card.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MockScheduleService extends ScheduleService {
  MockScheduleService({required StorageService storage})
      : super(
          apiClient: ApiClient(),
          storageService: storage,
        );

  @override
  Future<ScheduleData> fetchScheduleData() async {
    final now = DateTime.now();
    return ScheduleData(
      user: const UserModel(
        id: 1,
        username: 'juan_delacruz',
        email: 'juan@example.com',
        fullName: 'Juan Dela Cruz',
        role: 'RESIDENT',
      ),
      activities: [
        ActivityScheduleModel(
          id: 1,
          title: 'Mobile Health Clinic',
          description: 'Free check-ups, flu vaccines, and basic consultations for all residents.',
          eventDatetime: DateTime(now.year, now.month, now.day, 8, 0),
          location: 'Community Covered Court',
        ),
        ActivityScheduleModel(
          id: 2,
          title: 'Barangay Assembly',
          description: 'Quarterly meeting to discuss new community infrastructure projects.',
          eventDatetime: DateTime(now.year, now.month, now.day + 4, 16, 0),
          location: 'Main Hall, Brgy. Center',
        ),
      ],
      documentRequests: [
        DocumentRequestModel(
          id: 9201,
          documentType: 'Barangay Clearance',
          status: 'READY_FOR_PICKUP',
          createdAt: DateTime(now.year, now.month, now.day),
        ),
      ],
    );
  }
}

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({
      'access_token': 'dummy_jwt_token',
      'user_data': '{"id": 1, "username": "juan_delacruz", "email": "juan@example.com", "full_name": "Juan Dela Cruz", "role": "RESIDENT"}',
    });
  });

  Widget createScheduleScreenTestWidget(
    ScheduleService service, {
    ActivityCalendarService? calendarService,
  }) {
    return MaterialApp(
      theme: AppTheme.lightTheme,
      home: ScheduleScreen(
        scheduleService: service,
        calendarService: calendarService,
      ),
    );
  }

  testWidgets('ScheduleScreen renders all key UI sections matching reference design', (WidgetTester tester) async {
    final storage = await StorageService.init();
    final mockService = MockScheduleService(storage: storage);

    await tester.pumpWidget(createScheduleScreenTestWidget(mockService));
    await tester.pumpAndSettle();

    // 1. Verify KapitBayan Logo Header & Avatar
    expect(find.text('KapitBayan'), findsOneWidget);
    expect(find.text('J'), findsOneWidget); // User initial

    // 2. Verify "MY APPOINTMENTS" Section and "ACTIVE ONGOING REQUESTS" Section
    expect(find.text('MY APPOINTMENTS'), findsOneWidget);
    expect(find.text('ACTIVE ONGOING REQUESTS'), findsOneWidget);
    expect(find.text('1 Active'), findsOneWidget);
    expect(find.text('CONFIRMED'), findsNWidgets(2));
    expect(find.text('Document Pickup'), findsNWidgets(2));
    expect(find.text('Barangay Clearance (ID-9201)'), findsNWidgets(2));

    // 3. Verify "Upcoming Events" Section
    expect(find.text('Upcoming Events'), findsOneWidget);
    expect(find.text('View All'), findsOneWidget);
    expect(find.text('Mobile Health Clinic'), findsOneWidget);
    expect(find.text('Community Covered Court'), findsOneWidget);
    expect(find.text('Add to Calendar'), findsWidgets);

    // 4. Verify Custom Bottom Navigation Bar tab selection
    expect(find.text('SCHEDULE'), findsOneWidget);
    expect(find.text('DASHBOARD'), findsOneWidget);
    expect(find.text('QUEUE'), findsOneWidget);
    expect(find.text('DOCUMENTS'), findsOneWidget);
  });

  testWidgets('Add to Calendar launches the event form and asks resident to save', (WidgetTester tester) async {
    final storage = await StorageService.init();
    final mockService = MockScheduleService(storage: storage);
    Event? launchedEvent;
    final calendarService = ActivityCalendarService(
      addEvent: (event) async {
        launchedEvent = event;
        return true;
      },
    );

    await tester.pumpWidget(createScheduleScreenTestWidget(
      mockService,
      calendarService: calendarService,
    ));
    await tester.pumpAndSettle();

    // Find the Add to Calendar button and scroll to it
    final addBtn = find.text('Add to Calendar').first;
    await tester.ensureVisible(addBtn);
    await tester.pumpAndSettle();

    await tester.tap(addBtn);
    await tester.pumpAndSettle();

    final event = launchedEvent;
    expect(event, isNotNull);
    expect(event!.title, 'Mobile Health Clinic');
    expect(event.description, contains('Free check-ups'));
    expect(event.location, 'Community Covered Court');
    expect(find.text('Calendar opened. Review and save the event there.'), findsOneWidget);
  });

  testWidgets('Add to Calendar shows failure when the plugin throws', (WidgetTester tester) async {
    final storage = await StorageService.init();
    final mockService = MockScheduleService(storage: storage);
    final calendarService = ActivityCalendarService(
      addEvent: (_) async => throw StateError('No calendar handler'),
    );

    await tester.pumpWidget(createScheduleScreenTestWidget(
      mockService,
      calendarService: calendarService,
    ));
    await tester.pumpAndSettle();

    final addBtn = find.text('Add to Calendar').first;
    await tester.ensureVisible(addBtn);
    await tester.tap(addBtn);
    await tester.pumpAndSettle();

    expect(find.text('Could not open your device calendar.'), findsOneWidget);
  });

  testWidgets('API failure displays visible retry state and recovers on retry', (WidgetTester tester) async {
    final storage = await StorageService.init();
    var fail = true;
    final dynamicService = _DynamicScheduleService(
      storage: storage,
      onFetch: () async {
        if (fail) {
          throw const ScheduleServiceException('Server connection timed out');
        }
        return const ScheduleData(
          user: UserModel(
            id: 1,
            username: 'juan_delacruz',
            email: 'juan@example.com',
            fullName: 'Juan Dela Cruz',
            role: 'RESIDENT',
          ),
          activities: [],
          documentRequests: [],
        );
      },
    );

    await tester.pumpWidget(createScheduleScreenTestWidget(dynamicService));
    await tester.pumpAndSettle();

    // Verify error state
    expect(find.text('Unable to load schedule data'), findsOneWidget);
    expect(find.text('Server connection timed out'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);

    // Now recover
    fail = false;
    await tester.tap(find.text('Try again'));
    await tester.pump();
    await tester.pumpAndSettle();

    // Verify error state is cleared
    expect(find.text('Unable to load schedule data'), findsNothing);
    expect(find.text('MY APPOINTMENTS'), findsOneWidget);
    expect(find.text('Upcoming Events'), findsOneWidget);
  });

  testWidgets('partial failure displays inline retry notices in affected sections', (WidgetTester tester) async {
    final storage = await StorageService.init();
    final partialService = _DynamicScheduleService(
      storage: storage,
      onFetch: () async => const ScheduleData(
        hasAppointmentsError: true,
        hasActivitiesError: true,
        errorMessage: 'Some schedule details could not be updated.',
      ),
    );

    await tester.pumpWidget(createScheduleScreenTestWidget(partialService));
    await tester.pumpAndSettle();

    expect(find.text('Unable to update appointments.'), findsOneWidget);
    expect(find.text('Unable to update community events.'), findsOneWidget);
  });

  testWidgets('selecting date with no records shows honest empty states and isolates active requests', (WidgetTester tester) async {
    final storage = await StorageService.init();
    final now = DateTime.now();
    final mockService = _DynamicScheduleService(
      storage: storage,
      onFetch: () async => ScheduleData(
        user: const UserModel(
          id: 1,
          username: 'juan_delacruz',
          email: 'juan@example.com',
          fullName: 'Juan Dela Cruz',
          role: 'RESIDENT',
        ),
        activities: [
          ActivityScheduleModel(
            id: 1,
            title: 'Mobile Health Clinic',
            description: 'Health consultations',
            eventDatetime: DateTime(now.year, now.month, now.day, 9, 0),
            location: 'Covered Court',
          ),
        ],
        documentRequests: [
          DocumentRequestModel(
            id: 9201,
            documentType: 'Barangay Clearance',
            status: 'READY_FOR_PICKUP',
            createdAt: DateTime(now.year, now.month, now.day),
          ),
        ],
      ),
    );

    await tester.pumpWidget(createScheduleScreenTestWidget(mockService));
    await tester.pumpAndSettle();

    // Initial state: today has appointment in MY APPOINTMENTS and also appears in ACTIVE ONGOING REQUESTS
    expect(find.text('Barangay Clearance (ID-9201)'), findsNWidgets(2));
    expect(find.text('Mobile Health Clinic'), findsOneWidget);
    expect(find.text('ACTIVE ONGOING REQUESTS'), findsOneWidget);
    expect(find.text('1 Active'), findsOneWidget);

    // Tap next week chevron to navigate to next week
    await tester.tap(find.byIcon(Icons.chevron_right_rounded));
    await tester.pumpAndSettle();

    // For selected date: honest empty placeholders
    expect(find.text('No appointments scheduled for this date'), findsOneWidget);
    expect(find.text('No community events scheduled'), findsOneWidget);

    // Active ongoing request remains in dedicated ACTIVE ONGOING REQUESTS section
    expect(find.text('ACTIVE ONGOING REQUESTS'), findsOneWidget);
    expect(find.text('1 Active'), findsOneWidget);
    expect(find.text('Barangay Clearance (ID-9201)'), findsOneWidget);
  });

  testWidgets('true empty schedule renders honest empty states without fabricated data', (WidgetTester tester) async {
    final storage = await StorageService.init();
    final emptyService = _DynamicScheduleService(
      storage: storage,
      onFetch: () async => const ScheduleData(
        activities: [],
        documentRequests: [],
      ),
    );

    await tester.pumpWidget(createScheduleScreenTestWidget(emptyService));
    await tester.pumpAndSettle();

    expect(find.text('No appointments scheduled for this date'), findsOneWidget);
    expect(find.text('No community events scheduled'), findsOneWidget);
    expect(find.text('ACTIVE ONGOING REQUESTS'), findsNothing);
  });

  testWidgets('displays and makes accessible all active requests when three or more exist', (WidgetTester tester) async {
    final storage = await StorageService.init();
    final now = DateTime.now();
    final serviceWith3Active = _DynamicScheduleService(
      storage: storage,
      onFetch: () async => ScheduleData(
        user: const UserModel(
          id: 1,
          username: 'juan_delacruz',
          email: 'juan@example.com',
          fullName: 'Juan Dela Cruz',
          role: 'RESIDENT',
        ),
        activities: [],
        documentRequests: [
          DocumentRequestModel(
            id: 9201,
            documentType: 'Barangay Clearance',
            status: 'READY_FOR_PICKUP',
            createdAt: DateTime(now.year, now.month, now.day),
          ),
          DocumentRequestModel(
            id: 9202,
            documentType: 'Certificate of Residency',
            status: 'PROCESSING',
            createdAt: DateTime(now.year, now.month, now.day),
          ),
          DocumentRequestModel(
            id: 9203,
            documentType: 'Certificate of Indigency',
            status: 'PENDING',
            createdAt: DateTime(now.year, now.month, now.day),
          ),
        ],
      ),
    );

    await tester.pumpWidget(createScheduleScreenTestWidget(serviceWith3Active));
    await tester.pumpAndSettle();

    // Verify the dedicated active section header and badge
    expect(find.text('ACTIVE ONGOING REQUESTS'), findsOneWidget);
    expect(find.text('3 Active'), findsOneWidget);

    // Specifically verify the dedicated active ongoing requests list
    final activeListFinder = find.byKey(const Key('active_ongoing_requests_list'));
    expect(activeListFinder, findsOneWidget);

    // Verify all 3 items are present in the dedicated active section (would fail if capped at 2)
    final activeCards = find.descendant(
      of: activeListFinder,
      matching: find.byType(AppointmentScheduleCard),
    );
    expect(activeCards, findsNWidgets(3));

    expect(
      find.descendant(
        of: activeListFinder,
        matching: find.text('Barangay Clearance (ID-9201)'),
      ),
      findsOneWidget,
    );
    expect(
      find.descendant(
        of: activeListFinder,
        matching: find.text('Certificate of Residency (ID-9202)'),
      ),
      findsOneWidget,
    );
    expect(
      find.descendant(
        of: activeListFinder,
        matching: find.text('Certificate of Indigency (ID-9203)'),
      ),
      findsOneWidget,
    );

    // Distinct date-filtered daily section preserves its own preview results (capped at 2)
    final dailyListFinder = find.byKey(const Key('daily_appointments_list'));
    expect(dailyListFinder, findsOneWidget);
    expect(
      find.descendant(
        of: dailyListFinder,
        matching: find.byType(AppointmentScheduleCard),
      ),
      findsNWidgets(2),
    );

    // Verify tapping on the 3rd request in the dedicated active section opens its details modal
    final thirdActiveRequest = find.descendant(
      of: activeListFinder,
      matching: find.byKey(const Key('active_request_card_9203')),
    );
    await tester.ensureVisible(thirdActiveRequest);
    await tester.tap(thirdActiveRequest);
    await tester.pumpAndSettle();

    expect(find.text('Close'), findsOneWidget);
    expect(find.textContaining('CI-2026-9203'), findsOneWidget);
  });
}

class _DynamicScheduleService extends ScheduleService {
  final Future<ScheduleData> Function() onFetch;

  _DynamicScheduleService({
    required StorageService storage,
    required this.onFetch,
  }) : super(
          apiClient: ApiClient(),
          storageService: storage,
        );

  @override
  Future<ScheduleData> fetchScheduleData() => onFetch();
}
