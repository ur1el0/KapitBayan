import 'package:flutter/material.dart';
import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';
import '../models/queue_ticket_model.dart';

/// Section listing recently serviced and completed queue tickets
class RecentCompletionsSection extends StatelessWidget {
  final List<QueueTicketModel> completedTickets;
  final VoidCallback? onViewAll;

  const RecentCompletionsSection({
    super.key,
    required this.completedTickets,
    this.onViewAll,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section Header
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              context.tr('Recent Completions'),
              style: TextStyle(
                color: Color(0xFF0F172A),
                fontSize: 18,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
              ),
            ),
            GestureDetector(
              onTap: onViewAll,
              behavior: HitTestBehavior.opaque,
              child: Text(
                context.tr('VIEW ALL'),
                style: TextStyle(
                  color: AppColors.primaryNavy,
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.6,
                ),
              ),
            ),
          ],
        ),

        const SizedBox(height: 14),

        // List of Completed Ticket Cards
        if (completedTickets.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20.0),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Center(
              child: Text(
                context.tr('No completed queue tickets yet today'),
                style: TextStyle(
                  color: Color(0xFF64748B),
                  fontSize: 13.5,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          )
        else
          ...completedTickets.take(4).map((ticket) {
            return Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 12.0),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(18),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF0F172A).withValues(alpha: 0.03),
                    blurRadius: 10,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: Row(
                children: [
                  // Left Ticket Number Badge
                  Container(
                    width: 52,
                    height: 38,
                    decoration: BoxDecoration(
                      color: const Color(0xFFEDF3FA),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      ticket.ticketNumber,
                      style: const TextStyle(
                        color: AppColors.primaryNavy,
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.2,
                      ),
                    ),
                  ),

                  const SizedBox(width: 14),

                  // Middle Service Info & Time
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          ticket.serviceType,
                          style: const TextStyle(
                            color: Color(0xFF0F172A),
                            fontSize: 14.5,
                            fontWeight: FontWeight.w700,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          ticket.completedTimeAgo,
                          style: const TextStyle(
                            color: Color(0xFF64748B),
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Right Completion Indicator Icon
                  const Icon(
                    Icons.check_circle_outline_rounded,
                    color: Color(0xFF10B981),
                    size: 22,
                  ),
                ],
              ),
            );
          }),
      ],
    );
  }
}
