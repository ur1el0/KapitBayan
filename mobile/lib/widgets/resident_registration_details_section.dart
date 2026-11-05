import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../core/theme/app_colors.dart';
import '../core/localization/app_language.dart';
import '../models/barangay_model.dart';
import 'custom_text_field.dart';
import 'barangay_select_field.dart';
import 'photo_upload_card.dart';

class ResidentRegistrationDetailsSection extends StatelessWidget {
  final TextEditingController fullNameController;
  final TextEditingController usernameController;
  final TextEditingController emailController;
  final TextEditingController passwordController;
  final TextEditingController confirmPasswordController;
  final TextEditingController contactNumberController;
  final TextEditingController purokController;
  final TextEditingController addressDetailsController;
  final TextEditingController guardianController;
  final List<BarangayModel> barangays;
  final int? selectedBarangayId;
  final bool isLoadingBarangays;
  final String? barangayLoadError;
  final bool obscurePassword;
  final bool obscureConfirmPassword;
  final DateTime? birthDate;
  final bool requiresGuardian;
  final String guardianRelationship;
  final XFile? guardianshipEvidence;
  final bool voterStatus;
  final bool isLoading;
  final ValueChanged<int?> onBarangayChanged;
  final VoidCallback onTogglePasswordVisibility;
  final VoidCallback onToggleConfirmPasswordVisibility;
  final VoidCallback onSelectBirthDate;
  final ValueChanged<bool> onVoterStatusChanged;
  final ValueChanged<String> onGuardianRelationshipChanged;
  final VoidCallback onPickGuardianshipEvidence;
  final VoidCallback onRemoveGuardianshipEvidence;
  final VoidCallback onSubmit;

