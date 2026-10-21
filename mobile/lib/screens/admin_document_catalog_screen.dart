import 'package:flutter/material.dart';

import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';
import '../models/document_offering_model.dart';
import '../services/document_service.dart';

class AdminDocumentCatalogScreen extends StatefulWidget {
  final DocumentService service;

  const AdminDocumentCatalogScreen({super.key, required this.service});

  @override
  State<AdminDocumentCatalogScreen> createState() =>
      _AdminDocumentCatalogScreenState();
}

class _AdminDocumentCatalogScreenState
    extends State<AdminDocumentCatalogScreen> {
  List<DocumentOfferingModel> _offerings = [];
  bool _loading = true;
  String? _error;
  int? _savingId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final offerings = await widget.service.fetchDocumentOfferings();
      if (!mounted) return;
      setState(() {
        _offerings = offerings;
        _error = null;
      });
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not load document services.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _edit([DocumentOfferingModel? offering]) async {
    final draft = await showDialog<_DocumentOfferingDraft>(
      context: context,
      builder: (_) => _DocumentOfferingEditor(offering: offering),
    );
    if (draft == null || !mounted) return;

    setState(() => _savingId = offering?.id ?? -1);
    try {
      await widget.service.saveDocumentOffering(
        offeringId: offering?.id,
        documentType: draft.documentType,
        requirements: draft.requirements,
        publishedFeeAmount: draft.publishedFeeAmount,
        details: draft.details,
        isActive: draft.isActive,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.tr('Document service saved.'))),
      );
      await _load();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(context.tr("We couldn't save this document service.")),
        ),
      );
    } finally {
      if (mounted) setState(() => _savingId = null);
    }
  }

  Future<void> _setActive(DocumentOfferingModel offering, bool value) async {
    setState(() => _savingId = offering.id);
    try {
      await widget.service.setDocumentOfferingActive(
        offeringId: offering.id,
        isActive: value,
      );
      await _load();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            context.tr("We couldn't update this document service."),
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _savingId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tr;
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        title: Text(t('Document services and requirements')),
        actions: [
          IconButton(
            tooltip: t('Refresh'),
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _savingId != null ? null : () => _edit(),
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: Text(t('Add document service')),
      ),
      body: _loading && _offerings.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : _error != null && _offerings.isEmpty
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(_error!, textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                    OutlinedButton(onPressed: _load, child: Text(t('Retry'))),
                  ],
                ),
              ),
            )
          : _offerings.isEmpty
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  t(
                    'Add each document your Barangay offers, then save its requirements, fee, and details for residents.',
                  ),
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppColors.textMuted),
                ),
              ),
            )
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
                itemCount: _offerings.length + (_error != null ? 1 : 0),
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (context, index) {
                  if (_error != null && index == 0) {
                    return MaterialBanner(
                      content: Text(t(_error!)),
                      leading: const Icon(Icons.error_outline),
                      actions: [
                        TextButton(onPressed: _load, child: Text(t('Retry'))),
                      ],
                    );
                  }
                  final offering = _offerings[index - (_error != null ? 1 : 0)];
                  final busy = _savingId == offering.id;
                  return Card(
                    color: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                      side: const BorderSide(color: Color(0xFFE2E8F0)),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: Text(
                                  t(offering.documentType),
                                  style: const TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.w800,
                                    color: AppColors.textPrimary,
                                  ),
                                ),
                              ),
                              IconButton(
                                tooltip: t('Edit document service'),
                                onPressed: _savingId == null
                                    ? () => _edit(offering)
                                    : null,
                                icon: const Icon(Icons.edit_outlined),
                              ),
                            ],
                          ),
                          Text(
                            offering.publishedFeeAmount == null
                                ? t('Fee not listed')
                                : offering.publishedFeeAmount == 0
                                ? t('No fee')
                                : '₱${offering.publishedFeeAmount!.toStringAsFixed(2)}',
                            style: const TextStyle(
                              color: AppColors.primaryNavy,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            t('Requirements'),
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                          const SizedBox(height: 4),
                          if (offering.requirements.isEmpty)
                            Text(t('No requirements listed.'))
                          else
                            ...offering.requirements.map(
                              (requirement) => Padding(
                                padding: const EdgeInsets.only(bottom: 2),
                                child: Text('• ${t(requirement)}'),
                              ),
                            ),
                          if (offering.details.isNotEmpty) ...[
                            const SizedBox(height: 8),
                            Text(t(offering.details)),
                          ],
                          const Divider(height: 22),
                          SwitchListTile.adaptive(
                            contentPadding: EdgeInsets.zero,
                            title: Text(t('Available to residents')),
                            subtitle: Text(
                              offering.isActive ? t('Active') : t('Inactive'),
                            ),
                            value: offering.isActive,
                            onChanged: _savingId == null
                                ? (value) => _setActive(offering, value)
                                : null,
                          ),
                          if (busy) const LinearProgressIndicator(minHeight: 2),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
    );
  }
}

