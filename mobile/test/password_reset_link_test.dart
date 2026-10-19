import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/utils/password_reset_link.dart';

void main() {
  group('PasswordResetLink.parse', () {
    test('extracts both credentials from the emailed reset URL', () {
      final link = PasswordResetLink.parse(
        'https://kapitbayan-ph.vercel.app/reset-password'
        '?uidb64=MzY&token=abc-123_def',
      );

      expect(link?.uidb64, 'MzY');
      expect(link?.token, 'abc-123_def');
    });

    test('rejects URLs without both unique reset credentials', () {
      expect(
        PasswordResetLink.parse(
          'https://kapitbayan-ph.vercel.app/reset-password?uidb64=MzY',
        ),
        isNull,
      );
      expect(
        PasswordResetLink.parse(
          'https://kapitbayan-ph.vercel.app/reset-password'
          '?uidb64=MzY&token=first&token=second',
        ),
        isNull,
      );
    });

    test('rejects unrelated routes and malformed URLs', () {
      expect(
        PasswordResetLink.parse(
          'https://kapitbayan-ph.vercel.app/forgot-password'
          '?uidb64=MzY&token=abc',
        ),
        isNull,
      );
      expect(PasswordResetLink.parse('not a URL'), isNull);
    });
  });
}
