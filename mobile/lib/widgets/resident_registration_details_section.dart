import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';
import '../models/barangay_model.dart';
import 'custom_text_field.dart';
import 'barangay_select_field.dart';

class ResidentRegistrationDetailsSection extends StatelessWidget {
  final TextEditingController fullNameController;
  final TextEditingController usernameController;
  final TextEditingController emailController;
  final TextEditingController passwordController;
  final TextEditingController confirmPasswordController;
  final TextEditingController contactNumberController;
  final TextEditingController guardianController;
  final List<BarangayModel> barangays;
  final int? selectedBarangayId;
  final bool isLoadingBarangays;
  final String? barangayLoadError;
  final bool obscurePassword;
  final bool obscureConfirmPassword;
  final DateTime? birthDate;
  final bool requiresGuardian;
  final bool voterStatus;
  final bool isLoading;
  final ValueChanged<int?> onBarangayChanged;
  final VoidCallback onTogglePasswordVisibility;
  final VoidCallback onToggleConfirmPasswordVisibility;
  final VoidCallback onSelectBirthDate;
  final ValueChanged<bool> onVoterStatusChanged;
  final VoidCallback onSubmit;

  const ResidentRegistrationDetailsSection({
    super.key,
    required this.fullNameController,
    required this.usernameController,
    required this.emailController,
    required this.passwordController,
    required this.confirmPasswordController,
    required this.contactNumberController,
    required this.guardianController,
    required this.barangays,
    required this.selectedBarangayId,
    required this.isLoadingBarangays,
    required this.barangayLoadError,
    required this.obscurePassword,
    required this.obscureConfirmPassword,
    required this.birthDate,
    required this.requiresGuardian,
    required this.voterStatus,
    required this.isLoading,
    required this.onBarangayChanged,
    required this.onTogglePasswordVisibility,
    required this.onToggleConfirmPasswordVisibility,
    required this.onSelectBirthDate,
    required this.onVoterStatusChanged,
    required this.onSubmit,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        // Full Name Input
        CustomTextField(
          label: 'FULL NAME',
          controller: fullNameController,
          hintText: 'Johnathan Doe',
          prefixIcon: Icons.person_outline_rounded,
          textInputAction: TextInputAction.next,
          enabled: !isLoading,
          validator: (value) {
            if (value == null || value.trim().isEmpty) {
              return 'Please enter your full name';
            }
            return null;
          },
        ),

        const SizedBox(height: 18),

        // Local Barangay Jurisdiction Dropdown
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'LOCAL BARANGAY JURISDICTION',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppColors.textLabel,
                letterSpacing: 0.8,
              ),
            ),
            const SizedBox(height: 8),
            Container(
              decoration: BoxDecoration(
                color: AppColors.inputBackground,
                borderRadius: BorderRadius.circular(12),
              ),
              child: BarangaySelectField(
                barangays: barangays,
                selectedId: selectedBarangayId,
                enabled:
                    !isLoading && !isLoadingBarangays && barangays.isNotEmpty,
                onChanged: onBarangayChanged,
              ),
            ),
            if (isLoadingBarangays)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  'Loading approved barangays…',
                  style: TextStyle(color: AppColors.textMuted, fontSize: 12),
                ),
              ),
            if (!isLoadingBarangays && barangays.isEmpty && barangayLoadError == null)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  'No registered barangays are currently available.',
                  style: TextStyle(color: AppColors.textMuted, fontSize: 12),
                ),
              ),
            if (barangayLoadError != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  barangayLoadError!,
                  style: const TextStyle(color: Colors.red, fontSize: 12),
                ),
              ),
          ],
        ),

        // Barangay ID / Username Input
        CustomTextField(
          label: 'BARANGAY ID / USERNAME',
          controller: usernameController,
          hintText: 'CID-99201',
          prefixIcon: Icons.fingerprint_rounded,
          textInputAction: TextInputAction.next,
          enabled: !isLoading,
          validator: (value) {
            if (value == null || value.trim().isEmpty) {
              return 'Please enter your barangay ID or username';
            }
            return null;
          },
        ),

        const SizedBox(height: 18),

        // Email Address Input
        CustomTextField(
          label: 'EMAIL ADDRESS',
          controller: emailController,
          hintText: 'name@civic.gov',
          prefixIcon: Icons.mail_outline_rounded,
          keyboardType: TextInputType.emailAddress,
          textInputAction: TextInputAction.next,
          enabled: !isLoading,
          validator: (value) {
            if (value == null || value.trim().isEmpty) {
              return 'Please enter your email address';
            }
            final emailRegex = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');
            if (!emailRegex.hasMatch(value.trim())) {
              return 'Please enter a valid email address';
            }
            return null;
          },
        ),

        const SizedBox(height: 18),

        // Password Input
        CustomTextField(
          label: 'PASSWORD',
          controller: passwordController,
          hintText: '••••••••',
          prefixIcon: Icons.lock_outline_rounded,
          obscureText: obscurePassword,
          textInputAction: TextInputAction.next,
          enabled: !isLoading,
          suffixIcon: IconButton(
            icon: Icon(
              obscurePassword
                  ? Icons.visibility_outlined
                  : Icons.visibility_off_outlined,
              color: AppColors.textMuted,
              size: 20,
            ),
            onPressed: () {
              onTogglePasswordVisibility();
            },
          ),
          validator: (value) {
            if (value == null || value.isEmpty) {
              return 'Please enter a password';
            }
            if (value.length < 8) {
              return 'Password must be at least 8 characters';
            }
            return null;
          },
        ),

        const SizedBox(height: 18),

        // Confirm Password Input
        CustomTextField(
          label: 'CONFIRM PASSWORD',
          controller: confirmPasswordController,
          hintText: '••••••••',
          prefixIcon: Icons.shield_outlined,
          obscureText: obscureConfirmPassword,
          textInputAction: TextInputAction.done,
          enabled: !isLoading,
          onFieldSubmitted: (_) => onSubmit(),
          suffixIcon: IconButton(
            icon: Icon(
              obscureConfirmPassword
                  ? Icons.visibility_outlined
                  : Icons.visibility_off_outlined,
              color: AppColors.textMuted,
              size: 20,
            ),
            onPressed: () {
              onToggleConfirmPasswordVisibility();
            },
          ),
          validator: (value) {
            if (value == null || value.isEmpty) {
              return 'Please confirm your password';
            }
            if (value != passwordController.text) {
              return 'Passwords do not match';
            }
            return null;
          },
        ),

        const SizedBox(height: 24),

        CustomTextField(
          label: 'CONTACT NUMBER (OPTIONAL)',
          controller: contactNumberController,
          hintText: '09123456789',
          prefixIcon: Icons.phone_outlined,
          keyboardType: TextInputType.phone,
          enabled: !isLoading,
        ),
        const SizedBox(height: 24),

        const Text(
          'BIRTH DATE',
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w800,
            color: Color(0xFF64748B),
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 8),
        InkWell(
          onTap: isLoading ? null : () => onSelectBirthDate(),
          borderRadius: BorderRadius.circular(16),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFE2E8F0), width: 1.2),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.calendar_today_rounded,
                  color: Color(0xFF94A3B8),
                  size: 20,
                ),
                const SizedBox(width: 12),
                Text(
                  birthDate != null
                      ? "${birthDate!.year}-${birthDate!.month.toString().padLeft(2, '0')}-${birthDate!.day.toString().padLeft(2, '0')}"
                      : "Select your birth date",
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: birthDate != null
                        ? AppColors.textPrimary
                        : const Color(0xFF94A3B8),
                  ),
                ),
              ],
            ),
          ),
        ),

        if (requiresGuardian) ...[
          const SizedBox(height: 24),
          CustomTextField(
            label: "GUARDIAN'S REGISTERED ID (REQUIRED)",
            controller: guardianController,
            hintText: 'CID-XXXXX',
            prefixIcon: Icons.supervisor_account_outlined,
            enabled: !isLoading,
          ),
          const SizedBox(height: 8),
          const Text(
            'Residents under 18 must be registered under a verified parent or guardian.',
            style: TextStyle(
              fontSize: 12,
              color: Color(0xFFEF4444),
              fontWeight: FontWeight.w600,
            ),
          ),
        ],

        const SizedBox(height: 16),
        SwitchListTile(
          title: const Text(
            'Registered Voter in this Barangay',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          value: voterStatus,
          activeThumbColor: AppColors.primaryNavy,
          contentPadding: EdgeInsets.zero,
          onChanged: isLoading
              ? null
              : (bool value) {
                  onVoterStatusChanged(value);
                },
        ),
        const SizedBox(height: 20),
      ],
    );
  }
}
