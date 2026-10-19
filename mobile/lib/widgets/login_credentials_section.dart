import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';
import 'custom_button.dart';
import 'custom_text_field.dart';

class LoginCredentialsSection extends StatelessWidget {
  final TextEditingController usernameController;
  final TextEditingController passwordController;
  final bool isOfficialMode;
  final bool isLoading;
  final bool obscurePassword;
  final VoidCallback onTogglePasswordVisibility;
  final VoidCallback onForgotPassword;
  final VoidCallback onSubmit;

  const LoginCredentialsSection({
    super.key,
    required this.usernameController,
    required this.passwordController,
    required this.isOfficialMode,
    required this.isLoading,
    required this.obscurePassword,
    required this.onTogglePasswordVisibility,
    required this.onForgotPassword,
    required this.onSubmit,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CustomTextField(
          label: isOfficialMode ? 'Official Email' : 'Citizen ID / Username',
          controller: usernameController,
          hintText: isOfficialMode ? 'name@barangay.gov.ph' : 'resident',
          prefixIcon: Icons.person_outline_rounded,
          keyboardType: isOfficialMode ? TextInputType.emailAddress : TextInputType.text,
          textInputAction: TextInputAction.next,
          enabled: !isLoading,
          validator: (value) {
            if (value == null || value.trim().isEmpty) {
              return isOfficialMode
                  ? 'Please enter your official email address'
                  : 'Please enter your citizen ID or username';
            }
            return null;
          },
        ),
        const SizedBox(height: 20),
        CustomTextField(
          label: 'Password',
          controller: passwordController,
          hintText: '••••••••',
          prefixIcon: Icons.lock_outline_rounded,
          obscureText: obscurePassword,
          textInputAction: TextInputAction.done,
          enabled: !isLoading,
          onFieldSubmitted: (_) => onSubmit(),
          suffixIcon: IconButton(
            tooltip: obscurePassword ? 'Show password' : 'Hide password',
            icon: Icon(
              obscurePassword
                  ? Icons.visibility_outlined
                  : Icons.visibility_off_outlined,
              color: AppColors.textMuted,
              size: 20,
            ),
            onPressed: onTogglePasswordVisibility,
          ),
          validator: (value) {
            if (value == null || value.isEmpty) {
              return 'Please enter your password';
            }
            return null;
          },
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: onForgotPassword,
            child: const Text(
              'Forgot Password?',
              style: TextStyle(
                fontSize: 13.5,
                fontWeight: FontWeight.w700,
                color: AppColors.primaryNavy,
              ),
            ),
          ),
        ),
        const SizedBox(height: 28),
        CustomButton(
          text: isOfficialMode
              ? 'Authenticate Official'
              : 'Sign In to Citizen Portal',
          isLoading: isLoading,
          icon: Icons.arrow_forward_rounded,
          onPressed: onSubmit,
        ),
      ],
    );
  }
}
