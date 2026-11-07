enum ResidentNotificationTargetType { queueTicket, documentRequest }

class ResidentNotificationTarget {
  const ResidentNotificationTarget({required this.type, required this.id});

  final ResidentNotificationTargetType type;
  final int id;

  static ResidentNotificationTarget? tryParse(Map<String, dynamic> data) {
    final type = data['type']?.toString().toLowerCase();
    final idValue = switch (type) {
      'queue' => data['ticket_id'],
      'document' => data['request_id'] ?? data['document_request_id'],
      _ =>
        data['ticket_id'] ?? data['request_id'] ?? data['document_request_id'],
    };
    final id = int.tryParse(idValue?.toString() ?? '');
    if (id == null || id <= 0) return null;

    final targetType = switch (type) {
      'queue' => ResidentNotificationTargetType.queueTicket,
      'document' => ResidentNotificationTargetType.documentRequest,
      _ when data.containsKey('ticket_id') =>
        ResidentNotificationTargetType.queueTicket,
      _
          when data.containsKey('request_id') ||
              data.containsKey('document_request_id') =>
        ResidentNotificationTargetType.documentRequest,
      _ => null,
    };
    if (targetType == null) return null;
    return ResidentNotificationTarget(type: targetType, id: id);
  }
}
