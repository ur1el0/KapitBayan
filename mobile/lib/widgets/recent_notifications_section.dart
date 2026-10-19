import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';
import '../models/notification_item_model.dart';

/// Recent notifications section rendering alert items with status badge indicators
class RecentNotificationsSection extends StatelessWidget {
  final List<NotificationItemModel> notifications;
  final VoidCallback? onViewAll;
  final Function(NotificationItemModel)? onNotificationTap;
  final bool hasError;
  final String? errorMessage;
  final VoidCallback? onRetry;

  const RecentNotificationsSection({
    super.key,
    required this.notifications,
    this.onViewAll,
    this.onNotificationTap,
    this.hasError = false,
    this.errorMessage,
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section Header Row
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Recent Notifications',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
                letterSpacing: -0.3,
              ),
            ),
            GestureDetector(
              onTap: onViewAll,
              child: const Text(
                'View all',
                style: TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w700,
                  color: AppColors.primaryNavy,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),

        // Notifications List Cards
        if (hasError)
          Container(
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFFECACA)),
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
                Container(
                  width: 36,
                  height: 36,
                  decoration: const BoxDecoration(
                    color: Color(0xFFFEE2E2),
                    shape: BoxShape.circle,
                  ),
                  child: const Center(
                    child: Icon(
                      Icons.cloud_off_rounded,
                      color: Color(0xFFDC2626),
                      size: 22,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        notifications.isNotEmpty
                            ? 'Some notifications could not load'
                            : 'Unable to load notifications',
                        style: TextStyle(
                          fontSize: 14.5,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFFB91C1C),
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        errorMessage ?? 'Check connection and tap retry',
                        style: const TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w400,
                          color: AppColors.textMuted,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                if (onRetry != null)
                  IconButton(
                    onPressed: onRetry,
                    tooltip: 'Retry loading notifications',
                    constraints: const BoxConstraints(
                      minWidth: 48,
                      minHeight: 48,
                    ),
                    icon: const Icon(
                      Icons.refresh_rounded,
                      color: AppColors.primaryNavy,
                    ),
                  ),
              ],
            ),
          ),
        if (!hasError && notifications.isEmpty)
          Container(
            padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFF1F5F9)),
            ),
            child: const Center(
              child: Text(
                'No new notifications at this time.',
                style: TextStyle(fontSize: 13.5, color: AppColors.textMuted),
              ),
            ),
          ),
        if (notifications.isNotEmpty)
          Column(
            children: notifications.take(2).map((item) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: _NotificationCard(
                  notification: item,
                  onTap: () => onNotificationTap?.call(item),
                ),
              );
            }).toList(),
          ),
      ],
    );
  }
}

class _NotificationCard extends StatelessWidget {
  final NotificationItemModel notification;
  final VoidCallback? onTap;

  const _NotificationCard({required this.notification, this.onTap});

  @override
  Widget build(BuildContext context) {
    Color iconBgColor;
    Color iconColor;
    IconData iconData;

    switch (notification.type) {
      case NotificationType.approved:
        iconBgColor = const Color(0xFFE0F2FE);
        iconColor = const Color(0xFF0284C7);
        iconData = Icons.check_circle_outline_rounded;
        break;
      case NotificationType.warning:
        iconBgColor = const Color(0xFFFEE2E2);
        iconColor = const Color(0xFFEF4444);
        iconData = Icons.warning_amber_rounded;
        break;
      case NotificationType.info:
        iconBgColor = const Color(0xFFF1F5F9);
        iconColor = AppColors.primaryNavy;
        iconData = Icons.notifications_none_rounded;
        break;
      case NotificationType.queue:
        iconBgColor = const Color(0xFFE0E7FF);
        iconColor = AppColors.primaryNavy;
        iconData = Icons.confirmation_number_outlined;
        break;
    }

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0F172A).withValues(alpha: 0.03),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
        border: Border.all(color: const Color(0xFFF1F5F9), width: 1.2),
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: 12.0,
              vertical: 10.0,
            ),
            child: Row(
              children: [
                // Circular Status Badge Icon
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: iconBgColor,
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Icon(iconData, color: iconColor, size: 22),
                  ),
                ),
                const SizedBox(width: 10),

                // Title and Timestamp Subtitle
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        notification.title,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: AppColors.textPrimary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        notification.formattedSubtitle,
                        style: const TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w400,
                          color: AppColors.textMuted,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
