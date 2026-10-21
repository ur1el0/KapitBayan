import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../core/theme/app_colors.dart';
import '../core/localization/app_language.dart';
import 'custom_text_field.dart';
import 'photo_upload_card.dart';

class ResidentIdentityVerificationSection extends StatelessWidget {
  final TextEditingController philsysIdController;
  final XFile? philsysPhoto;
  final XFile? utilityBillingPhoto;
  final XFile? secondaryIdPhoto;
  final String utilityBillingType;
  final String secondaryIdType;
  final List<String> billingTypes;
  final List<String> secondaryIdTypes;
  final bool dataPrivacyConsent;
  final bool isLoading;
  final VoidCallback onPickPhilsysPhoto;
  final VoidCallback onPickUtilityBillingPhoto;
  final VoidCallback onPickSecondaryIdPhoto;
  final VoidCallback onRemovePhilsysPhoto;
  final VoidCallback onRemoveUtilityBillingPhoto;
  final VoidCallback onRemoveSecondaryIdPhoto;
  final ValueChanged<String> onUtilityBillingTypeChanged;
  final ValueChanged<String> onSecondaryIdTypeChanged;
  final ValueChanged<bool?> onPrivacyConsentChanged;

  const ResidentIdentityVerificationSection({
    super.key,
    required this.philsysIdController,
    required this.philsysPhoto,
    required this.utilityBillingPhoto,
    required this.secondaryIdPhoto,
    required this.utilityBillingType,
    required this.secondaryIdType,
    required this.billingTypes,
    required this.secondaryIdTypes,
    required this.dataPrivacyConsent,
    required this.isLoading,
    required this.onPickPhilsysPhoto,
    required this.onPickUtilityBillingPhoto,
    required this.onPickSecondaryIdPhoto,
    required this.onRemovePhilsysPhoto,
    required this.onRemoveUtilityBillingPhoto,
    required this.onRemoveSecondaryIdPhoto,
    required this.onUtilityBillingTypeChanged,
    required this.onSecondaryIdTypeChanged,
    required this.onPrivacyConsentChanged,
  });

