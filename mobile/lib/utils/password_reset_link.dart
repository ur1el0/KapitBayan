class PasswordResetLink {
  const PasswordResetLink({required this.uidb64, required this.token});

  final String uidb64;
  final String token;

  static PasswordResetLink? parse(String value) {
    final uri = Uri.tryParse(value.trim());
    if (uri == null ||
        !uri.hasAuthority ||
        !{'http', 'https'}.contains(uri.scheme.toLowerCase()) ||
        uri.host.isEmpty ||
        uri.path != '/reset-password') {
      return null;
    }

    final uidValues = uri.queryParametersAll['uidb64'];
    final tokenValues = uri.queryParametersAll['token'];
    if (uidValues?.length != 1 || tokenValues?.length != 1) return null;

    final uidb64 = uidValues!.single.trim();
    final token = tokenValues!.single.trim();
    if (uidb64.isEmpty || token.isEmpty) return null;

    return PasswordResetLink(uidb64: uidb64, token: token);
  }
}
