import 'package:add_2_calendar/add_2_calendar.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/activity_schedule_model.dart';
import 'package:mobile/services/activity_calendar_service.dart';

void main() {
  group('ActivityCalendarService', () {
    test(
      'maps schedule details into a one-hour local calendar event',
      () async {
        final activityStart = DateTime.utc(2026, 10, 20, 4, 30);
        Event? launchedEvent;
        final calendar = ActivityCalendarService(
          addEvent: (event) async {
            launchedEvent = event;
            return true;
          },
        );

        final opened = await calendar.addActivity(
          ActivityScheduleModel(
            id: 9,
            title: 'Barangay Health Day',
            description: 'Free checkups',
            eventDatetime: activityStart,
            location: 'Barangay Hall',
          ),
        );

        expect(opened, isTrue);
        expect(launchedEvent?.title, 'Barangay Health Day');
        expect(launchedEvent?.description, 'Free checkups');
        expect(launchedEvent?.location, 'Barangay Hall');
        expect(launchedEvent?.startDate, activityStart.toLocal());
        expect(
          launchedEvent?.endDate.difference(launchedEvent!.startDate),
          const Duration(hours: 1),
        );
      },
    );

    test('returns false when the device has no calendar handler', () async {
      final calendar = ActivityCalendarService(addEvent: (_) async => false);
      final opened = await calendar.addActivity(
        ActivityScheduleModel(
          id: 10,
          title: 'Assembly',
          description: '',
          eventDatetime: DateTime(2026, 10, 20, 9),
          location: 'Barangay Hall',
        ),
      );

      expect(opened, isFalse);
    });
  });
}
