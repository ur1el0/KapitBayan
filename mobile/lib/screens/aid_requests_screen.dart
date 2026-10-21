import 'package:flutter/material.dart';

import '../core/network/api_client.dart';
import '../core/theme/app_colors.dart';
import '../core/localization/app_language.dart';
import '../services/aid_request_service.dart';
import '../services/storage_service.dart';

class AidRequestsScreen extends StatefulWidget {
  final AidRequestService? aidRequestService;

  const AidRequestsScreen({super.key, this.aidRequestService});

  @override
  State<AidRequestsScreen> createState() => _AidRequestsScreenState();
}

class _AidRequestsScreenState extends State<AidRequestsScreen> {
  static const _assistanceTypes = [
    'Medical assistance',
    'Food assistance',
    'Educational assistance',
    'Emergency assistance',
    'Other barangay assistance',
  ];

  AidRequestService? _service;
  List<Map<String, dynamic>> _requests = [];
  final _reasonController = TextEditingController();
  String _assistanceType = _assistanceTypes.first;
  bool _isLoading = true;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  Future<void> _initialize() async {
    _service = widget.aidRequestService;
    if (_service == null) {
      final storage = await StorageService.init();
      final apiClient = ApiClient();
      final token = storage.getAccessToken();
      if (token != null) apiClient.setAuthCredentials(accessToken: token);
      _service = AidRequestService(apiClient: apiClient);
    }
    await _loadRequests();
  }

  Future<void> _loadRequests() async {
    try {
      final requests = await _service!.fetchRequests();
      if (mounted) setState(() => _requests = requests);
    } catch (_) {
      if (mounted) _showMessage(context.tr('Could not load assistance requests.'));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _submitRequest() async {
    final reason = _reasonController.text.trim();
    if (reason.isEmpty || _isSubmitting) return;
    setState(() => _isSubmitting = true);
    try {
      await _service!.createRequest(
        assistanceType: _assistanceType,
        reason: reason,
      );
      _reasonController.clear();
      await _loadRequests();
      if (mounted) _showMessage(context.tr('Request submitted for barangay staff review.'));
    } catch (_) {
      if (mounted) _showMessage(context.tr('Could not submit your assistance request.'));
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  String _statusLabel(BuildContext context, String status) {
    switch (status) {
      case 'UNDER_REVIEW':
        return context.tr('Under review');
      case 'APPROVED':
        return context.tr('Approved');
      case 'DECLINED':
        return context.tr('Declined');
      default:
        return context.tr('Pending review');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: Text(context.tr('Barangay Assistance')),
        foregroundColor: AppColors.textPrimary,
        backgroundColor: Colors.white,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadRequests,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            context.tr('Request assistance'),
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            context.tr('Barangay staff will review your request manually. Submission does not guarantee approval.'),
                            style: TextStyle(
                              color: AppColors.textMuted,
                              height: 1.35,
                            ),
                          ),
                          const SizedBox(height: 14),
                          DropdownButtonFormField<String>(
                            initialValue: _assistanceType,
                            decoration: InputDecoration(
                              labelText: context.tr('Type of assistance'),
                            ),
                            items: _assistanceTypes
                                .map(
                                  (type) => DropdownMenuItem(
                                    value: type,
                                    child: Text(context.tr(type)),
                                  ),
                                )
                                .toList(),
                            onChanged: (value) {
                              if (value != null) {
                                setState(() => _assistanceType = value);
                              }
                            },
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: _reasonController,
                            maxLength: 2000,
                            maxLines: 4,
                            decoration: InputDecoration(
                              labelText: context.tr('Reason for request'),
                              alignLabelWithHint: true,
                              border: OutlineInputBorder(),
                            ),
                          ),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton.icon(
                              onPressed: _isSubmitting ? null : _submitRequest,
                              icon: _isSubmitting
                                  ? const SizedBox.square(
                                      dimension: 16,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Icon(Icons.send_outlined),
                              label: Text(
                                _isSubmitting
                                    ? context.tr('Submitting…')
                                    : context.tr('Submit for review'),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    context.tr('Your requests'),
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  if (_requests.isEmpty)
                    Card(
                      child: Padding(
                        padding: EdgeInsets.all(18),
                        child: Text(context.tr('No assistance requests have been submitted.')),
                      ),
                    ),
                  ..._requests.map(
                    (request) => Card(
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
                                    request['assistance_type']?.toString() ??
                                        context.tr('Assistance request'),
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                                Text(
                                  _statusLabel(context,
                                    request['status']?.toString() ?? 'PENDING',
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(request['reason']?.toString() ?? ''),
                            if ((request['staff_notes']?.toString() ?? '')
                                .isNotEmpty) ...[
                              const SizedBox(height: 8),
                              Text(
                                '${context.tr('Staff note: ')}${request['staff_notes']}',
                                style: const TextStyle(
                                  color: AppColors.textMuted,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