  @override
  Widget build(BuildContext context) {
    final hasUploadedProof =
        philsysPhoto != null ||
        utilityBillingPhoto != null ||
        secondaryIdPhoto != null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        // Section Divider & Collapsible Container: Identity & Residency Verification Proofs
        Material(
          color: const Color(0xFFF1F5F9),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: const BorderSide(color: Color(0xFFE2E8F0)),
          ),
          clipBehavior: Clip.antiAlias,
          child: Theme(
            data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
            child: ExpansionTile(
              leading: const Icon(
                Icons.badge_outlined,
                color: AppColors.primaryNavy,
                size: 22,
              ),
              title: Text(
                context.tr('IDENTITY & RESIDENCY VERIFICATION'),
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                  letterSpacing: 0.5,
                ),
              ),
              subtitle: Text(
                hasUploadedProof
                    ? context.tr('Document attached (Tap to view/edit)')
                    : context.tr('Required: upload at least one ID or proof of residency'),
                style: TextStyle(
                  fontSize: 11,
                  color: hasUploadedProof
                      ? const Color(0xFF10B981)
                      : AppColors.textSecondary,
                  fontWeight: hasUploadedProof
                      ? FontWeight.w700
                      : FontWeight.w400,
                ),
              ),
              childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              children: [
                Text(
                  context.tr('Upload at least one image to register: a PhilSys ID, a secondary valid ID, or proof of residency such as a utility bill or lease. A typed ID number alone does not count.'),
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: 16),

                // 1. PhilSys ID Number
                CustomTextField(
                  label: context.tr('PHILSYS NATIONAL ID NUMBER'),
                  controller: philsysIdController,
                  hintText: 'e.g. 1234-5678-9012-3456',
                  prefixIcon: Icons.fingerprint_rounded,
                  enabled: !isLoading,
                ),
                const SizedBox(height: 12),

                // PhilSys ID Photo Upload
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    context.tr('PHILSYS ID CARD PHOTO'),
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textLabel,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                PhotoUploadCard(
                  title: context.tr('Upload PhilSys ID Photo'),
                  selectedFile: philsysPhoto,
                  onPick: onPickPhilsysPhoto,
                  onRemove: onRemovePhilsysPhoto,
                  enabled: !isLoading,
                ),

                const SizedBox(height: 18),

                // 2. Utility Proof of Residency
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    context.tr('BILLING STATEMENT TYPE'),
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textLabel,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: DropdownButtonFormField<String>(
                    initialValue: utilityBillingType,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      border: InputBorder.none,
                      contentPadding: EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 12,
                      ),
                      prefixIcon: Icon(
                        Icons.receipt_long_outlined,
                        color: AppColors.textMuted,
                        size: 20,
                      ),
                    ),
                    items: billingTypes
                        .map(
                          (type) => DropdownMenuItem(
                            value: type,
                            child: Text(
                              context.tr(type),
                              style: const TextStyle(
                                fontSize: 14,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ),
                        )
                        .toList(),
                    onChanged: isLoading
                        ? null
                        : (val) {
                            if (val != null) {
                              onUtilityBillingTypeChanged(val);
                            }
                          },
                  ),
                ),
                const SizedBox(height: 12),

                // Utility Billing Photo Upload
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    context.tr('UPLOAD BILLING RECEIPT'),
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textLabel,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                PhotoUploadCard(
                  title: context.tr('Upload Billing Receipt Photo'),
                  selectedFile: utilityBillingPhoto,
                  onPick: onPickUtilityBillingPhoto,
                  onRemove: onRemoveUtilityBillingPhoto,
                  enabled: !isLoading,
                ),

                const SizedBox(height: 18),

                // 3. Optional Secondary Valid ID
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    context.tr('SECONDARY VALID ID (OPTIONAL)'),
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textLabel,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: DropdownButtonFormField<String>(
                    initialValue: secondaryIdType,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      border: InputBorder.none,
                      contentPadding: EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 12,
                      ),
                      prefixIcon: Icon(
                        Icons.credit_card_outlined,
                        color: AppColors.textMuted,
                        size: 20,
                      ),
                    ),
                    items: secondaryIdTypes
                        .map(
                          (type) => DropdownMenuItem(
                            value: type,
                            child: Text(
                              type.isEmpty ? context.tr('None / Not Applicable') : context.tr(type),
                              style: const TextStyle(
                                fontSize: 14,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ),
                        )
                        .toList(),
                    onChanged: isLoading
                        ? null
                        : (val) {
                            if (val != null) {
                              onSecondaryIdTypeChanged(val);
                            }
                          },
                  ),
                ),
                if (secondaryIdType.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      context.tr('UPLOAD SECONDARY ID'),
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textLabel,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  PhotoUploadCard(
                    title: context.tr('Upload Secondary ID Photo'),
                    selectedFile: secondaryIdPhoto,
                    onPick: onPickSecondaryIdPhoto,
                    onRemove: onRemoveSecondaryIdPhoto,
                    enabled: !isLoading,
                  ),
                ],
              ],
            ),
          ),
        ),

        const SizedBox(height: 16),

        // RA 10173 Data Privacy Act Consent Checkbox
        CheckboxListTile(
          value: dataPrivacyConsent,
          activeColor: AppColors.primaryNavy,
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          title: Text(
            context.tr('I consent to provide my personal data as a resident for barangay verification, in accordance with the RA 10173 Data Privacy Act.'),
            style: TextStyle(
              fontSize: 12,
              color: AppColors.textSecondary,
              height: 1.35,
            ),
          ),
          onChanged: isLoading
              ? null
              : (bool? value) {
                  onPrivacyConsentChanged(value);
                },
        ),
        const SizedBox(height: 24),
      ],
    );
  }
}
