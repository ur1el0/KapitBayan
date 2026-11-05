enum NotificationType { approved, warning, info, queue }

/// Unified UI model for recent notifications synthesized from document updates
/// and community announcements.
class NotificationItemModel {
  final String id;
  final String title;
  final String category;
  final DateTime timestamp;
  final NotificationType type;
  final String? actionRoute;
  final String? description;

  /// Null means this item is synthesized locally and has no persisted read state.
  final bool? isRead;

  const NotificationItemModel({
    required this.id,
    required this.title,
    required this.category,
    required this.timestamp,
    this.type = NotificationType.info,
    this.actionRoute,
    this.description,
    this.isRead,
  });

  bool get isUnread => isRead == false;

  NotificationItemModel copyWith({bool? isRead}) {
    return NotificationItemModel(
      id: id,
      title: title,
      category: category,
      timestamp: timestamp,
      type: type,
      actionRoute: actionRoute,
      description: description,
      isRead: isRead ?? this.isRead,
    );
  }

  /// Formatted relative or short time (e.g. "2 hours ago • Document Services")
  String get formattedSubtitle {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    String timeAgo;
    if (difference.inMinutes < 60) {
      final mins = difference.inMinutes.clamp(1, 60);
      timeAgo = '$mins ${mins == 1 ? 'min' : 'mins'} ago';
    } else if (difference.inHours < 24) {
      final hrs = difference.inHours;
      timeAgo = '$hrs ${hrs == 1 ? 'hour' : 'hours'} ago';
    } else if (difference.inDays < 7) {
      final days = difference.inDays;
      timeAgo = '$days ${days == 1 ? 'day' : 'days'} ago';
    } else {
      timeAgo = '${timestamp.month}/${timestamp.day}';
    }

    return '$timeAgo • $category';
  }
}
