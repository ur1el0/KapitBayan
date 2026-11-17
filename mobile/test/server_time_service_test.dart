import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/server_time_service.dart';

void main() {
  group('ServerTimeService', () {
    setUp(() {
      ServerTimeService.resetForTesting();
    });

    test('defaults to zero skew when unsynchronized', () {
      expect(ServerTimeService.isSynchronized, isFalse);
      expect(ServerTimeService.clockSkew, Duration.zero);
      final diff = DateTime.now().difference(ServerTimeService.now()).abs();
      expect(diff.inMilliseconds, lessThan(100));
    });

    test('calculates skew correctly from X-Server-Time ISO string', () {
      final nowUtc = DateTime.now().toUtc();
      final futureServerTime = nowUtc.add(const Duration(hours: 2));
      final headers = {
        'x-server-time': futureServerTime.toIso8601String(),
      };

      ServerTimeService.updateClockSkewFromHeaders(headers);

      expect(ServerTimeService.isSynchronized, isTrue);
      expect(ServerTimeService.clockSkew.inMinutes, closeTo(120, 1));

      final synced = ServerTimeService.nowUtc();
      expect(synced.difference(futureServerTime).abs().inSeconds, lessThan(2));
    });

    test('handles past server time when device clock is ahead', () {
      final nowUtc = DateTime.now().toUtc();
      final pastServerTime = nowUtc.subtract(const Duration(days: 1));
      final headers = {
        'x-server-time': pastServerTime.toIso8601String(),
      };

      ServerTimeService.updateClockSkewFromHeaders(headers);

      expect(ServerTimeService.isSynchronized, isTrue);
      expect(ServerTimeService.clockSkew.inHours, closeTo(-24, 1));
    });
  });
}
