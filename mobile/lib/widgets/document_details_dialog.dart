import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../core/theme/app_colors.dart';
import '../models/document_request_model.dart';
import '../models/payment_recipient_model.dart';
import '../services/document_service.dart';
import 'document_payment_section.dart';
import 'document_request_summary.dart';

/// Modal dialog showing complete document request lifecycle details and PDF download
class DocumentDetailsDialog extends StatefulWidget {
  final DocumentRequestModel request;
  final DocumentService? documentService;
  final VoidCallback? onRequestUpdated;
  final Future<void> Function()? onGetCounterTicket;

  const DocumentDetailsDialog({
    super.key,
    required this.request,
    this.documentService,
    this.onRequestUpdated,
    this.onGetCounterTicket,
  });

  @override
  State<DocumentDetailsDialog> createState() => _DocumentDetailsDialogState();
}

class _DocumentDetailsDialogState extends State<DocumentDetailsDialog> {
  bool _isDownloading = false;
  bool _isRequestingCounterTicket = false;
  bool _isSubmittingPayment = false;
  bool _isLoadingPaymentRecipients = false;
  String? _paymentRecipientError;
  List<PaymentRecipientModel> _paymentRecipients = const [];
  int? _selectedRecipientId;
  final TextEditingController _paymentReferenceController =
      TextEditingController();
  late String _paymentStatus;
  late String? _paymentMethod;
  late String? _paymentReviewNote;
  DateTime _selectedTransactedAt = DateTime.now();
  Uint8List? _selectedProofBytes;
  String? _selectedProofFilename;

  @override
  void initState() {
    super.initState();
    _paymentStatus = widget.request.paymentStatus;
    _paymentMethod = widget.request.paymentMethod;
    _paymentReviewNote = widget.request.paymentReviewNote;
    _selectedRecipientId = widget.request.paymentRecipientId;
    _selectedTransactedAt =
        widget.request.paymentTransactedAt ?? DateTime.now();
    if (widget.request.isReadyForPickup &&
        (widget.request.feeAmount ?? 0) > 0 &&
        widget.documentService != null) {
      _loadPaymentRecipients();
    }
  }

  Future<void> _loadPaymentRecipients() async {
    setState(() => _isLoadingPaymentRecipients = true);
    try {
      final recipients = await widget.documentService!.fetchPaymentRecipients();
      if (!mounted) return;
      setState(() {
        _paymentRecipients = recipients;
        if (!recipients.any((item) => item.id == _selectedRecipientId)) {
          _selectedRecipientId = recipients.isEmpty
              ? null
              : recipients.first.id;
        }
      });
    } catch (_) {
      if (!mounted) return;
      setState(
        () => _paymentRecipientError =
            'Could not load your barangay payment recipients.',
      );
    } finally {
      if (mounted) setState(() => _isLoadingPaymentRecipients = false);
    }
  }

  @override
  void dispose() {
    _paymentReferenceController.dispose();
    super.dispose();
  }

