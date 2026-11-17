/// Global clock synchronization service that maintains the skew between
/// the device's hardware clock and the authoritative backend server clock.
class ServerTimeService {
  static Duration _clockSkew = Duration.zero;
  static bool _hasSynced = false;

  /// Returns true if the client has received at least one server timestamp.
  static bool get isSynchronized => _hasSynced;

  /// Current estimated clock skew (`serverTime - deviceTime`).
  static Duration get clockSkew => _clockSkew;

  /// Updates the clock skew from a server response header (`X-Server-Time` or standard `Date`).
  static void updateClockSkewFromHeaders(Map<String, String> headers) {
    final serverTimeRaw = headers['x-server-time'] ?? headers['date'];
    if (serverTimeRaw == null || serverTimeRaw.isEmpty) return;

    try {
      final parsedServerTime = DateTime.parse(serverTimeRaw).toUtc();
      final deviceTimeUtc = DateTime.now().toUtc();
      _clockSkew = parsedServerTime.difference(deviceTimeUtc);
      _hasSynced = true;
    } catch (_) {
      // If parsing fails (e.g. non-ISO HTTP-date), ignore without crashing
    }
  }

  /// Returns current DateTime synchronized with the server's clock.
  static DateTime now() {
    return DateTime.now().add(_clockSkew);
  }

  /// Returns current UTC DateTime synchronized with the server's clock.
  static DateTime nowUtc() {
    return DateTime.now().toUtc().add(_clockSkew);
  }

  /// Resets synchronization state (for unit testing).
  static void resetForTesting() {
    _clockSkew = Duration.zero;
    _hasSynced = false;
  }
}
