import 'package:flutter/material.dart';

import '../core/document_types.dart';
import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';
import '../models/document_request_model.dart';
import '../models/document_offering_model.dart';
import '../services/document_service.dart';
import 'custom_button.dart';

/// Modal dialog allowing residents to submit a new document request
class RequestDocumentDialog extends StatefulWidget {
  final String? initialDocumentType;
  final DocumentService documentService;
  final Function(DocumentRequestModel createdRequest) onCreated;

  const RequestDocumentDialog({
    super.key,
    this.initialDocumentType,
    required this.documentService,
    required this.onCreated,
  });

  @override
  State<RequestDocumentDialog> createState() => _RequestDocumentDialogState();
}

class _RequestDocumentDialogState extends State<RequestDocumentDialog> {
  late String _selectedType;
  List<DocumentOfferingModel> _offerings = const [];
  bool _isLoadingOfferings = true;
  String? _catalogError;
  String _selectedUrgency = 'REGULAR';
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _selectedType = otherDocumentRequestType;
    _loadOfferings();
  }

  DocumentOfferingModel? get _selectedOffering {
    if (!_selectedType.startsWith('offering:')) return null;
    final id = int.tryParse(_selectedType.substring('offering:'.length));
    for (final offering in _offerings) {
      if (offering.id == id) return offering;
    }
    return null;
  }

  Future<void> _loadOfferings() async {
    try {
      final offerings = await widget.documentService.fetchDocumentOfferings();
      if (!mounted) return;
      final initialOffering = offerings.where(
        (offering) => offering.documentType == widget.initialDocumentType,
      );
      setState(() {
        _offerings = offerings;
        if (initialOffering.isNotEmpty) {
          _selectedType = 'offering:${initialOffering.first.id}';
        } else if (widget.initialDocumentType != null) {
          _selectedType = otherDocumentRequestType;
          _otherTypeController.text = widget.initialDocumentType!;
        } else if (offerings.isNotEmpty) {
          _selectedType = 'offering:${offerings.first.id}';
        }
      });
    } catch (_) {
      if (mounted) {
        setState(
          () =>
              _catalogError = 'Could not load your Barangay document services.',
        );
      }
    } finally {
      if (mounted) setState(() => _isLoadingOfferings = false);
    }
  }

  final TextEditingController _purposeController = TextEditingController();
  final TextEditingController _otherTypeController = TextEditingController();

  @override
  void dispose() {
    _purposeController.dispose();
    _otherTypeController.dispose();
    super.dispose();
  }

  Future<void> _submitRequest() async {
    final selectedOffering = _selectedOffering;
    final documentType =
        selectedOffering?.documentType ??
        (_selectedType == otherDocumentRequestType
            ? _otherTypeController.text.trim()
            : '');
    if (documentType.isEmpty || documentType.length > 100) {
      setState(
        () => _errorMessage = 'Enter a document name up to 100 characters.',
      );
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final purpose = _purposeController.text.isNotEmpty
          ? _purposeController.text
          : null;
      final newDoc = selectedOffering == null
          ? await widget.documentService.createDocumentRequest(
              documentType: documentType,
              urgencyTag: _selectedUrgency,
              purpose: purpose,
            )
          : await widget.documentService.createDocumentRequestFromOffering(
              offeringId: selectedOffering.id,
              documentType: documentType,
              urgencyTag: _selectedUrgency,
              purpose: purpose,
            );

      if (mounted) {
        widget.onCreated(newDoc);
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${context.tr('Request for')} ${context.tr(documentType)} ${context.tr('submitted successfully!')}',
            ),
            backgroundColor: const Color(0xFF10B981),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
          _errorMessage = e.toString().replaceAll('Exception:', '').trim();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final selectedOffering = _selectedOffering;
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
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

          Text(
            context.tr('New Document Request'),
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            context.tr(
              'Fill in the details below to submit your official request.',
            ),
            style: TextStyle(fontSize: 13, color: AppColors.textMuted),
          ),
          const SizedBox(height: 20),

          // Document Type Dropdown
          Text(
            context.tr('DOCUMENT TYPE'),
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: AppColors.textLabel,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _selectedType,
                isExpanded: true,
                icon: const Icon(
                  Icons.arrow_drop_down,
                  color: AppColors.primaryNavy,
                ),
                items: [
                  ..._offerings.map(
                    (offering) => DropdownMenuItem<String>(
                      value: 'offering:${offering.id}',
                      child: Text(
                        context.tr(offering.documentType),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                  ),
                  DropdownMenuItem<String>(
                    value: otherDocumentRequestType,
                    child: Text(
                      context.tr(otherDocumentRequestType),
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ),
                ],
                onChanged: (val) {
                  if (val != null) {
                    setState(() {
                      _selectedType = val;
                      _errorMessage = null;
                    });
                  }
                },
              ),
            ),
          ),
          if (_isLoadingOfferings) ...[
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: LinearProgressIndicator(minHeight: 2),
            ),
          ],
          if (_catalogError != null) ...[
            Text(
              context.tr(_catalogError!),
              style: const TextStyle(color: Colors.red, fontSize: 12),
            ),
          ],
          if (_offerings.isEmpty && !_isLoadingOfferings) ...[
            Text(
              context.tr(
                'Your Barangay has not published its document services yet. The request will need staff confirmation.',
              ),
              style: const TextStyle(color: Color(0xFFB45309), fontSize: 12),
            ),
          ],
          if (_selectedType == otherDocumentRequestType) ...[
            const SizedBox(height: 14),
            TextField(
              controller: _otherTypeController,
              maxLength: 100,
              textCapitalization: TextCapitalization.words,
              onChanged: (_) {
                if (_errorMessage != null) {
                  setState(() => _errorMessage = null);
                }
              },
              decoration: InputDecoration(
                labelText: context.tr('Document name'),
                hintText: context.tr('Enter the Barangay document name'),
                helperText: context.tr(
                  'Confirm availability and requirements with your Barangay.',
                ),
                border: OutlineInputBorder(),
              ),
            ),
          ],
          if (selectedOffering != null) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFEFF6FF),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFBFDBFE)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${context.tr('Published fee')}: ${selectedOffering.publishedFeeAmount == null
                        ? context.tr('Confirm with Barangay staff')
                        : selectedOffering.publishedFeeAmount == 0
                        ? context.tr('No fee')
                        : '₱${selectedOffering.publishedFeeAmount!.toStringAsFixed(2)}'}',
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(height: 6),
                  if (selectedOffering.requirements.isNotEmpty) ...[
                    Text(
                      context.tr('Bring these requirements:'),
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(height: 3),
                    ...selectedOffering.requirements.map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: 2),
                        child: Text(
                          '• ${context.tr(item)}',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ),
                    ),
                  ] else
                    Text(
                      context.tr(
                        'Your Barangay has not published requirements for this service yet.',
                      ),
                      style: const TextStyle(fontSize: 12),
                    ),
                  if (selectedOffering.details.isNotEmpty) ...[
                    const SizedBox(height: 5),
                    Text(
                      context.tr(selectedOffering.details),
                      style: const TextStyle(fontSize: 12),
                    ),
                  ],
                  const SizedBox(height: 5),
                  Text(
                    context.tr(
                      'Final fees are confirmed by Barangay staff during processing.',
                    ),
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.textMuted,
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 18),

          Text(
            context.tr('STATED PURPOSE (OPTIONAL)'),
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: AppColors.textLabel,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _purposeController,
            decoration: InputDecoration(
              hintText: context.tr('e.g. For local employment application'),
              hintStyle: const TextStyle(
                fontSize: 13,
                color: Color(0xFF94A3B8),
              ),
              filled: true,
              fillColor: const Color(0xFFF8FAFC),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 12,
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
              ),
            ),
          ),
          // Processing Urgency
          Text(
            context.tr('PROCESSING SPEED'),
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: AppColors.textLabel,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _UrgencyChoiceCard(
                  title: context.tr('Regular'),
                  subtitle: context.tr('1-3 Business Days'),
                  isSelected: _selectedUrgency == 'REGULAR',
                  onTap: () => setState(() => _selectedUrgency = 'REGULAR'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _UrgencyChoiceCard(
                  title: context.tr('Urgent'),
                  subtitle: context.tr('Same Day / Priority'),
                  isSelected: _selectedUrgency == 'URGENT',
                  onTap: () => setState(() => _selectedUrgency = 'URGENT'),
                ),
              ),
            ],
          ),

          if (_errorMessage != null) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFEE2E2),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.error_outline,
                    color: Color(0xFFDC2626),
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(
                        color: Color(0xFFDC2626),
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],

          const SizedBox(height: 24),

          // Submit Button
          CustomButton(
            text: context.tr('Submit Request'),
            isLoading: _isSubmitting,
            onPressed: _submitRequest,
          ),
        ],
      ),
    );
  }
}

class _UrgencyChoiceCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final bool isSelected;
  final VoidCallback onTap;

  const _UrgencyChoiceCard({
    required this.title,
    required this.subtitle,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFFEEF2FF) : Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? AppColors.accentBlue : const Color(0xFFE2E8F0),
            width: isSelected ? 1.8 : 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w700,
                    color: isSelected
                        ? AppColors.accentBlue
                        : AppColors.textPrimary,
                  ),
                ),
                Icon(
                  isSelected ? Icons.check_circle : Icons.circle_outlined,
                  size: 16,
                  color: isSelected
                      ? AppColors.accentBlue
                      : const Color(0xFF94A3B8),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              subtitle,
              style: const TextStyle(
                fontSize: 10.5,
                fontWeight: FontWeight.w500,
                color: AppColors.textMuted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