  Future<void> _handleSubmitPaymentReference() async {
    final service = widget.documentService;
    final reference = _paymentReferenceController.text.trim();
    if (_isSubmittingPayment) {
      return;
    }
    if (service == null) {
      _showPaymentSubmissionMessage(
        'Payment submission is unavailable. Please reopen the request and try again.',
      );
      return;
    }
    if (_selectedRecipientId == null) {
      _showPaymentSubmissionMessage('Choose a payment recipient first.');
      return;
    }
    if (reference.isEmpty) {
      _showPaymentSubmissionMessage('Enter the transfer reference first.');
      return;
    }
    final proofBytes = _selectedProofBytes;
    if (proofBytes == null || proofBytes.isEmpty) {
      _showPaymentSubmissionMessage('Add a receipt screenshot first.');
      return;
    }

    setState(() => _isSubmittingPayment = true);
    try {
      final updated = await service.submitPaymentReference(
        requestId: widget.request.id,
        paymentRecipientId: _selectedRecipientId!,
        paymentReference: reference,
        transactedAt: _selectedTransactedAt,
        proofImageBytes: proofBytes,
        proofImageFilename: _selectedProofFilename ?? 'receipt.jpg',
      );
      if (!mounted) return;
      setState(() {
        _paymentStatus = updated.paymentStatus;
        _paymentMethod = updated.paymentMethod;
        _paymentReviewNote = updated.paymentReviewNote;
        _paymentReferenceController.clear();
        _selectedProofBytes = null;
        _selectedProofFilename = null;
      });
      widget.onRequestUpdated?.call();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Reference sent to barangay staff for verification.'),
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not submit payment reference: $error')),
      );
    } finally {
      if (mounted) setState(() => _isSubmittingPayment = false);
    }
  }

  Future<void> _handleGetCounterTicket() async {
    final callback = widget.onGetCounterTicket;
    if (callback == null || _isRequestingCounterTicket) return;
    setState(() => _isRequestingCounterTicket = true);
    try {
      await callback();
    } finally {
      if (mounted) setState(() => _isRequestingCounterTicket = false);
    }
  }

  void _showPaymentSubmissionMessage(String message) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  void _handleViewProof() {
    final service = widget.documentService;
    if (service == null) return;
    showDialog<void>(
      context: context,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Uploaded Receipt Proof',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              FutureBuilder<Uint8List>(
                future: service.fetchPaymentProof(widget.request.id),
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Padding(
                      padding: EdgeInsets.all(32),
                      child: CircularProgressIndicator(),
                    );
                  }
                  if (snapshot.hasError ||
                      !snapshot.hasData ||
                      snapshot.data!.isEmpty) {
                    return const Padding(
                      padding: EdgeInsets.all(24),
                      child: Text(
                        'Could not load payment proof image.',
                        style: TextStyle(color: Colors.red),
                      ),
                    );
                  }
                  return ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Image.memory(
                      snapshot.data!,
                      fit: BoxFit.contain,
                      height: 300,
                    ),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _handleDownloadPdf() async {
    final documentService = widget.documentService;
    if (documentService == null || _isDownloading) return;

    setState(() => _isDownloading = true);

    try {
      final pdfBytes = await documentService.downloadDocumentPdf(
        widget.request.id,
      );

      if (pdfBytes.isEmpty) {
        throw Exception('The server returned an empty PDF.');
      }

      final directory = await getApplicationDocumentsDirectory();
      final fileName = 'kapitbayan_clearance_${widget.request.id}.pdf';
      final file = File('${directory.path}/$fileName');

      await file.writeAsBytes(pdfBytes, flush: true);

      final openResult = await OpenFilex.open(
        file.path,
        type: 'application/pdf',
      );

      if (openResult.type != ResultType.done) {
        throw Exception(
          'Saved as $fileName, but could not open it: ${openResult.message}',
        );
      }

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('PDF saved and opened: $fileName'),
          backgroundColor: const Color(0xFF10B981),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (e) {
      if (!mounted) return;

      final message = e.toString().replaceFirst(RegExp(r'^Exception:\s*'), '');

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not download or open the PDF: $message'),
          backgroundColor: const Color(0xFFEF4444),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isDownloading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final req = widget.request;
    final canDownload = req.isReadyForPickup || req.isReleased;

    final canSubmitElectronicPayment =
        req.isReadyForPickup &&
        (req.feeAmount ?? 0) > 0 &&
        _paymentMethod != 'CASH' &&
        (_paymentStatus == 'UNPAID' || _paymentStatus == 'REJECTED');

    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.85,
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Drag handle
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: const Color(0xFFCBD5E1),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 18),

              // Header with Title and Status
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: const Color(0xFFF1F5F9),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Center(
                      child: Icon(
                        Icons.description_outlined,
                        color: AppColors.primaryNavy,
                        size: 24,
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          req.documentType,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                            color: AppColors.textPrimary,
                            letterSpacing: -0.3,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          req.formattedTrackingId,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: req.statusBadgeBgColor,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      req.statusBadgeLabel,
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        color: req.statusBadgeTextColor,
                        letterSpacing: 0.4,
                      ),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 20),
              const Divider(color: Color(0xFFF1F5F9), height: 1),
              const SizedBox(height: 16),

              DocumentRequestSummary(
                request: req,
                paymentStatus: _paymentStatus,
                paymentReviewNote: _paymentReviewNote,
              ),

              DocumentPaymentSection(
                request: DocumentRequestModel(
                  id: req.id,
                  documentType: req.documentType,
                  purpose: req.purpose,
                  urgencyTag: req.urgencyTag,
                  status: req.status,
                  adminNotes: req.adminNotes,
                  orNumber: req.orNumber,
                  feeAmount: req.feeAmount,
                  paymentMethod: _paymentMethod,
                  paymentReference: req.paymentReference,
                  paymentRecipientId: req.paymentRecipientId,
                  paymentRecipientName: req.paymentRecipientName,
                  paymentRecipientIdentifier: req.paymentRecipientIdentifier,
                  paymentInstructions: req.paymentInstructions,
                  paymentStatus: _paymentStatus,
                  paymentReviewNote: _paymentReviewNote,
                  paymentProofUrl: req.paymentProofUrl,
                  paymentTransactedAt: req.paymentTransactedAt,
                  isWalkin: req.isWalkin,
                  createdAt: req.createdAt,
                  updatedAt: req.updatedAt,
                ),
                canSubmitElectronicPayment: canSubmitElectronicPayment,
                isLoadingRecipients: _isLoadingPaymentRecipients,
                recipientError: _paymentRecipientError,
                recipients: _paymentRecipients,
                selectedRecipientId: _selectedRecipientId,
                referenceController: _paymentReferenceController,
                selectedTransactedAt: _selectedTransactedAt,
                selectedProofBytes: _selectedProofBytes,
                selectedProofFilename: _selectedProofFilename,
                isSubmitting: _isSubmittingPayment,
                onSelectedRecipientChanged: (value) =>
                    setState(() => _selectedRecipientId = value),
                onTransactedAtChanged: (value) =>
                    setState(() => _selectedTransactedAt = value),
                onProofSelected: (bytes) =>
                    setState(() => _selectedProofBytes = bytes),
                onProofFilenameSelected: (filename) =>
                    setState(() => _selectedProofFilename = filename),
                onSubmitPaymentReference: _handleSubmitPaymentReference,
                onViewProof: _handleViewProof,
              ),

              const SizedBox(height: 24),

              if (widget.onGetCounterTicket != null) ...[
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: OutlinedButton.icon(
                    onPressed: _isRequestingCounterTicket
                        ? null
                        : _handleGetCounterTicket,
                    icon: _isRequestingCounterTicket
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.confirmation_number_outlined),
                    label: Text(
                      _isRequestingCounterTicket
                          ? 'Getting counter ticket...'
                          : 'Get counter queue ticket',
                    ),
                  ),
                ),
                const SizedBox(height: 10),
              ],

              // Action Button if PDF can be generated or Close
              if (canDownload) ...[
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton.icon(
                    onPressed: _isDownloading ? null : _handleDownloadPdf,
                    icon: _isDownloading
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                Colors.white,
                              ),
                            ),
                          )
                        : const Icon(
                            Icons.download_rounded,
                            color: Colors.white,
                            size: 20,
                          ),
                    label: Text(
                      _isDownloading
                          ? 'Generating Certificate...'
                          : 'Download Official PDF',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primaryNavy,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
              ],

              SizedBox(
                width: double.infinity,
                height: 46,
                child: TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text(
                    'Close',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textMuted,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
