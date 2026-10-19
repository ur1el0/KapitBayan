import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/network/api_client.dart';
import '../core/theme/app_colors.dart';
import '../services/auth_service.dart';
import '../services/storage_service.dart';
import '../utils/password_reset_link.dart';
import '../widgets/custom_text_field.dart';

class ForgotPasswordScreen extends StatefulWidget {
  final AuthService? authService;

  const ForgotPasswordScreen({super.key, this.authService});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _resetLinkController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  AuthService? _authService;
  bool _requestSent = false;
  bool _completed = false;
  bool _isSubmitting = false;
  bool _obscurePassword = true;
  bool _obscureConfirmation = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _authService = widget.authService;
  }

  @override
  void dispose() {
    _emailController.dispose();
    _resetLinkController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<AuthService> _getAuthService() async {
    final existingService = _authService;
    if (existingService != null) return existingService;

    final storage = await StorageService.init();
    final service = AuthService(
      apiClient: ApiClient(),
      storageService: storage,
    );
    _authService = service;
    return service;
  }

  Future<void> _submit() async {
    if (_isSubmitting) return;
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final service = await _getAuthService();
      if (!mounted) return;

      if (_requestSent) {
        final resetLink = PasswordResetLink.parse(_resetLinkController.text);
        if (resetLink == null) return;

        await service.confirmPasswordReset(
          newPassword: _passwordController.text,
          uidb64: resetLink.uidb64,
          token: resetLink.token,
        );
        if (!mounted) return;
        setState(() {
          _completed = true;
          _resetLinkController.clear();
          _passwordController.clear();
          _confirmPasswordController.clear();
        });
      } else {
        await service.requestPasswordReset(_emailController.text);
        if (!mounted) return;
        setState(() => _requestSent = true);
      }
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _errorMessage = error
            .toString()
            .replaceFirst(RegExp(r'^(Exception|ApiException):\s*'), '')
            .trim();
      });
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Password Recovery'),
        backgroundColor: Colors.white,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: _completed ? _buildCompletion() : _buildForm(),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildForm() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            _requestSent ? 'Set a new password' : 'Recover your account',
            style: const TextStyle(
              color: AppColors.textPrimary,
              fontSize: 24,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _requestSent
                ? 'If the address is registered, a reset link was sent. Open it in your browser, or copy the complete link and paste it below to finish in this app.'
                : 'Enter the email address associated with your account. We will send reset instructions if it is registered.',
            style: const TextStyle(color: AppColors.textSecondary, height: 1.5),
          ),
          if (_errorMessage != null) ...[
            const SizedBox(height: 16),
            Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
          ],
          const SizedBox(height: 24),
          if (!_requestSent) ...[
            CustomTextField(
              label: 'Registered email',
              controller: _emailController,
              hintText: 'resident@example.com',
              prefixIcon: Icons.email_outlined,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.done,
              validator: (value) {
                final email = value?.trim() ?? '';
                if (email.isEmpty) return 'Enter your email address.';
                if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email)) {
                  return 'Enter a valid email address.';
                }
                return null;
              },
            ),
          ] else ...[
            CustomTextField(
              label: 'Reset link from email',
              controller: _resetLinkController,
              hintText: 'Paste the complete password reset link',
              prefixIcon: Icons.link_outlined,
              keyboardType: TextInputType.url,
              validator: (value) => PasswordResetLink.parse(value ?? '') != null
                  ? null
                  : 'Paste the complete, valid reset link from your email.',
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: _isSubmitting ? null : _pasteResetLink,
                icon: const Icon(Icons.content_paste_outlined),
                label: const Text('Paste reset link'),
              ),
            ),
            const SizedBox(height: 16),
            CustomTextField(
              label: 'New password',
              controller: _passwordController,
              hintText: 'At least 8 characters',
              prefixIcon: Icons.lock_outline,
              obscureText: _obscurePassword,
              suffixIcon: IconButton(
                onPressed: () {
                  setState(() => _obscurePassword = !_obscurePassword);
                },
                icon: Icon(
                  _obscurePassword ? Icons.visibility : Icons.visibility_off,
                ),
              ),
              validator: (value) => (value ?? '').length >= 8
                  ? null
                  : 'Use at least 8 characters.',
            ),
            const SizedBox(height: 16),
            CustomTextField(
              label: 'Confirm new password',
              controller: _confirmPasswordController,
              hintText: 'Re-enter the new password',
              prefixIcon: Icons.lock_outline,
              obscureText: _obscureConfirmation,
              suffixIcon: IconButton(
                onPressed: () {
                  setState(() => _obscureConfirmation = !_obscureConfirmation);
                },
                icon: Icon(
                  _obscureConfirmation
                      ? Icons.visibility
                      : Icons.visibility_off,
                ),
              ),
              validator: (value) => value == _passwordController.text
                  ? null
                  : 'Passwords do not match.',
            ),
          ],
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _isSubmitting ? null : _submit,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primaryNavy,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: _isSubmitting
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : Text(_requestSent ? 'Reset Password' : 'Send Reset Link'),
          ),
          if (_requestSent) ...[
            const SizedBox(height: 8),
            TextButton(
              onPressed: _isSubmitting
                  ? null
                  : () {
                      setState(() {
                        _requestSent = false;
                        _errorMessage = null;
                        _resetLinkController.clear();
                        _passwordController.clear();
                        _confirmPasswordController.clear();
                      });
                    },
              child: const Text('Use a different email'),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _pasteResetLink() async {
    final clipboardData = await Clipboard.getData(Clipboard.kTextPlain);
    if (!mounted) return;

    final copiedLink = clipboardData?.text?.trim();
    if (copiedLink == null || copiedLink.isEmpty) {
      setState(
        () => _errorMessage = 'Copy the reset link from your email first.',
      );
      return;
    }

    setState(() {
      _resetLinkController.text = copiedLink;
      _errorMessage = null;
    });
  }

  Widget _buildCompletion() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Icon(
          Icons.check_circle_outline,
          color: Color(0xFF10B981),
          size: 56,
        ),
        const SizedBox(height: 16),
        const Text(
          'Password updated',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 24,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'You can now return to the login screen and sign in with your new password.',
          textAlign: TextAlign.center,
          style: TextStyle(color: AppColors.textSecondary, height: 1.5),
        ),
        const SizedBox(height: 24),
        ElevatedButton(
          onPressed: () => Navigator.of(context).pop(),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primaryNavy,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
          child: const Text('Return to Login'),
        ),
      ],
    );
  }
}
