import 'package:flutter/material.dart';
import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';
import '../models/activity_schedule_model.dart';

/// Community schedule vertical timeline section matching reference design
class CommunityScheduleSection extends StatelessWidget {
  final List<ActivityScheduleModel> activities;
  final Function(ActivityScheduleModel)? onActivityTap;

  const CommunityScheduleSection({
    super.key,
    required this.activities,
    this.onActivityTap,
  });

  @override
  Widget build(BuildContext context) {
    // If backend has no activity events yet, populate with sample events matching design
    final displayList = activities.isNotEmpty
        ? activities
        : [
            ActivityScheduleModel(
              id: 1,
              title: 'Vaccination Drive',
              description: 'Free basic immunization and health checkup for residents',
              eventDatetime: DateTime.now(),
              location: 'Barangay Center',
            ),
            ActivityScheduleModel(
              id: 2,
              title: 'Town Hall Meeting',
              description: 'Quarterly barangay assembly and community forum',
              eventDatetime: DateTime(DateTime.now().year, 10, 24, 16, 0),
              location: 'Covered Court',
            ),
            ActivityScheduleModel(
              id: 3,
              title: 'Eco-Waste Clean Up',
              description: 'Community cleanup drive along railroad sectors',
              eventDatetime: DateTime(DateTime.now().year, 10, 26, 7, 0),
              location: 'Rail Road Lines',
            ),
          ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.tr('Community Schedule'),
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w800,
            color: AppColors.textPrimary,
            letterSpacing: -0.3,
          ),
        ),
        const SizedBox(height: 12),

        // Rounded timeline container
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 24.0),
          decoration: BoxDecoration(
            color: const Color(0xFFF1F5F9).withValues(alpha: 0.65),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: const Color(0xFFE2E8F0),
              width: 1.0,
            ),
          ),
          child: Column(
            children: List.generate(displayList.length, (index) {
              final item = displayList[index];
              final isLast = index == displayList.length - 1;
              final isActive = index == 0 || item.isToday;

              return IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Timeline Line and Dot
                    Column(
                      children: [
                        // Dot Ring Indicator
                        Container(
                          width: 20,
                          height: 20,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: isActive
                                ? AppColors.primaryNavy
                                : Colors.transparent,
                            border: Border.all(
                              color: isActive
                                  ? AppColors.primaryNavy
                                  : const Color(0xFFCBD5E1),
                              width: isActive ? 5 : 4,
                            ),
                          ),
                          child: isActive
                              ? const Center(
                                  child: SizedBox(
                                    width: 6,
                                    height: 6,
                                    child: DecoratedBox(
                                      decoration: BoxDecoration(
                                        color: Colors.white,
                                        shape: BoxShape.circle,
                                      ),
                                    ),
                                  ),
                                )
                              : null,
                        ),

                        // Connecting Vertical Line
                        if (!isLast)
                          Expanded(
                            child: Container(
                              width: 1.5,
                              color: const Color(0xFFCBD5E1),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(width: 16),

                    // Event Details
                    Expanded(
                      child: GestureDetector(
                        onTap: () => onActivityTap?.call(item),
                        child: Padding(
                          padding: EdgeInsets.only(bottom: isLast ? 0 : 24.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Date/Time Tag
                              Text(
                                item.timelineDateTag,
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w800,
                                  color: isActive
                                      ? AppColors.primaryNavy
                                      : AppColors.textMuted,
                                  letterSpacing: 0.8,
                                ),
                              ),
                              const SizedBox(height: 4),

                              // Event Title
                              Text(
                                context.tr(item.title),
                                style: const TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w800,
                                  color: AppColors.textPrimary,
                                  letterSpacing: -0.2,
                                ),
                              ),
                              const SizedBox(height: 2),

                              // Event Location
                              Text(
                                context.tr(item.location),
                                style: const TextStyle(
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w400,
                                  color: AppColors.textMuted,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }),
          ),
        ),
      ],
    );
  }
}
