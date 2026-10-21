import 'package:flutter/material.dart';

/// Model representing a resident's document request (e.g. Barangay Clearance, Certificate of Residency, Business Permit).
class DocumentRequestModel {
  final int id;
  final String documentType;
  final int? offeringId;
  final List<String> requirementsSnapshot;
  final double? publishedFeeAmountSnapshot;
  final String offeringDetailsSnapshot;
  final String? purpose;
  final String urgencyTag;
  final String status;
  final String? adminNotes;
  final String? orNumber;
  final double? feeAmount;
  final String? paymentMethod;
  final String? paymentReference;
  final int? paymentRecipientId;
  final String? paymentRecipientName;
  final String? paymentRecipientIdentifier;
  final String? paymentInstructions;
  final String paymentStatus;
  final String? paymentReviewNote;
  final String? paymentProofUrl;
  final DateTime? paymentTransactedAt;
  final String feeAssessmentStatus;
  final String? feeAssessedByName;
  final DateTime? feeAssessedAt;
  final String? feeWaiverReason;
  final bool isWalkin;
  final String? requesterName;
  final String? purok;
  final String? walkinName;
  final String? walkinPurok;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const DocumentRequestModel({
    required this.id,
    required this.documentType,
    this.offeringId,
    this.requirementsSnapshot = const [],
    this.publishedFeeAmountSnapshot,
    this.offeringDetailsSnapshot = '',
    this.purpose,
    this.urgencyTag = 'REGULAR',
    this.status = 'PENDING',
    this.adminNotes,
    this.orNumber,
    this.feeAmount,
    this.paymentMethod,
    this.paymentReference,
    this.paymentRecipientId,
    this.paymentRecipientName,
    this.paymentRecipientIdentifier,
    this.paymentInstructions,
    this.paymentStatus = 'NOT_REQUIRED',
    this.paymentReviewNote,
    this.paymentProofUrl,
    this.paymentTransactedAt,
    this.feeAssessmentStatus = 'AWAITING_ASSESSMENT',
    this.feeAssessedByName,
    this.feeAssessedAt,
    this.feeWaiverReason,
    this.isWalkin = false,
    this.requesterName,
    this.purok,
    this.walkinName,
    this.walkinPurok,
    this.createdAt,
    this.updatedAt,
  });

  factory DocumentRequestModel.fromJson(Map<String, dynamic> json) {
    return DocumentRequestModel(
      id: (json['request_id'] ?? json['id']) is int
          ? (json['request_id'] ?? json['id']) as int
          : int.tryParse(
                  (json['request_id'] ?? json['id'])?.toString() ?? '',
                ) ??
                0,
      documentType: json['document_type'] as String? ?? 'Document Request',
      offeringId: (json['offering_id'] as num?)?.toInt(),
      requirementsSnapshot: json['requirements_snapshot'] is List
          ? (json['requirements_snapshot'] as List)
                .map((item) => item.toString())
                .toList(growable: false)
          : const [],
      publishedFeeAmountSnapshot: json['published_fee_amount_snapshot'] is num
          ? (json['published_fee_amount_snapshot'] as num).toDouble()
          : double.tryParse(
              json['published_fee_amount_snapshot']?.toString() ?? '',
            ),
      offeringDetailsSnapshot:
          json['offering_details_snapshot'] as String? ?? '',
      purpose: json['purpose'] as String?,
      urgencyTag: json['urgency_tag'] as String? ?? 'REGULAR',
      status: json['status'] as String? ?? 'PENDING',
      adminNotes: json['admin_notes'] as String?,
      orNumber: json['or_number'] as String?,
      feeAmount: json['fee_amount'] != null
          ? (json['fee_amount'] is num
                ? (json['fee_amount'] as num).toDouble()
                : double.tryParse(json['fee_amount'].toString()))
          : null,
      paymentMethod: json['payment_method'] as String?,
      paymentReference: json['payment_reference'] as String?,
      paymentRecipientId: json['payment_recipient'] as int?,
      paymentRecipientName: json['payment_recipient_name_snapshot'] as String?,
      paymentRecipientIdentifier:
          json['payment_recipient_identifier_snapshot'] as String?,
      paymentInstructions: json['payment_instructions_snapshot'] as String?,
      paymentStatus: json['payment_status'] as String? ?? 'NOT_REQUIRED',
      paymentReviewNote: json['payment_review_note'] as String?,
      paymentProofUrl: json['payment_proof_url'] as String?,
      paymentTransactedAt: json['payment_transacted_at'] != null
          ? DateTime.tryParse(json['payment_transacted_at'].toString())
          : null,
      feeAssessmentStatus:
          json['fee_assessment_status'] as String? ?? 'AWAITING_ASSESSMENT',
      feeAssessedByName: json['fee_assessed_by_name'] as String?,
      feeAssessedAt: json['fee_assessed_at'] != null
          ? DateTime.tryParse(json['fee_assessed_at'].toString())
          : null,
      feeWaiverReason: json['fee_waiver_reason'] as String?,
      isWalkin: json['is_walkin'] as bool? ?? false,
      requesterName: json['requester_name'] as String?,
      purok: json['purok']?.toString(),
      walkinName: json['walkin_name'] as String?,
      walkinPurok: json['walkin_purok'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString())
          : null,
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'].toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'document_type': documentType,
      'offering_id': offeringId,
      'requirements_snapshot': requirementsSnapshot,
      'published_fee_amount_snapshot': publishedFeeAmountSnapshot,
      'offering_details_snapshot': offeringDetailsSnapshot,
      'urgency_tag': urgencyTag,
      'status': status,
      'admin_notes': adminNotes,
      'or_number': orNumber,
      'fee_amount': feeAmount,
      'payment_method': paymentMethod,
      'payment_reference': paymentReference,
      'payment_recipient': paymentRecipientId,
      'payment_recipient_name_snapshot': paymentRecipientName,
      'payment_recipient_identifier_snapshot': paymentRecipientIdentifier,
      'payment_instructions_snapshot': paymentInstructions,
      'payment_status': paymentStatus,
      'payment_review_note': paymentReviewNote,
      'payment_proof_url': paymentProofUrl,
      'payment_transacted_at': paymentTransactedAt?.toIso8601String(),
      'fee_assessment_status': feeAssessmentStatus,
      'fee_assessed_by_name': feeAssessedByName,
      'fee_assessed_at': feeAssessedAt?.toIso8601String(),
      'fee_waiver_reason': feeWaiverReason,
      'is_walkin': isWalkin,
      'requester_name': requesterName,
      'purok': purok,
      'walkin_name': walkinName,
      'walkin_purok': walkinPurok,
      'created_at': createdAt?.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
    };
  }

