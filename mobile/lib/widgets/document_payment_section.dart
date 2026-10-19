import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../core/theme/app_colors.dart';
import '../models/document_request_model.dart';
import '../models/payment_recipient_model.dart';

class DocumentPaymentSection extends StatefulWidget {
  final DocumentRequestModel? request;
  final bool canSubmitElectronicPayment;
  final bool isLoadingRecipients;
  final String? recipientError;
  final List<PaymentRecipientModel> recipients;
  final int? selectedRecipientId;
  final TextEditingController referenceController;
  final DateTime? selectedTransactedAt;
  final Uint8List? selectedProofBytes;
  final String? selectedProofFilename;
  final bool isSubmitting;
  final ValueChanged<int?> onSelectedRecipientChanged;
  final ValueChanged<DateTime>? onTransactedAtChanged;
  final ValueChanged<Uint8List?>? onProofSelected;
  final ValueChanged<String?>? onProofFilenameSelected;
  final VoidCallback onSubmitPaymentReference;
  final VoidCallback? onViewProof;

  const DocumentPaymentSection({
    super.key,
    this.request,
    required this.canSubmitElectronicPayment,
    required this.isLoadingRecipients,
    required this.recipientError,
    required this.recipients,
    required this.selectedRecipientId,
    required this.referenceController,
    this.selectedTransactedAt,
    this.selectedProofBytes,
    this.selectedProofFilename,
    required this.isSubmitting,
    required this.onSelectedRecipientChanged,
    this.onTransactedAtChanged,
    this.onProofSelected,
    this.onProofFilenameSelected,
    required this.onSubmitPaymentReference,
    this.onViewProof,
  });

  @override
  State<DocumentPaymentSection> createState() => _DocumentPaymentSectionState();
}

class _DocumentPaymentSectionState extends State<DocumentPaymentSection> {
  late DateTime _transactedAt;
  Uint8List? _internalProofBytes;
  String? _internalProofFilename;

  @override
  void initState() {
    super.initState();
    _transactedAt = widget.selectedTransactedAt ?? DateTime.now();
    _internalProofBytes = widget.selectedProofBytes;
    _internalProofFilename = widget.selectedProofFilename;
  }

