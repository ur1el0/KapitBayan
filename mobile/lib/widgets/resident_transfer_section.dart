import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../core/localization/app_language.dart';
import '../core/network/api_exception.dart';
import '../core/theme/app_colors.dart';
import '../models/barangay_model.dart';
import '../models/resident_transfer_model.dart';
import '../models/user_model.dart';
import '../services/auth_service.dart';
import 'custom_button.dart';
import 'custom_text_field.dart';

class ResidentTransferSection extends StatefulWidget {
  final UserModel user;
  final AuthService authService;

  const ResidentTransferSection({
    super.key,
    required this.user,
    required this.authService,
  });

  @override
  State<ResidentTransferSection> createState() => _ResidentTransferSectionState();
}

class _ResidentTransferSectionState extends State<ResidentTransferSection> {
  bool _isLoading = true;
  bool _loadError = false;
  bool _isSubmitting = false;

  List<BarangayModel> _barangays = [];
  List<ResidentTransferModel> _transfers = [];

  BarangayModel? _selectedBarangay;
  final TextEditingController _purokController = TextEditingController();
  final TextEditingController _addressDetailsController = TextEditingController();
  final TextEditingController _reasonController = TextEditingController();

  XFile? _proofFile;
  String? _proofFileError;
  String? _submissionFeedback;
  bool _isFeedbackError = false;

  final ImagePicker _imagePicker = ImagePicker();

  @override
  void initState() {
    super.initState();
    _loadTransferData();
  }

  @override
  void dispose() {
    _purokController.dispose();
    _addressDetailsController.dispose();
    _reasonController.dispose();
    super.dispose();
  }

