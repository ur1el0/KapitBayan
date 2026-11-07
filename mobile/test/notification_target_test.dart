import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/navigation/notification_target.dart';

void main() {
  test('parses a queue notification into its ticket detail target', () {
    final target = ResidentNotificationTarget.tryParse({
      'type': 'queue',
      'ticket_id': '41',
    });

    expect(target?.type, ResidentNotificationTargetType.queueTicket);
    expect(target?.id, 41);
  });

  test('parses document notification payloads from supported ID keys', () {
    expect(
      ResidentNotificationTarget.tryParse({
        'type': 'document',
        'request_id': '12',
      })?.id,
      12,
    );
    expect(
      ResidentNotificationTarget.tryParse({
        'type': 'document',
        'document_request_id': 13,
      })?.id,
      13,
    );
  });

  test('ignores missing, invalid, nonpositive, and unrelated IDs', () {
    expect(ResidentNotificationTarget.tryParse({}), isNull);
    expect(
      ResidentNotificationTarget.tryParse({'type': 'queue', 'ticket_id': 'x'}),
      isNull,
    );
    expect(
      ResidentNotificationTarget.tryParse({
        'type': 'document',
        'request_id': 0,
      }),
      isNull,
    );
    expect(
      ResidentNotificationTarget.tryParse({'type': 'system', 'id': 123}),
      isNull,
    );
  });
}
