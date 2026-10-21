import 'package:flutter/material.dart';
import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';
import '../models/activity_schedule_model.dart';

/// Event card displayed in the "Upcoming Events" section matching reference UI
class ScheduleEventCard extends StatelessWidget {
  final ActivityScheduleModel activity;
  final VoidCallback? onAddToCalendar;
  final VoidCallback? onTap;

  const ScheduleEventCard({
    super.key,
    required this.activity,
    this.onAddToCalendar,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: const Color(0xFFE2E8F0),
            width: 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Row: Title and Thumbnail placeholder
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    context.tr(activity.title),
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w900,
                      color: AppColors.textPrimary,
                      letterSpacing: -0.3,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: const Color(0xFFCBD5E1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Center(
                    child: Icon(
                      _getEventIcon(activity.title),
                      size: 22,
                      color: const Color(0xFF475569),
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 8),

            // Date & Time Row
            Row(
              children: [
                const Icon(
                  Icons.calendar_today_outlined,
                  size: 15,
                  color: Color(0xFF64748B),
                ),
                const SizedBox(width: 6),
                Text(
                  activity.formattedEventDateTime,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF475569),
                  ),
                ),
              ],
            ),

            if (activity.description.isNotEmpty) ...[
              const SizedBox(height: 12),
              // Description
              Text(
                activity.description,
                style: const TextStyle(
                  fontSize: 13.5,
                  height: 1.45,
                  color: Color(0xFF475569),
                  fontWeight: FontWeight.w400,
                ),
              ),
            ],

            const SizedBox(height: 12),

            // Location Row
            Row(
              children: [
                const Icon(
                  Icons.location_on_outlined,
                  size: 15,
                  color: Color(0xFF64748B),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                context.tr(activity.location),
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF475569),
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 18),

            // Add to Calendar Outline Button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: onAddToCalendar,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.white,
                  foregroundColor: AppColors.primaryNavy,
                  elevation: 0,
                  side: const BorderSide(
                    color: Color(0xFFE2E8F0),
                    width: 1.0,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.calendar_month_outlined,
                      size: 18,
                      color: AppColors.primaryNavy,
                    ),
                    SizedBox(width: 8),
                    Text(
                      context.tr('Add to Calendar'),
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        color: AppColors.primaryNavy,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getEventIcon(String title) {
    final lower = title.toLowerCase();
    if (lower.contains('health') || lower.contains('medical') || lower.contains('clinic') || lower.contains('vaccine')) {
      return Icons.medical_services_outlined;
    }
    if (lower.contains('assembly') || lower.contains('meeting') || lower.contains('session')) {
      return Icons.groups_outlined;
    }
    if (lower.contains('clean') || lower.contains('waste') || lower.contains('environment')) {
      return Icons.eco_outlined;
    }
    if (lower.contains('sports') || lower.contains('game') || lower.contains('league')) {
      return Icons.sports_basketball_outlined;
    }
    return Icons.event_outlined;
  }
}