  @override
  void didUpdateWidget(covariant DocumentPaymentSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.selectedTransactedAt != null) {
      _transactedAt = widget.selectedTransactedAt!;
    }
    if (widget.selectedProofBytes != oldWidget.selectedProofBytes) {
      _internalProofBytes = widget.selectedProofBytes;
    }
    if (widget.selectedProofFilename != oldWidget.selectedProofFilename) {
      _internalProofFilename = widget.selectedProofFilename;
    }
  }

  String _formatDateTime(DateTime dt) {
    const months = [
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
    final hour = dt.hour == 0 ? 12 : (dt.hour > 12 ? dt.hour - 12 : dt.hour);
    final ampm = dt.hour >= 12 ? 'PM' : 'AM';
    final minute = dt.minute.toString().padLeft(2, '0');
    return '${months[dt.month - 1]} ${dt.day}, ${dt.year} $hour:$minute $ampm';
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picker = ImagePicker();
      final picked = await picker.pickImage(
        source: source,
        maxWidth: 2048,
        maxHeight: 2048,
        imageQuality: 85,
      );
      if (picked != null) {
        final bytes = await picked.readAsBytes();
        if (bytes.lengthInBytes > 5 * 1024 * 1024) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Receipt screenshot must be 5MB or smaller.'),
              backgroundColor: Colors.red,
            ),
          );
          return;
        }
        setState(() {
          _internalProofBytes = bytes;
          _internalProofFilename = picked.name;
        });
        widget.onProofSelected?.call(bytes);
        widget.onProofFilenameSelected?.call(picked.name);
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not pick image: $e')),
      );
    }
  }

  Future<void> _selectDateTime() async {
    final now = DateTime.now();
    final date = await showDatePicker(
      context: context,
      initialDate: _transactedAt,
      firstDate: now.subtract(const Duration(days: 365)),
      lastDate: now.add(const Duration(minutes: 5)),
    );
    if (date != null && mounted) {
      final time = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(_transactedAt),
      );
      if (time != null) {
        final combined = DateTime(
          date.year,
          date.month,
          date.day,
          time.hour,
          time.minute,
        );
        setState(() => _transactedAt = combined);
        widget.onTransactedAtChanged?.call(combined);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final req = widget.request;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 1. Processing Banner
        if (req != null && req.isProcessing && !req.isFeeWaived && !req.isStatutoryExempt) ...[
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFEFF6FF),
              border: Border.all(color: const Color(0xFFBFDBFE)),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.hourglass_top_rounded,
                  color: Color(0xFF1D4ED8),
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Payment Unavailable During Processing',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1E3A8A),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        req.isAwaitingAssessment
                            ? 'Your document is currently being prepared. Fee is awaiting staff assessment. Payment instructions will become available once marked READY FOR PICKUP.'
                            : 'Your document is currently being prepared. Payment submission unlocks once marked READY FOR PICKUP.${(req.feeAmount ?? 0) > 0 ? " Assessed fee: ${req.formattedFee}." : ""}',
                        style: const TextStyle(
                          fontSize: 12,
                          height: 1.4,
                          color: Color(0xFF1E40AF),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],

        // Staff-Approved Fee Waiver Banner
        if (req != null && req.isFeeWaived) ...[
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFF0FDF4),
              border: Border.all(color: const Color(0xFF86EFAC)),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.verified_outlined,
                  color: Color(0xFF15803D),
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Fee Waived (₱0.00) — Staff Approved',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF14532D),
                        ),
                      ),
                      if (req.feeWaiverReason != null && req.feeWaiverReason!.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Reason: ${req.feeWaiverReason}',
                          style: const TextStyle(
                            fontSize: 12,
                            height: 1.4,
                            color: Color(0xFF166534),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],

        // 2. Cash Instructions Banner
        if (req != null && req.paymentMethod == 'CASH') ...[
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFF0FDF4),
              border: Border.all(color: const Color(0xFFBBF7D0)),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.payments_outlined,
                  color: Color(0xFF15803D),
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Cash Payment at Barangay Hall',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF14532D),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Please proceed to the Barangay Treasurer desk to settle your fee (${req.formattedFee ?? "upon pickup"}). No online receipt upload is required.',
                        style: const TextStyle(
                          fontSize: 12,
                          height: 1.4,
                          color: Color(0xFF166534),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],

        // 3. Fee-Exempt Banner
        if (req != null && req.isFeeExempt) ...[
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFF0FDF4),
              border: Border.all(color: const Color(0xFF86EFAC)),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.verified_outlined,
                  color: Color(0xFF15803D),
                  size: 20,
                ),
                SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Statutory Fee Exemption (₱0.00)',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF14532D),
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'This certificate qualifies for statutory fee exemption under RA 11261 / Indigency guidelines. No fee or payment reference required.',
                        style: TextStyle(
                          fontSize: 12,
                          height: 1.4,
                          color: Color(0xFF166534),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],

        if (req != null &&
            !req.isFeeExempt &&
            (req.isReadyForPickup || req.isReleased) &&
            (req.feeAmount ?? 0) <= 0) ...[
          const SizedBox(height: 16),
          const Text(
            'No payment required',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: Color(0xFF166534),
            ),
          ),
        ],

        // 4. Pending Verification State Card with Proof Preview
        if (req != null && req.paymentStatus == 'PENDING_VERIFICATION') ...[
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFFFFBEB),
              border: Border.all(color: const Color(0xFFFDE68A)),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(
                      Icons.hourglass_bottom_rounded,
                      color: Color(0xFFB45309),
                      size: 18,
                    ),
                    SizedBox(width: 8),
                    Text(
                      'Payment Submitted · Awaiting Verification',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF78350F),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                if (req.paymentReference != null &&
                    req.paymentReference!.isNotEmpty)
                  Text(
                    'Reference: ${req.paymentReference}',
                    style: const TextStyle(
                      fontSize: 12,
                      fontFamily: 'monospace',
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF92400E),
                    ),
                  ),
                if (req.paymentTransactedAt != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      'Transacted: ${_formatDateTime(req.paymentTransactedAt!)}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFF92400E),
                      ),
                    ),
                  ),
                if (req.paymentRecipientName != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      'Recipient: ${req.paymentRecipientName} · ${req.paymentRecipientIdentifier ?? ""}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFF92400E),
                      ),
                    ),
                  ),
                if (widget.onViewProof != null &&
                    req.paymentProofUrl != null) ...[
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    onPressed: widget.onViewProof,
                    icon: const Icon(Icons.image_outlined, size: 16),
                    label: const Text('View Uploaded Receipt Proof'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF92400E),
                      side: const BorderSide(color: Color(0xFFFDE68A)),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],

        // 5. Rejection Alert Card
        if (req != null && req.paymentStatus == 'REJECTED') ...[
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFFEF2F2),
              border: Border.all(color: const Color(0xFFFECACA)),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(
                      Icons.error_outline_rounded,
                      color: Color(0xFFDC2626),
                      size: 18,
                    ),
                    SizedBox(width: 8),
                    Text(
                      'Payment Reference Rejected',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF991B1B),
                      ),
                    ),
                  ],
                ),
                if (req.paymentReviewNote != null &&
                    req.paymentReviewNote!.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    'Staff note: ${req.paymentReviewNote}',
                    style: const TextStyle(
                      fontSize: 12,
                      color: Color(0xFFB91C1C),
                      height: 1.4,
                    ),
                  ),
                ],
                const SizedBox(height: 6),
                const Text(
                  'Please verify your transfer details, take a clear screenshot, and re-submit below.',
                  style: TextStyle(fontSize: 12, color: Color(0xFF7F1D1D)),
                ),
              ],
            ),
          ),
        ],

        // 6. Electronic Payment Submission Form
        if (widget.canSubmitElectronicPayment) ...[
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              border: Border.all(color: const Color(0xFFE2E8F0)),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Choose the official recipient configured by your barangay. Staff will verify the transfer reference manually before release.',
                  style: TextStyle(
                    fontSize: 12,
                    height: 1.4,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 10),
                if (widget.isLoadingRecipients)
                  const LinearProgressIndicator(),
                if (widget.recipientError != null)
                  Text(
                    widget.recipientError!,
                    style: const TextStyle(color: Colors.red),
                  ),
                if (!widget.isLoadingRecipients &&
                    widget.recipientError == null &&
                    widget.recipients.isEmpty)
                  const Text(
                    'Your barangay has no e-payment recipient configured. Contact the barangay hall or pay in person.',
                  ),
                if (widget.recipients.isNotEmpty) ...[
                  DropdownButtonFormField<int>(
                    initialValue: widget.recipients.any(
                          (item) => item.id == widget.selectedRecipientId,
                        )
                        ? widget.selectedRecipientId
                        : null,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Payment recipient',
                      border: OutlineInputBorder(),
                    ),
                    items: widget.recipients
                        .map(
                          (recipient) => DropdownMenuItem<int>(
                            value: recipient.id,
                            child: Text(
                              '${recipient.displayName} · ${recipient.providerLabel}',
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        )
                        .toList(),
                    onChanged: (value) =>
                        widget.onSelectedRecipientChanged(value),
                  ),
                  if (widget.selectedRecipientId != null)
                    Builder(
                      builder: (context) {
                        final recipient = widget.recipients.firstWhere(
                          (item) => item.id == widget.selectedRecipientId,
                        );
                        return Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            '${recipient.recipientName} · ${recipient.recipientIdentifier}'
                            '${recipient.instructions.isEmpty ? '' : '\n${recipient.instructions}'}',
                            style: const TextStyle(fontSize: 12, height: 1.4),
                          ),
                        );
                      },
                    ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: widget.referenceController,
                    maxLength: 100,
                    decoration: const InputDecoration(
                      labelText: 'Transfer reference',
                      border: OutlineInputBorder(),
                      helperText: 'Required before submitting',
                      counterText: '',
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Transaction Date & Time Selector
                  InkWell(
                    onTap: _selectDateTime,
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 12,
                      ),
                      decoration: BoxDecoration(
                        border: Border.all(color: const Color(0xFFCBD5E1)),
                        borderRadius: BorderRadius.circular(8),
                        color: Colors.white,
                      ),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.calendar_today_outlined,
                            size: 18,
                            color: AppColors.textMuted,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'Transaction Date & Time',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: AppColors.textMuted,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  _formatDateTime(_transactedAt),
                                  style: const TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                    color: AppColors.textPrimary,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const Icon(
                            Icons.edit_outlined,
                            size: 16,
                            color: AppColors.textMuted,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Receipt Screenshot Dropzone / Picker
                  const Text(
                    'Receipt Screenshot Proof (Required)',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 6),
                  if (_internalProofBytes != null) ...[
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        border: Border.all(color: const Color(0xFFCBD5E1)),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(6),
                            child: Image.memory(
                              _internalProofBytes!,
                              width: 48,
                              height: 48,
                              fit: BoxFit.cover,
                              errorBuilder: (context, error, stackTrace) =>
                                  Container(
                                    width: 48,
                                    height: 48,
                                    color: const Color(0xFFF1F5F9),
                                    child: const Icon(
                                      Icons.image_outlined,
                                      size: 24,
                                      color: AppColors.textMuted,
                                    ),
                                  ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _internalProofFilename ?? 'proof.jpg',
                                  style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  '${(_internalProofBytes!.lengthInBytes / 1024).toStringAsFixed(1)} KB',
                                  style: const TextStyle(
                                    fontSize: 11,
                                    color: AppColors.textMuted,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          IconButton(
                            icon: const Icon(
                              Icons.close,
                              size: 18,
                              color: Colors.red,
                            ),
                            onPressed: () {
                              setState(() {
                                _internalProofBytes = null;
                                _internalProofFilename = null;
                              });
                              widget.onProofSelected?.call(null);
                              widget.onProofFilenameSelected?.call(null);
                            },
                          ),
                        ],
                      ),
                    ),
                  ] else ...[
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => _pickImage(ImageSource.camera),
                            icon: const Icon(Icons.camera_alt_outlined, size: 16),
                            label: const Text('Take Photo', style: TextStyle(fontSize: 12)),
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 10),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => _pickImage(ImageSource.gallery),
                            icon: const Icon(Icons.photo_library_outlined, size: 16),
                            label: const Text('Gallery', style: TextStyle(fontSize: 12)),
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 10),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Please ensure your uploaded screenshot visibly shows the transaction reference number, amount, and date/time.',
                      style: TextStyle(
                        fontSize: 11,
                        color: AppColors.textMuted,
                        height: 1.3,
                      ),
                    ),
                  ],
                  if (_internalProofBytes == null ||
                      _internalProofBytes!.isEmpty) ...[
                    const SizedBox(height: 6),
                    const Text(
                      'Receipt screenshot is required before you can submit.',
                      style: TextStyle(
                        fontSize: 12,
                        color: Color(0xFFB91C1C),
                      ),
                    ),
                  ],

                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: widget.isSubmitting ||
                              widget.selectedRecipientId == null ||
                              _internalProofBytes == null ||
                              _internalProofBytes!.isEmpty
                          ? null
                          : widget.onSubmitPaymentReference,
                      child: Text(
                        widget.isSubmitting
                            ? 'Submitting…'
                            : 'Submit transfer reference',
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ],
    );
  }
}
