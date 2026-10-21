import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../core/localization/app_language.dart';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../core/theme/app_colors.dart';
import '../models/document_request_model.dart';
import '../services/auth_service.dart';
import '../services/document_service.dart';
import '../services/storage_service.dart';
import 'admin_document_catalog_screen.dart';

class AdminDocumentRequestsScreen extends StatefulWidget {
  final bool showActionNeededFirst;

  const AdminDocumentRequestsScreen({
    super.key,
    this.showActionNeededFirst = true,
  });

  @override
  State<AdminDocumentRequestsScreen> createState() =>
      _AdminDocumentRequestsScreenState();
}

class _AdminDocumentRequestsScreenState
    extends State<AdminDocumentRequestsScreen> {
  DocumentService? _service;
  List<DocumentRequestModel> _requests = [];
  bool _isInitializing = true;
  bool _isLoading = false;
  String? _error;
  bool _actionNeededOnly = true;

  @override
  void initState() {
    super.initState();
    _actionNeededOnly = widget.showActionNeededFirst;
    _initialize();
  }

  Future<void> _initialize() async {
    try {
      final storage = await StorageService.init();
      final apiClient = ApiClient();
      AuthService(apiClient: apiClient, storageService: storage);
      _service = DocumentService(apiClient: apiClient, storageService: storage);
      await _loadRequests();
    } catch (error) {
      if (mounted) setState(() => _error = _friendlyError(error));
    } finally {
      if (mounted) setState(() => _isInitializing = false);
    }
  }

  String _friendlyError(Object error) => error is ApiException
      ? error.message
      : 'Could not load document requests. Check your connection and try again.';

  Future<void> _loadRequests() async {
    final service = _service;
    if (service == null) return;
    if (mounted) setState(() => _isLoading = true);
    try {
      final requests = await service.fetchDocumentRequests();
      if (!mounted) return;
      setState(() {
        _requests = requests;
        _error = null;
      });
    } catch (error) {
      if (mounted) setState(() => _error = _friendlyError(error));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  bool _needsAction(DocumentRequestModel request) {
    return request.isPending ||
        request.paymentStatus.toUpperCase() == 'PENDING_VERIFICATION' ||
        request.isAwaitingAssessment;
  }

  Future<void> _openRequest(DocumentRequestModel request) async {
    final service = _service;
    if (service == null) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => AdminDocumentRequestDetailsScreen(
          request: request,
          service: service,
        ),
      ),
    );
    if (mounted) await _loadRequests();
  }

  @override
  Widget build(BuildContext context) {
    final visible = _requests
        .where((request) => !_actionNeededOnly || _needsAction(request))
        .toList();
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        title: Text(context.tr('Document Requests')),
        actions: [
          IconButton(
            tooltip: context.tr('Manage document services'),
            onPressed: _service == null
                ? null
                : () => Navigator.of(context).push<void>(
                    MaterialPageRoute(
                      builder: (_) =>
                          AdminDocumentCatalogScreen(service: _service!),
                    ),
                  ),
            icon: const Icon(Icons.fact_check_outlined),
          ),
          IconButton(
            tooltip: 'Refresh document requests',
            onPressed: _isInitializing ? null : _loadRequests,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: _isInitializing
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  child: SegmentedButton<bool>(
                    segments: const [
                      ButtonSegment(
                        value: true,
                        icon: Icon(Icons.pending_actions_rounded),
                        label: Text('Action needed'),
                      ),
                      ButtonSegment(
                        value: false,
                        icon: Icon(Icons.list_alt_rounded),
                        label: Text('All requests'),
                      ),
                    ],
                    selected: {_actionNeededOnly},
                    onSelectionChanged: (selection) =>
                        setState(() => _actionNeededOnly = selection.first),
                  ),
                ),
                if (_error != null && _requests.isNotEmpty)
                  MaterialBanner(
                    content: Text(_error!),
                    leading: const Icon(Icons.error_outline),
                    actions: [
                      TextButton(
                        onPressed: _loadRequests,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                Expanded(
                  child: _isLoading && _requests.isEmpty
                      ? const Center(child: CircularProgressIndicator())
                      : _error != null && _requests.isEmpty
                      ? _RetryState(message: _error!, onRetry: _loadRequests)
                      : visible.isEmpty
                      ? _EmptyRequests(
                          actionNeededOnly: _actionNeededOnly,
                          onRefresh: _loadRequests,
                        )
                      : RefreshIndicator(
                          onRefresh: _loadRequests,
                          child: ListView.separated(
                            physics: const AlwaysScrollableScrollPhysics(),
                            padding: const EdgeInsets.all(16),
                            itemCount: visible.length,
                            separatorBuilder: (_, _) =>
                                const SizedBox(height: 10),
                            itemBuilder: (context, index) =>
                                _DocumentRequestCard(
                                  request: visible[index],
                                  onTap: () => _openRequest(visible[index]),
                                ),
                          ),
                        ),
                ),
              ],
            ),
    );
  }
}

class _DocumentRequestCard extends StatelessWidget {
  final DocumentRequestModel request;
  final VoidCallback onTap;

  const _DocumentRequestCard({required this.request, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final requester = request.requesterName?.trim().isNotEmpty == true
        ? request.requesterName!.trim()
        : request.walkinName?.trim().isNotEmpty == true
        ? request.walkinName!.trim()
        : 'Resident';
    final purok = request.purok?.trim().isNotEmpty == true
        ? request.purok!.trim()
        : request.walkinPurok?.trim();
    final paymentPending =
        request.paymentStatus.toUpperCase() == 'PENDING_VERIFICATION';
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Request #${request.id}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFF64748B),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  _StatusBadge(label: request.status),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                request.documentType,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                [
                  requester,
                  if (purok?.isNotEmpty == true) 'Purok $purok',
                ].join(' • '),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Color(0xFF475569)),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  _InfoPill(
                    label: request.feeAmount == null
                        ? 'Fee not assessed'
                        : '₱${request.feeAmount!.toStringAsFixed(2)}',
                    color: const Color(0xFFEFF6FF),
                    textColor: const Color(0xFF1D4ED8),
                  ),
                  _InfoPill(
                    label: paymentPending
                        ? 'Transfer awaiting review'
                        : request.paymentStatus.replaceAll('_', ' '),
                    color: paymentPending
                        ? const Color(0xFFFFF7ED)
                        : const Color(0xFFF1F5F9),
                    textColor: paymentPending
                        ? const Color(0xFF9A3412)
                        : const Color(0xFF475569),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: Text(
                  'Review request  ›',
                  style: TextStyle(
                    color: AppColors.primaryNavy,
                    fontWeight: FontWeight.w800,
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

class _StatusBadge extends StatelessWidget {
  final String label;

  const _StatusBadge({required this.label});

  @override
  Widget build(BuildContext context) {
    final status = label.toUpperCase();
    final color = switch (status) {
      'RELEASED' => const Color(0xFF047857),
      'REJECTED' => const Color(0xFFB91C1C),
      'READY_FOR_PICKUP' => const Color(0xFF6D28D9),
      'PROCESSING' => const Color(0xFF1D4ED8),
      _ => const Color(0xFFB45309),
    };
    return _InfoPill(
      label: status.replaceAll('_', ' '),
      color: color.withValues(alpha: 0.1),
      textColor: color,
    );
  }
}

class _InfoPill extends StatelessWidget {
  final String label;
  final Color color;
  final Color textColor;

  const _InfoPill({
    required this.label,
    required this.color,
    required this.textColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10,
          color: textColor,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _EmptyRequests extends StatelessWidget {
  final bool actionNeededOnly;
  final Future<void> Function() onRefresh;

  const _EmptyRequests({
    required this.actionNeededOnly,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          const SizedBox(height: 140),
          const Icon(Icons.inbox_outlined, size: 50, color: Colors.blueGrey),
          const SizedBox(height: 12),
          Text(
            actionNeededOnly
                ? 'No requests need action'
                : 'No document requests found',
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
          ),
          const SizedBox(height: 6),
          const Text(
            'Pull down to refresh this list.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Color(0xFF64748B)),
          ),
        ],
      ),
    );
  }
}

class _RetryState extends StatelessWidget {
  final String message;
  final Future<void> Function() onRetry;

  const _RetryState({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_rounded, size: 42, color: Colors.red),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Try again'),
            ),
          ],
        ),
      ),
    );
  }
}

class AdminDocumentRequestDetailsScreen extends StatefulWidget {
  final DocumentRequestModel request;
  final DocumentService service;

  const AdminDocumentRequestDetailsScreen({
    super.key,
    required this.request,
    required this.service,
  });

  @override
  State<AdminDocumentRequestDetailsScreen> createState() =>
      _AdminDocumentRequestDetailsScreenState();
}

class _AdminDocumentRequestDetailsScreenState
    extends State<AdminDocumentRequestDetailsScreen> {
  late DocumentRequestModel _request;
  late final TextEditingController _adminNotesController;
  late final TextEditingController _feeController;
  late final TextEditingController _waiverController;
  late final TextEditingController _orController;
  late final TextEditingController _paymentNoteController;
  late String _selectedStatus;
  late String _selectedPaymentMethod;
  bool _editFeeAssessment = false;
  bool _isUpdating = false;
  Future<Uint8List>? _proofFuture;

  @override
  void initState() {
    super.initState();
    _request = widget.request;
    _adminNotesController = TextEditingController(
      text: _request.adminNotes ?? '',
    );
    _feeController = TextEditingController(
      text: _request.isAwaitingAssessment || _request.feeAmount == null
          ? ''
          : _request.feeAmount!.toStringAsFixed(2),
    );
    _waiverController = TextEditingController(
      text: _request.feeWaiverReason ?? '',
    );
    _orController = TextEditingController(text: _request.orNumber ?? '');
    _paymentNoteController = TextEditingController();
    _selectedStatus = _request.isPending ? 'PROCESSING' : _request.status;
    _selectedPaymentMethod = _request.paymentMethod ?? '';
    _editFeeAssessment = _request.isAwaitingAssessment;
    if (_request.paymentProofUrl?.isNotEmpty == true) {
      _proofFuture = widget.service.fetchPaymentProof(_request.id);
    }
  }

  @override
  void dispose() {
    _adminNotesController.dispose();
    _feeController.dispose();
    _waiverController.dispose();
    _orController.dispose();
    _paymentNoteController.dispose();
    super.dispose();
  }

  String _errorMessage(Object error) => error is ApiException
      ? error.message
      : 'The action could not be completed. Check your connection and try again.';

  void _showMessage(String message, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: error ? Colors.red.shade700 : const Color(0xFF047857),
      ),
    );
  }

  String _requesterName() {
    if (_request.requesterName?.trim().isNotEmpty == true) {
      return _request.requesterName!.trim();
    }
    if (_request.walkinName?.trim().isNotEmpty == true) {
      return _request.walkinName!.trim();
    }
    return 'Resident';
  }

  Future<void> _saveRequestReview() async {
    final notes = _adminNotesController.text.trim();
    if (_selectedStatus == 'REJECTED' && notes.isEmpty) {
      _showMessage('Enter a reason before rejecting the request.', error: true);
      return;
    }
    String? feeAmount;
    if (_editFeeAssessment) {
      feeAmount = _feeController.text.trim();
      if (feeAmount.isEmpty) {
        _showMessage(
          'Enter a fee amount or turn off fee assessment.',
          error: true,
        );
        return;
      }
      final parsedFee = double.tryParse(feeAmount);
      if (parsedFee == null || !parsedFee.isFinite || parsedFee < 0) {
        _showMessage('Enter a valid non-negative fee amount.', error: true);
        return;
      }
      if (parsedFee == 0 &&
          _waiverController.text.trim().isEmpty &&
          !_request.isStatutoryExempt) {
        _showMessage(
          'A written reason is required when waiving the fee.',
          error: true,
        );
        return;
      }
    }

    setState(() => _isUpdating = true);
    try {
      final updated = await widget.service.reviewAdminDocumentRequest(
        requestId: _request.id,
        status: _selectedStatus,
        adminNotes: notes,
        orNumber: _orController.text,
        feeAmount: feeAmount,
        paymentMethod: _selectedPaymentMethod,
        feeWaiverReason: _editFeeAssessment ? _waiverController.text : null,
      );
      if (!mounted) return;
      setState(() {
        _request = updated;
        _selectedStatus = updated.status;
        _selectedPaymentMethod = updated.paymentMethod ?? '';
        _adminNotesController.text = updated.adminNotes ?? '';
        _orController.text = updated.orNumber ?? '';
        _feeController.text = updated.feeAmount?.toStringAsFixed(2) ?? '';
        _waiverController.text = updated.feeWaiverReason ?? '';
        _editFeeAssessment = false;
      });
      _showMessage('Request review saved.');
    } catch (error) {
      if (mounted) _showMessage(_errorMessage(error), error: true);
    } finally {
      if (mounted) setState(() => _isUpdating = false);
    }
  }

  Future<void> _reviewPayment(String status) async {
    final isRejecting = status == 'REJECTED';
    final note = _paymentNoteController.text.trim();
    if (isRejecting && note.isEmpty) {
      _showMessage(
        'Enter a reason before rejecting the transfer.',
        error: true,
      );
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(isRejecting ? 'Reject e-payment?' : 'Verify e-payment?'),
        content: Text(
          isRejecting
              ? 'The resident will need to submit corrected transfer details.'
              : 'Confirm the transfer against the barangay receiving account before verifying.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            style: FilledButton.styleFrom(
              backgroundColor: isRejecting
                  ? Colors.red.shade700
                  : const Color(0xFF047857),
            ),
            child: Text(isRejecting ? 'Reject transfer' : 'Verify transfer'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _isUpdating = true);
    try {
      final updated = await widget.service.reviewAdminPayment(
        requestId: _request.id,
        status: status,
        note: note,
        orNumber: _orController.text,
      );
      if (!mounted) return;
      setState(() {
        _request = updated;
        _paymentNoteController.clear();
        _orController.text = updated.orNumber ?? '';
      });
      _showMessage(
        isRejecting ? 'Transfer reference rejected.' : 'Transfer verified.',
      );
    } catch (error) {
      if (mounted) _showMessage(_errorMessage(error), error: true);
    } finally {
      if (mounted) setState(() => _isUpdating = false);
    }
  }

  Widget _detail(String label, String? value) {
    final cleaned = value?.trim();
    if (cleaned == null || cleaned.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 128,
            child: Text(
              label,
              style: const TextStyle(color: Color(0xFF64748B), fontSize: 13),
            ),
          ),
          Expanded(
            child: Text(
              cleaned,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionCard({required String title, required Widget child}) {
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 12),
            child,
          ],
        ),
      ),
    );
  }

  Widget _paymentProofCard() {
    final url = _request.paymentProofUrl;
    if (url == null || url.isEmpty) {
      return _sectionCard(
        title: 'Payment proof',
        child: const Text('No payment proof image was submitted.'),
      );
    }
    return _sectionCard(
      title: 'Resident transfer proof',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _detail('Reference number', _request.paymentReference),
          _detail(
            'Payment method',
            _request.paymentMethod?.replaceAll('_', ' '),
          ),
          _detail('Recipient', _request.paymentRecipientName),
          _detail('Account / number', _request.paymentRecipientIdentifier),
          _detail(
            'Transaction time',
            _request.paymentTransactedAt?.toLocal().toString(),
          ),
          const SizedBox(height: 8),
          FutureBuilder<Uint8List>(
            future: _proofFuture,
            builder: (context, snapshot) {
              if (snapshot.hasError) {
                return Column(
                  children: [
                    const Text(
                      'Could not load private receipt image.',
                      style: TextStyle(color: Colors.red),
                    ),
                    TextButton.icon(
                      onPressed: () => setState(
                        () => _proofFuture = widget.service.fetchPaymentProof(
                          _request.id,
                        ),
                      ),
                      icon: const Icon(Icons.refresh),
                      label: const Text('Try again'),
                    ),
                  ],
                );
              }
              if (!snapshot.hasData) {
                return const SizedBox(
                  height: 180,
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              return ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: InteractiveViewer(
                  minScale: 1,
                  maxScale: 4,
                  child: Image.memory(
                    snapshot.data!,
                    height: 260,
                    width: double.infinity,
                    fit: BoxFit.contain,
                    errorBuilder: (_, _, _) => const SizedBox(
                      height: 180,
                      child: Center(
                        child: Text(
                          'The receipt image could not be displayed.',
                        ),
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 8),
          _detail(
            'Payment status',
            _request.paymentStatus.replaceAll('_', ' '),
          ),
          if (_request.paymentReviewNote?.isNotEmpty == true)
            _detail('Previous review note', _request.paymentReviewNote),
        ],
      ),
    );
  }

  Widget _paymentReviewActions() {
    if (_request.paymentStatus.toUpperCase() != 'PENDING_VERIFICATION') {
      return const SizedBox.shrink();
    }
    return _sectionCard(
      title: 'Review electronic transfer',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Compare the reference, amount, recipient, and transaction time with the official barangay receiving account.',
            style: TextStyle(color: Color(0xFF475569), fontSize: 13),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _paymentNoteController,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: 'Review note (required when rejecting)',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _isUpdating
                      ? null
                      : () => _reviewPayment('REJECTED'),
                  icon: const Icon(Icons.close_rounded),
                  label: const Text('Reject'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.red.shade700,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton.icon(
                  onPressed: _isUpdating
                      ? null
                      : () => _reviewPayment('VERIFIED'),
                  icon: const Icon(Icons.verified_rounded),
                  label: const Text('Verify transfer'),
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFF047857),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _reviewForm() {
    final feeAssessmentLabel = _request.feeAssessmentStatus.replaceAll(
      '_',
      ' ',
    );
    return _sectionCard(
      title: 'Request processing',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _detail('Fee assessment', feeAssessmentLabel),
          if (_request.feeAssessedByName?.isNotEmpty == true)
            _detail('Assessed by', _request.feeAssessedByName),
          SwitchListTile.adaptive(
            contentPadding: EdgeInsets.zero,
            title: const Text('Record or update fee assessment'),
            subtitle: const Text(
              'A written reason is required for a zero-fee waiver.',
            ),
            value: _editFeeAssessment,
            onChanged: _isUpdating
                ? null
                : (value) => setState(() => _editFeeAssessment = value),
          ),
          if (_editFeeAssessment) ...[
            TextField(
              controller: _feeController,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(
                labelText: 'Fee amount (PHP)',
                prefixText: '₱ ',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _waiverController,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Fee waiver justification (for zero fee)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 10),
          ],
          DropdownButtonFormField<String>(
            initialValue: _selectedPaymentMethod,
            decoration: const InputDecoration(
              labelText: 'Collection method',
              border: OutlineInputBorder(),
            ),
            items: const [
              DropdownMenuItem(
                value: '',
                child: Text('Let resident select e-payment'),
              ),
              DropdownMenuItem(
                value: 'CASH',
                child: Text('Cash at barangay hall'),
              ),
              DropdownMenuItem(value: 'GCASH', child: Text('GCash')),
              DropdownMenuItem(value: 'MAYA', child: Text('Maya')),
              DropdownMenuItem(value: 'BANK', child: Text('Bank transfer')),
              DropdownMenuItem(
                value: 'OTHER',
                child: Text('Other electronic transfer'),
              ),
            ],
            onChanged: _isUpdating
                ? null
                : (value) =>
                      setState(() => _selectedPaymentMethod = value ?? ''),
          ),
          const SizedBox(height: 10),
          DropdownButtonFormField<String>(
            initialValue: _selectedStatus,
            decoration: const InputDecoration(
              labelText: 'Request status',
              border: OutlineInputBorder(),
            ),
            items: const [
              DropdownMenuItem(value: 'PROCESSING', child: Text('Processing')),
              DropdownMenuItem(
                value: 'READY_FOR_PICKUP',
                child: Text('Ready for pickup'),
              ),
              DropdownMenuItem(
                value: 'RELEASED',
                child: Text('Released to resident'),
              ),
              DropdownMenuItem(value: 'REJECTED', child: Text('Rejected')),
            ],
            onChanged: _isUpdating
                ? null
                : (value) =>
                      setState(() => _selectedStatus = value ?? 'PROCESSING'),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _orController,
            decoration: const InputDecoration(
              labelText: 'Official receipt number',
              helperText: 'Required before releasing a paid document.',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _adminNotesController,
            minLines: 2,
            maxLines: 4,
            decoration: InputDecoration(
              labelText: _selectedStatus == 'REJECTED'
                  ? 'Rejection reason (required)'
                  : 'Resident-facing note (optional)',
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: _isUpdating ? null : _saveRequestReview,
            icon: _isUpdating
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.save_outlined),
            label: const Text('Save review'),
            style: FilledButton.styleFrom(
              minimumSize: const Size.fromHeight(50),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final purok = _request.purok?.isNotEmpty == true
        ? _request.purok
        : _request.walkinPurok;
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        title: Text('Request #${_request.id}'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _sectionCard(
            title: _request.documentType,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _detail('Resident', _requesterName()),
                _detail('Purok', purok),
                _detail('Purpose', _request.purpose),
                _detail('Urgency', _request.urgencyTag),
                _detail('Requested', _request.formattedRequestedDate),
                _detail('Current status', _request.status.replaceAll('_', ' ')),
                _detail('Fee', _request.formattedFee),
                _detail('Payment', _request.paymentStatus.replaceAll('_', ' ')),
              ],
            ),
          ),
          if (_request.hasOfferingSnapshot)
            _sectionCard(
              title: context.tr('Published requirements and fee'),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _detail(
                    context.tr('Published fee'),
                    _request.publishedFeeAmountSnapshot == null
                        ? context.tr('Confirm with Barangay staff')
                        : _request.publishedFeeAmountSnapshot == 0
                        ? context.tr('No fee')
                        : '₱${_request.publishedFeeAmountSnapshot!.toStringAsFixed(2)}',
                  ),
                  if (_request.requirementsSnapshot.isEmpty)
                    _detail(
                      context.tr('Requirements'),
                      context.tr('No requirements were listed.'),
                    )
                  else
                    _detail(
                      context.tr('Requirements'),
                      _request.requirementsSnapshot
                          .map((requirement) => '• ${context.tr(requirement)}')
                          .join('\n'),
                    ),
                  _detail(
                    context.tr('Additional details'),
                    _request.offeringDetailsSnapshot,
                  ),
                  Text(
                    context.tr(
                      'These are the published details saved when the request was filed. The fee assessment below records the final amount.',
                    ),
                    style: const TextStyle(
                      color: Color(0xFF64748B),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          _paymentProofCard(),
          _paymentReviewActions(),
          _reviewForm(),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