  Future<void> _loadTransferData() async {
    setState(() {
      _isLoading = true;
      _loadError = false;
    });

    try {
      final results = await Future.wait([
        widget.authService.fetchBarangays(),
        widget.authService.fetchTransferRequests(),
      ]);

      if (!mounted) return;

      setState(() {
        _barangays = results[0] as List<BarangayModel>;
        _transfers = results[1] as List<ResidentTransferModel>;
        _loadError = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loadError = true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  List<BarangayModel> get _availableBarangays {
    final currentId = widget.user.barangayId;
    return _barangays.where((b) => b.id != currentId).toList();
  }

  bool get _hasPendingTransfer {
    return _transfers.any((t) => t.isPending);
  }

  ResidentTransferModel? get _pendingTransfer {
    try {
      return _transfers.firstWhere((t) => t.isPending);
    } catch (_) {
      return null;
    }
  }

  Future<void> _pickProofImage() async {
    try {
      final picked = await _imagePicker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 85,
      );
      if (picked == null) return;

      final length = await picked.length();
      if (length > 5 * 1024 * 1024) {
        setState(() {
          _proofFile = null;
          _proofFileError = 'Residency proof image must be 5 MiB or smaller.';
        });
        return;
      }

      setState(() {
        _proofFile = picked;
        _proofFileError = null;
      });
    } catch (_) {
      setState(() {
        _proofFileError = 'Could not select proof image. Please try again.';
      });
    }
  }

  Future<void> _submitTransfer() async {
    if (_selectedBarangay == null) {
      setState(() {
        _submissionFeedback = 'Please select a receiving Barangay.';
        _isFeedbackError = true;
      });
      return;
    }

    final reason = _reasonController.text.trim();
    if (reason.isEmpty) {
      setState(() {
        _submissionFeedback = 'Please explain why you are requesting a transfer.';
        _isFeedbackError = true;
      });
      return;
    }

    if (_proofFile == null) {
      setState(() {
        _proofFileError = 'Upload proof of residency to request a transfer.';
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _submissionFeedback = null;
      _proofFileError = null;
    });

    try {
      await widget.authService.submitTransferRequest(
        destinationBarangayId: _selectedBarangay!.id,
        reason: reason,
        purok: _purokController.text.trim(),
        addressDetails: _addressDetailsController.text.trim(),
        proofFile: _proofFile!,
      );

      if (!mounted) return;

      _reasonController.clear();
      _purokController.clear();
      _addressDetailsController.clear();

      setState(() {
        _selectedBarangay = null;
        _proofFile = null;
        _submissionFeedback =
            'Transfer request sent to the receiving Barangay for verification.';
        _isFeedbackError = false;
      });

      await _loadTransferData();
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _submissionFeedback = e.message;
        _isFeedbackError = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _submissionFeedback =
            'Could not submit transfer request. Please try again.';
        _isFeedbackError = true;
      });
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Material(
        color: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        clipBehavior: Clip.antiAlias,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      color: const Color(0xFFEEF2FF),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(
                      Icons.swap_horiz_rounded,
                      color: Color(0xFF4338CA),
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.tr('Barangay Transfer'),
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          context.tr('Move your account to another Barangay.'),
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              if (_submissionFeedback != null) ...[
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: _isFeedbackError
                        ? const Color(0xFFFFF1F2)
                        : const Color(0xFFECFDF5),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: _isFeedbackError
                          ? const Color(0xFFFECDD3)
                          : const Color(0xFFA7F3D0),
                    ),
                  ),
                  child: Text(
                    _submissionFeedback!,
                    style: TextStyle(
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                      color: _isFeedbackError
                          ? const Color(0xFF9F1239)
                          : const Color(0xFF065F46),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
              ],
              if (_isLoading)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 24),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_loadError)
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF1F2),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFFECDD3)),
                  ),
                  child: Column(
                    children: [
                      Text(
                        context.tr('Could not load transfer information.'),
                        style: const TextStyle(
                          fontSize: 13,
                          color: Color(0xFF9F1239),
                        ),
                      ),
                      const SizedBox(height: 8),
                      TextButton.icon(
                        onPressed: _loadTransferData,
                        icon: const Icon(Icons.refresh_rounded, size: 18),
                        label: Text(context.tr('Try Again')),
                      ),
                    ],
                  ),
                )
              else if (!widget.user.isVerified)
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFFBEB),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFFDE68A)),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.shield_outlined,
                        color: Color(0xFFB45309),
                        size: 20,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          context.tr(
                            'Barangay transfer requests are available after your resident account is verified.',
                          ),
                          style: const TextStyle(
                            fontSize: 13,
                            color: Color(0xFF92400E),
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                )
              else if (_hasPendingTransfer)
                _buildPendingCard(_pendingTransfer!)
              else
                _buildTransferForm(),
              if (_transfers.isNotEmpty) ...[
                const SizedBox(height: 20),
                const Divider(height: 1, color: Color(0xFFE2E8F0)),
                const SizedBox(height: 16),
                Text(
                  context.tr('Transfer History'),
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 10),
                ..._transfers.map(_buildHistoryTile),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPendingCard(ResidentTransferModel transfer) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFBEB),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFFDE68A)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.hourglass_top_rounded,
                color: Color(0xFFB45309),
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${transfer.sourceBarangayName} → ${transfer.destinationBarangayName}',
                  style: const TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF92400E),
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEF3C7),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFFCD34D)),
                ),
                child: const Text(
                  'PENDING',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFFB45309),
                  ),
                ),
              ),
            ],
          ),
          if (transfer.newResidenceFormatted.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              'New residence: ${transfer.newResidenceFormatted}',
              style: const TextStyle(fontSize: 12, color: Color(0xFF78350F)),
            ),
          ],
          const SizedBox(height: 6),
          Text(
            transfer.reason,
            style: const TextStyle(fontSize: 12, color: Color(0xFF78350F)),
          ),
          const SizedBox(height: 8),
          const Text(
            'You already have a transfer request waiting for review. You can submit another after it is approved or rejected.',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: Color(0xFF92400E),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTransferForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          context.tr('RECEIVING BARANGAY'),
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w800,
            color: Color(0xFF64748B),
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.borderSubtle),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<BarangayModel>(
              isExpanded: true,
              value: _selectedBarangay,
              hint: Text(
                context.tr('Choose receiving Barangay'),
                style: const TextStyle(fontSize: 14, color: AppColors.textMuted),
              ),
              items: _availableBarangays.map((b) {
                return DropdownMenuItem<BarangayModel>(
                  value: b,
                  child: Text(
                    b.displayName,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                );
              }).toList(),
              onChanged: _isSubmitting
                  ? null
                  : (b) => setState(() => _selectedBarangay = b),
            ),
          ),
        ),
        const SizedBox(height: 14),
        CustomTextField(
          label: context.tr('Purok / Zone (if applicable)'),
          controller: _purokController,
          hintText: 'e.g. Purok 3',
          prefixIcon: Icons.location_on_outlined,
          enabled: !_isSubmitting,
        ),
        const SizedBox(height: 14),
        CustomTextField(
          label: context.tr('New Street Address / Details'),
          controller: _addressDetailsController,
          hintText: 'e.g. 123 Rizal St',
          prefixIcon: Icons.home_outlined,
          enabled: !_isSubmitting,
        ),
        const SizedBox(height: 14),
        Text(
          context.tr('PROOF OF RESIDENCY'),
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w800,
            color: Color(0xFF64748B),
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 6),
        InkWell(
          onTap: _isSubmitting ? null : _pickProofImage,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: _proofFileError != null
                    ? AppColors.error
                    : AppColors.borderSubtle,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  _proofFile != null
                      ? Icons.check_circle_rounded
                      : Icons.upload_file_rounded,
                  color: _proofFile != null
                      ? AppColors.success
                      : AppColors.primaryNavy,
                  size: 24,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _proofFile != null
                            ? _proofFile!.name
                            : context.tr('Upload residency proof (utility bill, lease, etc.)'),
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: _proofFile != null
                              ? FontWeight.w700
                              : FontWeight.w500,
                          color: _proofFile != null
                              ? AppColors.textPrimary
                              : AppColors.textMuted,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        context.tr('Image file up to 5 MiB'),
                        style: const TextStyle(
                          fontSize: 11,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                if (_proofFile != null)
                  IconButton(
                    onPressed: () => setState(() => _proofFile = null),
                    icon: const Icon(Icons.close_rounded, size: 18),
                    color: AppColors.textMuted,
                    tooltip: 'Remove proof image',
                  ),
              ],
            ),
          ),
        ),
        if (_proofFileError != null) ...[
          const SizedBox(height: 4),
          Text(
            _proofFileError!,
            style: const TextStyle(
              fontSize: 11.5,
              fontWeight: FontWeight.w600,
              color: AppColors.error,
            ),
          ),
        ],
        const SizedBox(height: 14),
        CustomTextField(
          label: context.tr('Reason for moving'),
          controller: _reasonController,
          hintText: 'Explain why you are requesting a transfer',
          prefixIcon: Icons.notes_rounded,
          enabled: !_isSubmitting,
        ),
        const SizedBox(height: 10),
        Text(
          context.tr(
            'Your Barangay assignment changes only after approval. Existing requests and queue records stay with the Barangay that handled them.',
          ),
          style: const TextStyle(fontSize: 11.5, color: AppColors.textSecondary),
        ),
        const SizedBox(height: 16),
        CustomButton(
          text: context.tr('Submit Transfer Request'),
          icon: Icons.send_rounded,
          isLoading: _isSubmitting,
          onPressed: _isSubmitting ? null : _submitTransfer,
        ),
      ],
    );
  }

  Widget _buildHistoryTile(ResidentTransferModel request) {
    Color badgeBg;
    Color badgeText;
    if (request.isApproved) {
      badgeBg = const Color(0xFFD1FAE5);
      badgeText = const Color(0xFF065F46);
    } else if (request.isRejected) {
      badgeBg = const Color(0xFFFFE4E6);
      badgeText = const Color(0xFF9F1239);
    } else {
      badgeBg = const Color(0xFFFEF3C7);
      badgeText = const Color(0xFF92400E);
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  '${request.sourceBarangayName} → ${request.destinationBarangayName}',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: badgeBg,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  request.status,
                  style: TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w800,
                    color: badgeText,
                  ),
                ),
              ),
            ],
          ),
          if (request.newResidenceFormatted.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              'New residence: ${request.newResidenceFormatted}',
              style: const TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w500,
                color: AppColors.textSecondary,
              ),
            ),
          ],
          const SizedBox(height: 4),
          Text(
            request.reason,
            style: const TextStyle(fontSize: 12, color: AppColors.textPrimary),
          ),
          if (request.isRejected && request.reviewNote.isNotEmpty) ...[
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF1F2),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFFECDD3)),
              ),
              child: Text(
                'Rejection reason: ${request.reviewNote}',
                style: const TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF9F1239),
                ),
              ),
            ),
          ],
          if (request.isApproved && request.reviewNote.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              'Admin note: ${request.reviewNote}',
              style: const TextStyle(fontSize: 11.5, color: AppColors.textSecondary),
            ),
          ],
          if (request.createdAt != null) ...[
            const SizedBox(height: 6),
            Text(
              request.createdAt!.toLocal().toString().split('.')[0],
              style: const TextStyle(fontSize: 10.5, color: AppColors.textMuted),
            ),
          ],
        ],
      ),
    );
  }
}
