import 'package:flutter/material.dart';

import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';
import '../models/document_request_model.dart';

class DocumentRequestSummary extends StatelessWidget {
  final DocumentRequestModel request;
  final String paymentStatus;
  final String? paymentReviewNote;

  const DocumentRequestSummary({
    super.key,
    required this.request,
    required this.paymentStatus,
    required this.paymentReviewNote,
  });

  @override
  Widget build(BuildContext context) {
    final req = request;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Details List
        _DetailRow(
          label: context.tr('Current Status'),
          value: req.statusDisplay,
          valueColor: req.statusBadgeTextColor,
        ),
        const SizedBox(height: 12),
        _DetailRow(
          label: context.tr('Urgency Priority'),
          value: req.urgencyTag.toUpperCase() == 'URGENT'
              ? 'Urgent / Priority'
              : 'Regular',
        ),
        const SizedBox(height: 12),
        _DetailRow(
          label: context.tr('Submission Date'),
          value: req.formattedRequestedDate,
        ),

        if (req.hasRequirementsOrOffering) ...[
          const SizedBox(height: 12),
          _DetailRow(
            label: context.tr('Published fee'),
            value: req.effectivePublishedFee == null
                ? context.tr('Confirm with Barangay staff')
                : req.effectivePublishedFee == 0
                ? context.tr('No fee')
                : '₱${req.effectivePublishedFee!.toStringAsFixed(2)}',
          ),
          const SizedBox(height: 8),
          Text(
            context.tr('Requirements'),
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: AppColors.textLabel,
            ),
          ),
          const SizedBox(height: 4),
          if (req.effectiveRequirements.isEmpty)
            Text(
              context.tr('No requirements were listed.'),
              style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
            )
          else
            ...req.effectiveRequirements.map(
              (requirement) => Padding(
                padding: const EdgeInsets.only(bottom: 3),
                child: Text(
                  '• ${context.tr(requirement)}',
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
            ),
          if (req.effectiveDetails.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              context.tr(req.effectiveDetails),
              style: const TextStyle(
                fontSize: 12,
                color: AppColors.textPrimary,
              ),
            ),
          ],
          const SizedBox(height: 4),
          Text(
            context.tr(
              'Final fees are confirmed by Barangay staff during processing.',
            ),
            style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
          ),
        ],

        if (req.orNumber != null && req.orNumber!.isNotEmpty) ...[
          const SizedBox(height: 12),
          _DetailRow(label: 'Official Receipt (O.R.)', value: req.orNumber!),
        ],
        if (req.formattedFee != null) ...[
          const SizedBox(height: 12),
          _DetailRow(
            label: 'Assessment Fee',
            value: req.formattedFee!,
            valueColor: const Color(0xFF0F766E),
          ),
        ],
        if ((req.feeAmount ?? 0) > 0) ...[
          const SizedBox(height: 12),
          _DetailRow(
            label: 'Payment status',
            value: paymentStatus.replaceAll('_', ' '),
          ),
          if (paymentReviewNote != null && paymentReviewNote!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              'Staff note: $paymentReviewNote',
              style: const TextStyle(color: Color(0xFFB91C1C), fontSize: 12),
            ),
          ],
        ],
        if (req.isWalkin) ...[
          const SizedBox(height: 12),
          const _DetailRow(
            label: 'Filing Channel',
            value: 'Barangay Hall Walk-In',
          ),
        ],

        if (req.adminNotes != null && req.adminNotes!.isNotEmpty) ...[
          const SizedBox(height: 16),
          const Text(
            'BARANGAY REMARKS / NOTES',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: AppColors.textLabel,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 6),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: Text(
              req.adminNotes!,
              style: const TextStyle(
                fontSize: 12.5,
                color: AppColors.textPrimary,
                height: 1.4,
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;

  const _DetailRow({required this.label, required this.value, this.valueColor});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 12.5,
            color: AppColors.textMuted,
            fontWeight: FontWeight.w500,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: 12.5,
            fontWeight: FontWeight.w700,
            color: valueColor ?? AppColors.textPrimary,
          ),
        ),
      ],
    );
  }
}
