import 'package:flutter/material.dart';

import '../core/localization/app_language.dart';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../core/theme/app_colors.dart';
import '../models/equipment_borrow_request_model.dart';
import '../services/auth_service.dart';
import '../services/equipment_borrow_service.dart';
import '../services/storage_service.dart';
import '../widgets/offline_snapshot_banner.dart';

class EquipmentBorrowingScreen extends StatefulWidget {
  final EquipmentBorrowService? equipmentBorrowService;
  final bool isAdmin;

  const EquipmentBorrowingScreen({
    super.key,
    this.equipmentBorrowService,
    this.isAdmin = false,
  });

  @override
  State<EquipmentBorrowingScreen> createState() =>
      _EquipmentBorrowingScreenState();
}

class _EquipmentBorrowingScreenState extends State<EquipmentBorrowingScreen> {
  EquipmentBorrowService? _service;
  List<EquipmentBorrowRequestModel> _requests = [];
  String _itemType = EquipmentBorrowRequestModel.defaultItemTypes.first;
  final _quantityController = TextEditingController(text: '1');
  final _borrowDateController = TextEditingController();
  final _returnDateController = TextEditingController();
  final _timeSlotController = TextEditingController(
    text: '08:00 AM - 05:00 PM',
  );
  final _purposeController = TextEditingController();
  final Map<int, TextEditingController> _adminNoteControllers = {};

  bool _isLoading = true;
  bool _isSubmitting = false;
  int? _reviewingId;
  bool _showingOfflineSnapshot = false;
  bool _couldNotRefreshRequests = false;
  bool _requestsLoadFailed = false;
  DateTime? _offlineSnapshotSavedAt;

  @override
  void initState() {
    super.initState();
    final tomorrow = DateTime.now().add(const Duration(days: 1));
    final formattedTomorrow = _formatDate(tomorrow);
    _borrowDateController.text = formattedTomorrow;
    _returnDateController.text = formattedTomorrow;
    _initialize();
  }