  const ResidentRegistrationDetailsSection({
    super.key,
    required this.fullNameController,
    required this.usernameController,
    required this.emailController,
    required this.passwordController,
    required this.confirmPasswordController,
    required this.contactNumberController,
    required this.purokController,
    required this.addressDetailsController,
    required this.guardianController,
    required this.barangays,
    required this.selectedBarangayId,
    required this.isLoadingBarangays,
    required this.barangayLoadError,
    required this.obscurePassword,
    required this.obscureConfirmPassword,
    required this.birthDate,
    required this.requiresGuardian,
    required this.guardianRelationship,
    required this.guardianshipEvidence,
    required this.voterStatus,
    required this.isLoading,
    required this.onBarangayChanged,
    required this.onTogglePasswordVisibility,
    required this.onToggleConfirmPasswordVisibility,
    required this.onSelectBirthDate,
    required this.onVoterStatusChanged,
    required this.onGuardianRelationshipChanged,
    required this.onPickGuardianshipEvidence,
    required this.onRemoveGuardianshipEvidence,
    required this.onSubmit,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        // Full Name Input
        CustomTextField(
          label: context.tr('FULL NAME'),
          controller: fullNameController,
          hintText: 'Johnathan Doe',
          prefixIcon: Icons.person_outline_rounded,
          textInputAction: TextInputAction.next,
          enabled: !isLoading,
          validator: (value) {
            if (value == null || value.trim().isEmpty) {
              return context.tr('Please enter your full name');
            }
            return null;
          },
        ),

        const SizedBox(height: 18),

        // Local Barangay Jurisdiction Dropdown
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.tr('LOCAL BARANGAY JURISDICTION'),
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
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  context.tr('Loading approved barangays…'),
                  style: TextStyle(color: AppColors.textMuted, fontSize: 12),
                ),
              ),
            if (!isLoadingBarangays &&
                barangays.isEmpty &&
                barangayLoadError == null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  context.tr('No registered barangays are currently available.'),
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

        const SizedBox(height: 18),
        CustomTextField(
          label: context.tr('PUROK / ZONE'),
          controller: purokController,
          hintText: 'e.g. Purok 3 or Zone 2',
          prefixIcon: Icons.place_outlined,
          textInputAction: TextInputAction.next,
          enabled: !isLoading,
          validator: (value) {
            if (value == null || value.trim().isEmpty) {
              return context.tr('Please enter your Purok or Zone');
            }
            if (value.trim().length > 100) {
              return context.tr('Purok or Zone must be 100 characters or fewer');
            }
            return null;
          },
        ),

        const SizedBox(height: 18),
        CustomTextField(
          label: context.tr('HOUSE / STREET / LANDMARK (OPTIONAL)'),
          controller: addressDetailsController,
          hintText: 'e.g. House 12, Mabini Street, near chapel',
          prefixIcon: Icons.home_outlined,
          textInputAction: TextInputAction.next,
          enabled: !isLoading,
          validator: (value) => value != null && value.trim().length > 255
              ? context.tr('Address details must be 255 characters or fewer')
              : null,
        ),

        // Barangay ID / Username Input
        CustomTextField(
          label: context.tr('BARANGAY ID / USERNAME'),
          controller: usernameController,
          hintText: 'CID-99201',
          prefixIcon: Icons.fingerprint_rounded,
          textInputAction: TextInputAction.next,
          enabled: !isLoading,
          validator: (value) {
            if (value == null || value.trim().isEmpty) {
              return context.tr('Please enter your barangay ID or username');
            }
            return null;
          },
        ),

        const SizedBox(height: 18),

        // Email Address Input
        CustomTextField(
          label: context.tr('EMAIL ADDRESS'),
          controller: emailController,
          hintText: 'name@civic.gov',
          prefixIcon: Icons.mail_outline_rounded,
          keyboardType: TextInputType.emailAddress,
          textInputAction: TextInputAction.next,
          enabled: !isLoading,
          validator: (value) {
            if (value == null || value.trim().isEmpty) {
              return context.tr('Please enter your email address');
            }
            final emailRegex = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');
            if (!emailRegex.hasMatch(value.trim())) {
              return context.tr('Please enter a valid email address');
            }
            return null;
          },
        ),

        const SizedBox(height: 18),

        // Password Input
        CustomTextField(
          label: context.tr('PASSWORD'),
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
              return context.tr('Please enter a password');
            }
            if (value.length < 8) {
              return context.tr('Password must be at least 8 characters');
            }
            return null;
          },
        ),

        const SizedBox(height: 18),

        // Confirm Password Input
        CustomTextField(
          label: context.tr('CONFIRM PASSWORD'),
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
              return context.tr('Please confirm your password');
            }
            if (value != passwordController.text) {
              return context.tr('Passwords do not match');
            }
            return null;
          },
        ),

        const SizedBox(height: 24),

        CustomTextField(
          label: context.tr('CONTACT NUMBER (OPTIONAL)'),
          controller: contactNumberController,
          hintText: '09123456789',
          prefixIcon: Icons.phone_outlined,
          keyboardType: TextInputType.phone,
          enabled: !isLoading,
        ),
        const SizedBox(height: 24),

        Text(
          context.tr('BIRTH DATE'),
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
                      : context.tr('Select your birth date'),
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
            label: context.tr("GUARDIAN'S REGISTERED ID (REQUIRED)"),
            controller: guardianController,
            hintText: 'CID-XXXXX',
            prefixIcon: Icons.supervisor_account_outlined,
            enabled: !isLoading,
          ),
          const SizedBox(height: 8),
          Text(
            context.tr('Link a verified adult resident and upload supporting proof. A Barangay Admin will review it before approval.'),
            style: TextStyle(
              fontSize: 12,
              color: Color(0xFFEF4444),
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: guardianRelationship.isEmpty ? null : guardianRelationship,
            decoration: InputDecoration(
              labelText: context.tr('Relationship to the applicant'),
              border: const OutlineInputBorder(),
              filled: true,
              fillColor: Colors.white,
            ),
            items: [
              DropdownMenuItem(value: 'PARENT', child: Text(context.tr('Parent'))),
              DropdownMenuItem(value: 'COURT_APPOINTED', child: Text(context.tr('Court-appointed guardian'))),
              DropdownMenuItem(value: 'OTHER_AUTHORIZED', child: Text(context.tr('Other authorized guardian'))),
            ],
            onChanged: isLoading
                ? null
                : (value) {
                    if (value != null) onGuardianRelationshipChanged(value);
                  },
          ),
          const SizedBox(height: 12),
          PhotoUploadCard(
            title: context.tr('Upload guardianship supporting document'),
            selectedFile: guardianshipEvidence,
            onPick: onPickGuardianshipEvidence,
            onRemove: onRemoveGuardianshipEvidence,
            enabled: !isLoading,
          ),
          const SizedBox(height: 6),
          Text(
            context.tr('Examples: a birth certificate for a parent or an official guardianship document. This supports human review; the system does not determine legal guardianship.'),
            style: const TextStyle(fontSize: 11, color: Color(0xFF92400E)),
          ),
        ],

        const SizedBox(height: 16),
        SwitchListTile(
          title: Text(
            context.tr('Registered Voter in this Barangay'),
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
