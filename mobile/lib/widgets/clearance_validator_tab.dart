import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';
import '../models/document_request_model.dart';

class ClearanceValidatorTab extends StatelessWidget {
  final TextEditingController trackingIdController;
  final bool isVerifying;
  final String? verificationError;
  final DocumentRequestModel? verifiedClearance;
  final VoidCallback onVerify;

  const ClearanceValidatorTab({
    super.key,
    required this.trackingIdController,
    required this.isVerifying,
    required this.verificationError,
    required this.verifiedClearance,
    required this.onVerify,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Clearance & Receipt Validator',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w900,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Enter a document tracking ID or the official receipt number recorded by your Barangay.',
            style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: trackingIdController,
                  decoration: InputDecoration(
                    hintText: 'e.g. REQ-12 or OR-2026-0099',
                    filled: true,
                    fillColor: Colors.white,
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 14,
                    ),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: const BorderSide(color: Color(0xFFCBD5E1)),
                    ),
                  ),
                  keyboardType: TextInputType.text,
                  onSubmitted: (_) => onVerify(),
                ),
              ),
              const SizedBox(width: 12),
              ElevatedButton(
                onPressed: isVerifying ? null : onVerify,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primaryNavy,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 15,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
                child: isVerifying
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Text(
                        'Verify',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          if (verificationError != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFFFCA5A5)),
              ),
              child: Text(
                verificationError!,
                style: const TextStyle(
                  color: Color(0xFFDC2626),
                  fontWeight: FontWeight.w600,
                  fontSize: 13.5,
                ),
              ),
            ),
          if (verifiedClearance != null)
            ClearanceResultCard(request: verifiedClearance!),
        ],
      ),
    );
  }
}

class ClearanceResultCard extends StatelessWidget {
  final DocumentRequestModel request;

  const ClearanceResultCard({super.key, required this.request});

  @override
  Widget build(BuildContext context) {
    final isValid = request.isReadyForPickup || request.isReleased;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isValid ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 5,
                ),
                decoration: BoxDecoration(
                  color: isValid
                      ? const Color(0xFFECFDF5)
                      : const Color(0xFFFFFBEB),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      isValid
                          ? Icons.verified_rounded
                          : Icons.pending_actions_rounded,
                      size: 16,
                      color: isValid
                          ? const Color(0xFF059669)
                          : const Color(0xFFD97706),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      isValid ? 'VALID IN SYSTEM' : 'PENDING APPROVAL',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        color: isValid
                            ? const Color(0xFF059669)
                            : const Color(0xFFD97706),
                      ),
                    ),
                  ],
                ),
              ),
              Text(
                request.formattedTrackingId,
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF64748B),
                  fontSize: 12,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            request.documentType,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w900,
              color: AppColors.primaryNavy,
            ),
          ),
          if (request.purpose != null && request.purpose!.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              'Purpose: ${request.purpose}',
              style: const TextStyle(
                fontSize: 13.5,
                fontWeight: FontWeight.w600,
                color: Color(0xFF334155),
              ),
            ),
          ],
          const SizedBox(height: 8),
          Text(
            'Status: ${request.statusDisplay}',
            style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
          ),
          Text(
            'Requested Date: ${request.formattedRequestedDate}',
            style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
          ),
          if (request.orNumber != null && request.orNumber!.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              'Official Receipt: ${request.orNumber}',
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: Color(0xFF0F766E),
              ),
            ),
          ],
          if (request.formattedFee != null) ...[
            const SizedBox(height: 4),
            Text(
              'Treasury Fee: ${request.formattedFee}',
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: Color(0xFF334155),
              ),
            ),
          ],
          if (request.isWalkin) ...[
            const SizedBox(height: 4),
            const Text(
              'Origin: Front Desk Walk-In',
              style: TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w500,
                color: Color(0xFF64748B),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