  @override
  void dispose() {
    _quantityController.dispose();
    _borrowDateController.dispose();
    _returnDateController.dispose();
    _timeSlotController.dispose();
    _purposeController.dispose();
    for (final controller in _adminNoteControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  String _formatDate(DateTime date) {
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '${date.year}-$month-$day';
  }

  Future<void> _pickDate(TextEditingController controller) async {
    final now = DateTime.now();
    final initial = DateTime.tryParse(controller.text.trim()) ?? now;
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(now.year - 1),
      lastDate: DateTime(now.year + 2),
    );
    if (picked != null && mounted) {
      setState(() => controller.text = _formatDate(picked));
    }
  }

  Future<void> _initialize() async {
    _service = widget.equipmentBorrowService;
    if (_service == null) {
      final storage = await StorageService.init();
      final apiClient = ApiClient();
      AuthService(apiClient: apiClient, storageService: storage);
      _service = EquipmentBorrowService(
        apiClient: apiClient,
        storageService: storage,
      );
    }
    await _loadRequests();
  }

  Future<void> _loadRequests() async {
    try {
      final requests = await _service!.fetchRequests();
      if (mounted) {
        setState(() {
          _requests = requests;
          _requestsLoadFailed = false;
          _showingOfflineSnapshot = _service!.lastRequestsUsedOfflineSnapshot;
          _couldNotRefreshRequests =
              _service!.lastFetchFailed &&
              !_service!.lastRequestsUsedOfflineSnapshot;
          _offlineSnapshotSavedAt = _service!.lastSnapshotSavedAt;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _requestsLoadFailed = true;
          _couldNotRefreshRequests = error is NetworkException;
          _showingOfflineSnapshot = false;
        });
        _showMessage(
          context.tr('Could not load equipment borrowing requests.'),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _submitRequest() async {
    final purpose = _purposeController.text.trim();
    final borrowDate = _borrowDateController.text.trim();
    final returnDate = _returnDateController.text.trim();
    final quantity = int.tryParse(_quantityController.text.trim()) ?? 0;

    if (borrowDate.isEmpty || returnDate.isEmpty) {
      _showMessage(context.tr('Please select both borrow and return dates.'));
      return;
    }
    if (returnDate.compareTo(borrowDate) < 0) {
      _showMessage(
        context.tr('Return date must be on or after the borrow date.'),
      );
      return;
    }
    if (quantity < 1) {
      _showMessage(context.tr('Quantity must be at least 1.'));
      return;
    }
    if (purpose.isEmpty || _isSubmitting) {
      if (purpose.isEmpty) {
        _showMessage(context.tr('Please provide the purpose for borrowing.'));
      }
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      await _service!.createRequest(
        itemType: _itemType,
        quantity: quantity,
        borrowDate: borrowDate,
        returnDate: returnDate,
        timeSlot: _timeSlotController.text.trim(),
        purpose: purpose,
      );
      _purposeController.clear();
      _quantityController.text = '1';
      await _loadRequests();
      if (mounted) {
        _showMessage(
          context.tr('Equipment borrowing request submitted for review.'),
        );
      }
    } catch (error) {
      if (mounted) {
        final String message;
        if (error is NetworkException) {
          message = context.tr(
            'We could not confirm whether the server received your submission. Check your requests after reconnecting before trying again.',
          );
        } else if (error is ApiException && error.message.trim().isNotEmpty) {
          message = context.tr(error.message.trim());
        } else {
          message = context.tr('Could not submit your borrowing request.');
        }
        _showMessage(message);
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  Future<void> _reviewRequest(
    EquipmentBorrowRequestModel request,
    String nextStatus,
  ) async {
    final noteController = _adminNoteControllers.putIfAbsent(
      request.id,
      () => TextEditingController(text: request.adminNotes),
    );
    final notes = noteController.text.trim();
    if (nextStatus == 'DECLINED' && notes.isEmpty) {
      _showMessage(
        context.tr('Add a reason before declining this borrowing request.'),
      );
      return;
    }

    setState(() => _reviewingId = request.id);
    try {
      await _service!.reviewRequest(
        requestId: request.id,
        status: nextStatus,
        adminNotes: notes,
      );
      await _loadRequests();
      if (mounted) {
        _showMessage(context.tr('Borrowing request updated.'));
      }
    } catch (_) {
      if (mounted) {
        _showMessage(context.tr('Could not update this borrowing request.'));
      }
    } finally {
      if (mounted) setState(() => _reviewingId = null);
    }
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: Text(context.tr('Equipment & Facility Borrowing')),
        foregroundColor: AppColors.textPrimary,
        backgroundColor: Colors.white,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadRequests,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (_showingOfflineSnapshot)
                      OfflineSnapshotBanner(savedAt: _offlineSnapshotSavedAt),
                    if (_couldNotRefreshRequests && !_showingOfflineSnapshot)
                      const OfflineSnapshotBanner(
                        message:
                            'Could not update your requests. Reconnect and refresh before submitting again.',
                      ),
                    if (!widget.isAdmin) _buildResidentFormCard(context),
                    if (!widget.isAdmin) const SizedBox(height: 20),
                    Text(
                      context.tr(
                        widget.isAdmin
                            ? 'Borrowing requests for your barangay'
                            : 'Your borrowing requests',
                      ),
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    if (_requests.isEmpty && _requestsLoadFailed)
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(18),
                          child: Text(
                            context.tr(
                              'Could not load your request history. Refresh and try again.',
                            ),
                          ),
                        ),
                      )
                    else if (_requests.isEmpty)
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(18),
                          child: Text(
                            context.tr(
                              'No equipment borrowing requests found.',
                            ),
                          ),
                        ),
                      ),
                    ..._requests.map(
                      (request) => _buildRequestCard(context, request),
                    ),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildResidentFormCard(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.tr('Request Equipment or Facility'),
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              context.tr(
                'Borrow barangay chairs, tents, tables, sound systems, or reserve community facilities. Requests are reviewed manually by barangay staff.',
              ),
              style: const TextStyle(color: AppColors.textMuted, height: 1.35),
            ),
            const SizedBox(height: 14),
            DropdownButtonFormField<String>(
              initialValue: _itemType,
              decoration: InputDecoration(
                labelText: context.tr('Item or facility'),
              ),
              items: EquipmentBorrowRequestModel.defaultItemTypes
                  .map(
                    (type) => DropdownMenuItem(
                      value: type,
                      child: Text(context.tr(type)),
                    ),
                  )
                  .toList(),
              onChanged: (value) {
                if (value != null) {
                  setState(() => _itemType = value);
                }
              },
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _quantityController,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: context.tr('Quantity'),
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _borrowDateController,
                    decoration: InputDecoration(
                      labelText: context.tr('Borrow date'),
                      border: const OutlineInputBorder(),
                      suffixIcon: IconButton(
                        icon: const Icon(Icons.calendar_today_outlined),
                        tooltip: context.tr('Borrow date'),
                        onPressed: () => _pickDate(_borrowDateController),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                    controller: _returnDateController,
                    decoration: InputDecoration(
                      labelText: context.tr('Return date'),
                      border: const OutlineInputBorder(),
                      suffixIcon: IconButton(
                        icon: const Icon(Icons.calendar_today_outlined),
                        tooltip: context.tr('Return date'),
                        onPressed: () => _pickDate(_returnDateController),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _timeSlotController,
              decoration: InputDecoration(
                labelText: context.tr('Time slot'),
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _purposeController,
              maxLength: 2000,
              maxLines: 3,
              decoration: InputDecoration(
                labelText: context.tr('Purpose'),
                alignLabelWithHint: true,
                border: const OutlineInputBorder(),
              ),
            ),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _isSubmitting ? null : _submitRequest,
                icon: _isSubmitting
                    ? const SizedBox.square(
                        dimension: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.send_outlined),
                label: Text(
                  _isSubmitting
                      ? context.tr('Submitting…')
                      : context.tr('Submit Borrowing Request'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRequestCard(
    BuildContext context,
    EquipmentBorrowRequestModel request,
  ) {
    final canReview =
        widget.isAdmin && (request.isPending || request.isApproved);
    final noteController = canReview
        ? _adminNoteControllers.putIfAbsent(
            request.id,
            () => TextEditingController(text: request.adminNotes),
          )
        : null;

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    '${context.tr(request.itemType)} (x${request.quantity})',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: request.statusBadgeBgColor,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    context.tr(request.statusDisplay),
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: request.statusBadgeTextColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            if (widget.isAdmin)
              Text(
                request.residentName,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            Text(
              request.formattedSchedule,
              style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
            ),
            const SizedBox(height: 8),
            Text(request.purpose),
            if (request.adminNotes.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                '${context.tr('Admin remarks: ')}${request.adminNotes}',
                style: const TextStyle(color: AppColors.textMuted),
              ),
            ],
            if (canReview && noteController != null) ...[
              const SizedBox(height: 12),
              TextField(
                controller: noteController,
                maxLines: 2,
                decoration: InputDecoration(
                  labelText: context.tr('Admin remarks'),
                  border: const OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (request.isPending) ...[
                    FilledButton(
                      onPressed: _reviewingId == request.id
                          ? null
                          : () => _reviewRequest(request, 'APPROVED'),
                      child: Text(context.tr('Approve')),
                    ),
                    OutlinedButton(
                      onPressed: _reviewingId == request.id
                          ? null
                          : () => _reviewRequest(request, 'DECLINED'),
                      child: Text(context.tr('Decline')),
                    ),
                  ],
                  if (request.isApproved)
                    FilledButton(
                      onPressed: _reviewingId == request.id
                          ? null
                          : () => _reviewRequest(request, 'RETURNED'),
                      child: Text(context.tr('Mark Returned')),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
