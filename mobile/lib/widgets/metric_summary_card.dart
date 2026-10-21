import 'package:flutter/material.dart';

import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';
import 'app_surface.dart';

/// 2-column metrics summary row displaying announcement count and pending request count
class MetricSummaryRow extends StatelessWidget {
  final int announcementCount;
  final int pendingRequestCount;
  final bool hasNewAnnouncements;
  final VoidCallback? onAnnouncementsTap;
  final VoidCallback? onPendingRequestsTap;

  const MetricSummaryRow({
    super.key,
    required this.announcementCount,
    required this.pendingRequestCount,
    this.hasNewAnnouncements = true,
    this.onAnnouncementsTap,
    this.onPendingRequestsTap,
  });

  @override
  Widget build(BuildContext context) {
    final annCountStr = announcementCount.toString().padLeft(2, '0');
    final reqCountStr = pendingRequestCount.toString().padLeft(2, '0');

    return Row(
      children: [
        // Announcements Metric Card
        Expanded(
          child: _MetricCard(
            icon: Icons.campaign_outlined,
            iconColor: AppColors.primaryNavy,
            badgeText: hasNewAnnouncements ? context.tr('New') : null,
            count: annCountStr,
            label: context.tr('ANNOUNCEMENTS'),
            onTap: onAnnouncementsTap,
          ),
        ),
        const SizedBox(width: 14),

        // My Pending Requests Metric Card
        Expanded(
          child: _MetricCard(
            icon: Icons.assignment_outlined,
            iconColor: const Color(0xFFC2410C), // Warm amber/orange accent
            count: reqCountStr,
            label: context.tr('MY PENDING\nREQUESTS'),
            onTap: onPendingRequestsTap,
          ),
        ),
      ],
    );
  }
}

class _MetricCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String? badgeText;
  final String count;
  final String label;
  final VoidCallback? onTap;

  const _MetricCard({
    required this.icon,
    required this.iconColor,
    this.badgeText,
    required this.count,
    required this.label,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 132),
      child: AppSurface(
        onTap: onTap,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            // Icon and optional Badge
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Icon(icon, color: iconColor, size: 24),
                if (badgeText != null)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFDBEAFE),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      badgeText!,
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF1E40AF),
                      ),
                    ),
                  ),
              ],
            ),

            // Numbers and Label
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(count, style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 4),
                Text(
                  label,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: AppColors.textSecondary,
                    letterSpacing: 0.6,
                    height: 1.2,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