  bool get isPending => status.toUpperCase() == 'PENDING';
  bool get isProcessing => status.toUpperCase() == 'PROCESSING';
  bool get isReadyForPickup => status.toUpperCase() == 'READY_FOR_PICKUP';
  bool get isReleased => status.toUpperCase() == 'RELEASED';
  bool get isRejected => status.toUpperCase() == 'REJECTED';
  bool get isCompleted => isReleased;
  bool get isAwaitingAssessment =>
      feeAssessmentStatus.toUpperCase() == 'AWAITING_ASSESSMENT';
  bool get isFeeWaived => feeAssessmentStatus.toUpperCase() == 'WAIVED';
  bool get isStatutoryExempt =>
      feeAssessmentStatus.toUpperCase() == 'STATUTORY_EXEMPT' ||
      {
        'certificate of indigency',
        'first time job seeker certificate',
      }.contains(
        documentType.trim().replaceAll(RegExp(r'\s+'), ' ').toLowerCase(),
      );
  bool get isFeeExempt => isStatutoryExempt;
  bool get hasOfferingSnapshot =>
      offeringId != null ||
      requirementsSnapshot.isNotEmpty ||
      publishedFeeAmountSnapshot != null ||
      offeringDetailsSnapshot.isNotEmpty;

  /// Formatted fee string in Philippine Pesos (e.g. "₱50.00")
  String? get formattedFee =>
      feeAmount != null ? '₱${feeAmount!.toStringAsFixed(2)}' : null;

  /// Returns tracking ID formatted matching reference design (e.g. "ID: #BC-2026-0892")
  String get formattedTrackingId {
    final prefix = _getDocumentPrefix(documentType);
    final year = createdAt != null ? createdAt!.year : DateTime.now().year;
    final paddedId = id.toString().padLeft(4, '0');
    return 'ID: #$prefix-$year-$paddedId';
  }

  /// Returns human-readable date string (e.g. "Requested Oct 24, 2026")
  String get formattedRequestedDate {
    if (createdAt == null) {
      return 'Requested recently';
    }
    final dt = createdAt!;
    final months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    final monthName = months[dt.month - 1];
    return 'Requested $monthName ${dt.day}, ${dt.year}';
  }

  /// Human-readable badge text in uppercase matching reference UI (e.g. "PROCESSING", "READY FOR PICKUP")
  String get statusBadgeLabel {
    switch (status.toUpperCase()) {
      case 'PROCESSING':
        return 'PROCESSING';
      case 'READY_FOR_PICKUP':
        return 'READY FOR PICKUP';
      case 'RELEASED':
        return 'COMPLETED';
      case 'REJECTED':
        return 'REJECTED';
      case 'PENDING':
      default:
        return 'PENDING';
    }
  }

  /// Badge background color matching reference UI
  Color get statusBadgeBgColor {
    switch (status.toUpperCase()) {
      case 'PROCESSING':
        return const Color(0xFFDBEAFE);
      case 'READY_FOR_PICKUP':
        return const Color(0xFFDCFCE7);
      case 'RELEASED':
        return const Color(0xFFF1F5F9);
      case 'REJECTED':
        return const Color(0xFFFEE2E2);
      case 'PENDING':
      default:
        return const Color(0xFFFEF3C7);
    }
  }

  /// Badge text color matching reference UI
  Color get statusBadgeTextColor {
    switch (status.toUpperCase()) {
      case 'PROCESSING':
        return const Color(0xFF1E40AF);
      case 'READY_FOR_PICKUP':
        return const Color(0xFF15803D);
      case 'RELEASED':
        return const Color(0xFF64748B);
      case 'REJECTED':
        return const Color(0xFFDC2626);
      case 'PENDING':
      default:
        return const Color(0xFFB45309);
    }
  }

  /// Human-readable label for status descriptions
  String get statusDisplay {
    switch (status.toUpperCase()) {
      case 'PENDING':
        return 'Pending Review';
      case 'PROCESSING':
        return 'In Processing';
      case 'READY_FOR_PICKUP':
        return 'Ready for Pickup';
      case 'RELEASED':
        return 'Released / Completed';
      case 'REJECTED':
        return 'Rejected';
      default:
        return status;
    }
  }

  static String _getDocumentPrefix(String docType) {
    final lower = docType.toLowerCase();
    if (lower.contains('clearance')) return 'BC';
    if (lower.contains('indigency')) return 'CI';
    if (lower.contains('residency')) return 'RC';
    if (lower.contains('business') || lower.contains('permit')) return 'BP';
    if (lower.contains('tax')) return 'TC';
    return 'DOC';
  }
}
