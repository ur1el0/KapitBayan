import 'package:flutter/material.dart';
import '../core/localization/app_language.dart';

import '../core/theme/app_colors.dart';
import '../models/notification_item_model.dart';

class NotificationCenterSheet extends StatelessWidget {
  final List<NotificationItemModel> notifications;
  final ScrollController scrollController;
  final bool hasError;
  final String? errorMessage;
  final VoidCallback? onRetry;

  const NotificationCenterSheet({
    super.key,
    required this.notifications,
    required this.scrollController,
    this.hasError = false,
    this.errorMessage,
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey[300],
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                context.tr('Notification Center'),
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: hasError
                      ? const Color(0xFFFEE2E2)
                      : AppColors.primaryNavy.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  hasError
                      ? context.tr(notifications.isEmpty ? 'Error' : 'Partial')
                      : '${notifications.length} ${context.tr('Active')}',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: hasError
                        ? const Color(0xFFDC2626)
                        : AppColors.primaryNavy,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: hasError && notifications.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(20.0),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.cloud_off_rounded,
                            color: Color(0xFFDC2626),
                            size: 40,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            context.tr('Unable to load notifications'),
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFFB91C1C),
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            context.tr(errorMessage ??
                                'Failed to retrieve notification updates'),
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: AppColors.textMuted,
                              fontSize: 13,
                            ),
                          ),
                          if (onRetry != null) ...[
                            const SizedBox(height: 16),
                            OutlinedButton.icon(
                              onPressed: onRetry,
                              icon: const Icon(Icons.refresh_rounded, size: 18),
                              label: Text(context.tr('Try again')),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: AppColors.primaryNavy,
                                side: const BorderSide(
                                  color: AppColors.primaryNavy,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  )
                : notifications.isEmpty
                ? Center(
                    child: Text(
                      context.tr('No recent notifications'),
                      style: TextStyle(color: AppColors.textMuted),
                    ),
                  )
                : Column(
                    children: [
                      if (hasError)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Row(
                            children: [
                              const Icon(
                                Icons.cloud_off_rounded,
                                color: Color(0xFFDC2626),
                                size: 20,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  errorMessage ??
                                      'Some notification updates could not load.',
                                  style: const TextStyle(
                                    color: Color(0xFFB91C1C),
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                              if (onRetry != null)
                                IconButton(
                                  tooltip: 'Try again',
                                  onPressed: onRetry,
                                  icon: const Icon(Icons.refresh_rounded),
                                ),
                            ],
                          ),
                        ),
                      Expanded(
                        child: ListView.separated(
                          controller: scrollController,
                          itemCount: notifications.length,
                          separatorBuilder: (_, _) => const Divider(height: 20),
                          itemBuilder: (context, index) {
                            final item = notifications[index];
                            final approved =
                                item.type == NotificationType.approved;
                            final queueAlert =
                                item.type == NotificationType.queue;
                            return Padding(
                              padding: const EdgeInsets.symmetric(vertical: 4),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.all(8),
                                    decoration: BoxDecoration(
                                      color: approved
                                          ? const Color(0xFFDCFCE7)
                                          : queueAlert
                                          ? const Color(0xFFE0E7FF)
                                          : const Color(0xFFFEF3C7),
                                      shape: BoxShape.circle,
                                    ),
                                    child: Icon(
                                      approved
                                          ? Icons.check_circle_rounded
                                          : queueAlert
                                          ? Icons.confirmation_number_outlined
                                          : Icons.info_rounded,
                                      color: approved
                                          ? const Color(0xFF15803D)
                                          : queueAlert
                                          ? AppColors.primaryNavy
                                          : const Color(0xFFB45309),
                                      size: 20,
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          item.title,
                                          style: const TextStyle(
                                            fontSize: 14,
                                            fontWeight: FontWeight.bold,
                                            color: AppColors.textPrimary,
                                          ),
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          item.category,
                                          style: const TextStyle(
                                            fontSize: 12,
                                            color: AppColors.textMuted,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}

class NotificationDetailSheet extends StatelessWidget {
  final NotificationItemModel item;

  const NotificationDetailSheet({super.key, required this.item});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: const Color(0xFFCBD5E1),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: const Color(0xFFEFF6FF),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.notifications_active_rounded,
                    color: AppColors.primaryNavy,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.title,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        item.formattedSubtitle,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.textMuted,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Text(
                item.description?.trim().isNotEmpty == true
                    ? item.description!.trim()
                    : context.tr('Advisory Category: {category}\n\nOfficial notice regarding "{title}". Check your document requests or community bulletin for real-time status updates.')
                        .replaceAll('{category}', item.category)
                        .replaceAll('{title}', item.title),
                style: const TextStyle(
                  fontSize: 13.5,
                  color: AppColors.textPrimary,
                  height: 1.5,
                ),
              ),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primaryNavy,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: Text(
                  context.tr('Dismiss'),
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
