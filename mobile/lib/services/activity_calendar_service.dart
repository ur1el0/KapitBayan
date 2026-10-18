import 'package:add_2_calendar/add_2_calendar.dart';

import '../models/activity_schedule_model.dart';

typedef CalendarEventLauncher = Future<bool> Function(Event event);

class ActivityCalendarService {
  ActivityCalendarService({CalendarEventLauncher? addEvent})
    : _addEvent = addEvent ?? Add2Calendar.addEvent2Cal;

  final CalendarEventLauncher _addEvent;

  Future<bool> addActivity(ActivityScheduleModel activity) {
    final startDate = activity.eventDatetime.toLocal();
    final event = Event(
      title: activity.title,
      description: activity.description,
      location: activity.location,
      startDate: startDate,
      // Activity schedules currently provide a start time but no end time.
      endDate: startDate.add(const Duration(hours: 1)),
    );

    return _addEvent(event);
  }
}
