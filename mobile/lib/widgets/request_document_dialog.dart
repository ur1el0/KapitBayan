import 'package:flutter/material.dart';
import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';
import '../models/document_request_model.dart';
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
  static const List<String> availableTypes = [
    'Barangay Clearance',
    'Certificate of Indigency',
    'Residency Certificate',
    'Business Permit',
    'Community Tax Certificate (Cedula)',
  ];

  late String _selectedType;
  String _selectedUrgency = 'REGULAR';
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _selectedType = widget.initialDocumentType != null &&
            availableTypes.contains(widget.initialDocumentType)
        ? widget.initialDocumentType!
        : availableTypes.first;
  }

  final TextEditingController _purposeController = TextEditingController();

  Future<void> _submitRequest() async {
    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final newDoc = await widget.documentService.createDocumentRequest(
        documentType: _selectedType,
        urgencyTag: _selectedUrgency,
        purpose: _purposeController.text.isNotEmpty ?_purposeController.text : null,
      );

      if (mounted) {
        widget.onCreated(newDoc);
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${context.tr('Request for')} ${context.tr(_selectedType)} ${context.tr('submitted successfully!')}'),
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
            context.tr('Fill in the details below to submit your official request.'),
            style: TextStyle(
              fontSize: 13,
              color: AppColors.textMuted,
            ),
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
                icon: const Icon(Icons.arrow_drop_down, color: AppColors.primaryNavy),
                items: availableTypes.map((type) {
                  return DropdownMenuItem<String>(
                    value: type,
                    child: Text(
                      context.tr(type),
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) {
                    setState(() => _selectedType = val);
                  }
                },
              ),
            ),
          ),
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
              hintStyle: const TextStyle(fontSize: 13, color: Color(0xFF94A3B8)),
              filled: true,
              fillColor: const Color(0xFFF8FAFC),
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
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
                  const Icon(Icons.error_outline, color: Color(0xFFDC2626), size: 18),
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
                    color: isSelected ? AppColors.accentBlue : AppColors.textPrimary,
                  ),
                ),
                Icon(
                  isSelected ? Icons.check_circle : Icons.circle_outlined,
                  size: 16,
                  color: isSelected ? AppColors.accentBlue : const Color(0xFF94A3B8),
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