class _DocumentOfferingDraft {
  final String documentType;
  final List<String> requirements;
  final double? publishedFeeAmount;
  final String details;
  final bool isActive;

  const _DocumentOfferingDraft({
    required this.documentType,
    required this.requirements,
    required this.publishedFeeAmount,
    required this.details,
    required this.isActive,
  });
}

class _DocumentOfferingEditor extends StatefulWidget {
  final DocumentOfferingModel? offering;

  const _DocumentOfferingEditor({this.offering});

  @override
  State<_DocumentOfferingEditor> createState() =>
      _DocumentOfferingEditorState();
}

class _DocumentOfferingEditorState extends State<_DocumentOfferingEditor> {
  late final TextEditingController _nameController;
  late final TextEditingController _requirementsController;
  late final TextEditingController _feeController;
  late final TextEditingController _detailsController;
  late bool _isActive;

  @override
  void initState() {
    super.initState();
    final offering = widget.offering;
    _nameController = TextEditingController(text: offering?.documentType ?? '');
    _requirementsController = TextEditingController(
      text: offering?.requirements.join('\n') ?? '',
    );
    _feeController = TextEditingController(
      text: offering?.publishedFeeAmount?.toStringAsFixed(2) ?? '',
    );
    _detailsController = TextEditingController(text: offering?.details ?? '');
    _isActive = offering?.isActive ?? true;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _requirementsController.dispose();
    _feeController.dispose();
    _detailsController.dispose();
    super.dispose();
  }

  void _save() {
    final name = _nameController.text.trim();
    final requirements = _requirementsController.text
        .split('\n')
        .map((value) => value.trim())
        .where((value) => value.isNotEmpty)
        .toList(growable: false);
    final feeText = _feeController.text.trim();
    final fee = feeText.isEmpty ? null : double.tryParse(feeText);
    final t = context.tr;
    if (name.isEmpty || name.length > 100) {
      _showError(t('Enter a document name up to 100 characters.'));
      return;
    }
    if (requirements.length > 30 ||
        requirements.any((value) => value.length > 250)) {
      _showError(
        t('Enter up to 30 requirements, each no longer than 250 characters.'),
      );
      return;
    }
    if (feeText.isNotEmpty && (fee == null || fee < 0 || fee > 999999.99)) {
      _showError(
        t('Enter a valid fee amount, or leave it blank if it varies.'),
      );
      return;
    }
    Navigator.of(context).pop(
      _DocumentOfferingDraft(
        documentType: name,
        requirements: requirements,
        publishedFeeAmount: fee,
        details: _detailsController.text.trim(),
        isActive: _isActive,
      ),
    );
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tr;
    return AlertDialog(
      title: Text(
        t(
          widget.offering == null
              ? 'New document service'
              : 'Edit document service',
        ),
      ),
      content: SizedBox(
        width: 480,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                controller: _nameController,
                maxLength: 100,
                textCapitalization: TextCapitalization.words,
                decoration: InputDecoration(labelText: t('Document name')),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _requirementsController,
                maxLength: 8000,
                maxLines: 5,
                decoration: InputDecoration(
                  labelText: t('Requirements, one per line'),
                  helperText: t(
                    'Requirements are specific to this document and Barangay.',
                  ),
                  alignLabelWithHint: true,
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _feeController,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: InputDecoration(
                  labelText: t('Published fee amount (PHP)'),
                  helperText: t(
                    'Leave blank if it varies or is not published. A value of 0 means no fee.',
                  ),
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _detailsController,
                maxLength: 2000,
                minLines: 2,
                maxLines: 4,
                decoration: InputDecoration(
                  labelText: t('Additional details'),
                  hintText: t('Add preparation, schedule, or payment details'),
                  alignLabelWithHint: true,
                ),
              ),
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: Text(t('Available to residents')),
                value: _isActive,
                onChanged: (value) => setState(() => _isActive = value),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(t('Cancel')),
        ),
        FilledButton.icon(
          onPressed: _save,
          icon: const Icon(Icons.save_outlined),
          label: Text(t('Save document service')),
        ),
      ],
    );
  }
}
