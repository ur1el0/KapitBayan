import 'package:flutter/material.dart';

import '../core/localization/app_language.dart';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../core/theme/app_colors.dart';
import '../models/admin_resident_model.dart';
import '../services/admin_resident_service.dart';
import '../services/auth_service.dart';
import '../services/storage_service.dart';
import '../widgets/resident_evidence_viewer_dialog.dart';

class AdminResidentsScreen extends StatefulWidget {
  final int initialTabIndex;

  const AdminResidentsScreen({super.key, this.initialTabIndex = 0});

  @override
  State<AdminResidentsScreen> createState() => _AdminResidentsScreenState();
}

class _AdminResidentsScreenState extends State<AdminResidentsScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  AdminResidentService? _service;
  bool _isInitializing = true;
  bool _loadingVerified = false;
  bool _loadingPending = false;
  String? _verifiedError;
  String? _pendingError;
  List<AdminResidentModel> _verifiedResidents = [];
  List<AdminResidentModel> _pendingResidents = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: 2,
      vsync: this,
      initialIndex: widget.initialTabIndex == 1 ? 1 : 0,
    );
    _initialize();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _initialize() async {
    try {
      final storage = await StorageService.init();
      final apiClient = ApiClient();
      final authService = AuthService(
        apiClient: apiClient,
        storageService: storage,
      );
      _service = AdminResidentService(
        apiClient: apiClient,
        authService: authService,
      );
      await Future.wait([_loadVerified(), _loadPending()]);
    } catch (error) {
      if (mounted) {
        setState(() {
          _verifiedError = _friendlyError(error);
          _pendingError = _friendlyError(error);
        });
      }
    } finally {
      if (mounted) setState(() => _isInitializing = false);
    }
  }

  String _friendlyError(Object error) => error is ApiException
      ? error.message
      : 'Could not load residents. Check your connection and try again.';

  Future<void> _loadVerified() async {
    final service = _service;
    if (service == null) return;
    if (mounted) setState(() => _loadingVerified = true);
    try {
      final residents = await service.fetchVerifiedResidents();
      if (!mounted) return;
      setState(() {
        _verifiedResidents = residents;
        _verifiedError = null;
      });
    } catch (error) {
      if (mounted) setState(() => _verifiedError = _friendlyError(error));
    } finally {
      if (mounted) setState(() => _loadingVerified = false);
    }
  }

  Future<void> _loadPending() async {
    final service = _service;
    if (service == null) return;
    if (mounted) setState(() => _loadingPending = true);
    try {
      final residents = await service.fetchPendingResidents();
      if (!mounted) return;
      setState(() {
        _pendingResidents = residents;
        _pendingError = null;
      });
    } catch (error) {
      if (mounted) setState(() => _pendingError = _friendlyError(error));
    } finally {
      if (mounted) setState(() => _loadingPending = false);
    }
  }

  Future<void> _openResident(AdminResidentModel resident) async {
    final service = _service;
    if (service == null) return;
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) =>
            AdminResidentDetailsScreen(resident: resident, service: service),
      ),
    );
    if (changed == true) {
      await Future.wait([_loadVerified(), _loadPending()]);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        title: Text(context.tr('Residents')),
        actions: [
          IconButton(
            tooltip: 'Refresh residents',
            onPressed: _isInitializing
                ? null
                : () => Future.wait([_loadVerified(), _loadPending()]),
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.white,
          tabs: [
            Tab(text: context.tr('Verified residents')),
            Tab(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(context.tr('Pending verification')),
                  if (_pendingResidents.isNotEmpty) ...[
                    const SizedBox(width: 7),
                    CircleAvatar(
                      radius: 10,
                      backgroundColor: Colors.white,
                      child: Text(
                        '${_pendingResidents.length}',
                        style: const TextStyle(
                          color: AppColors.primaryNavy,
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
      body: _isInitializing
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabController,
              children: [
                _ResidentList(
                  residents: _verifiedResidents,
                  isLoading: _loadingVerified,
                  error: _verifiedError,
                  emptyTitle: 'No verified residents found',
                  emptyMessage: 'Verified resident records will appear here.',
                  onRefresh: _loadVerified,
                  onTap: _openResident,
                ),
                _ResidentList(
                  residents: _pendingResidents,
                  isLoading: _loadingPending,
                  error: _pendingError,
                  emptyTitle: 'No registrations awaiting review',
                  emptyMessage: 'New resident registrations will appear here.',
                  onRefresh: _loadPending,
                  onTap: _openResident,
                  pending: true,
                ),
              ],
            ),
    );
  }
}

class _ResidentList extends StatelessWidget {
  final List<AdminResidentModel> residents;
  final bool isLoading;
  final String? error;
  final String emptyTitle;
  final String emptyMessage;
  final Future<void> Function() onRefresh;
  final ValueChanged<AdminResidentModel> onTap;
  final bool pending;

  const _ResidentList({
    required this.residents,
    required this.isLoading,
    required this.error,
    required this.emptyTitle,
    required this.emptyMessage,
    required this.onRefresh,
    required this.onTap,
    this.pending = false,
  });

  @override
  Widget build(BuildContext context) {
    if (isLoading && residents.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (error != null && residents.isEmpty) {
      return _RetryState(message: error!, onRetry: onRefresh);
    }
    if (residents.isEmpty) {
      return RefreshIndicator(
        onRefresh: onRefresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            const SizedBox(height: 120),
            const Icon(Icons.people_outline, size: 48, color: Colors.blueGrey),
            const SizedBox(height: 12),
            Text(
              emptyTitle,
              textAlign: TextAlign.center,
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
            ),
            const SizedBox(height: 6),
            Text(
              emptyMessage,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFF64748B)),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView.separated(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        itemCount: residents.length + (error == null ? 0 : 1),
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (context, index) {
          if (index == 0 && error != null) {
            return Material(
              color: const Color(0xFFFEF2F2),
              borderRadius: BorderRadius.circular(12),
              child: ListTile(
                title: Text(error!, style: const TextStyle(color: Colors.red)),
                trailing: IconButton(
                  onPressed: onRefresh,
                  icon: const Icon(Icons.refresh),
                ),
              ),
            );
          }
          final resident = residents[index - (error == null ? 0 : 1)];
          return Card(
            margin: EdgeInsets.zero,
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: const BorderSide(color: Color(0xFFE2E8F0)),
            ),
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 8,
              ),
              leading: CircleAvatar(
                backgroundColor: pending
                    ? const Color(0xFFFFF7ED)
                    : const Color(0xFFE0F2FE),
                child: Icon(
                  pending ? Icons.person_search_rounded : Icons.person_rounded,
                  color: pending ? const Color(0xFFC2410C) : Colors.blue,
                ),
              ),
              title: Text(
                resident.fullName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  [
                    if (resident.purok?.isNotEmpty == true)
                      'Purok ${resident.purok}',
                    if (resident.email.isNotEmpty) resident.email,
                  ].join(' • '),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => onTap(resident),
            ),
          );
        },
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

class AdminResidentDetailsScreen extends StatefulWidget {
  final AdminResidentModel resident;
  final AdminResidentService service;

  const AdminResidentDetailsScreen({
    super.key,
    required this.resident,
    required this.service,
  });

  @override
  State<AdminResidentDetailsScreen> createState() =>
      _AdminResidentDetailsScreenState();
}

class _AdminResidentDetailsScreenState
    extends State<AdminResidentDetailsScreen> {
  bool _isUpdating = false;

  Future<void> _verify() async {
    final approved = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Approve resident?'),
        content: Text(
          'This will verify ${widget.resident.fullName} and activate resident services.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Approve'),
          ),
        ],
      ),
    );
    if (approved != true || !mounted) return;
    setState(() => _isUpdating = true);
    try {
      await widget.service.verifyResident(widget.resident.id);
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Resident verified.')));
      Navigator.of(context).pop(true);
    } catch (error) {
      if (mounted) _showError(error);
    } finally {
      if (mounted) setState(() => _isUpdating = false);
    }
  }

  Future<void> _reject() async {
    final reasonController = TextEditingController();
    final reason = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Reject registration'),
        content: TextField(
          controller: reasonController,
          autofocus: true,
          minLines: 2,
          maxLines: 4,
          maxLength: 1000,
          decoration: const InputDecoration(
            labelText: 'Reason for rejection',
            hintText: 'Explain why this registration cannot be approved.',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          FilledButton.tonal(
            onPressed: () =>
                Navigator.pop(dialogContext, reasonController.text),
            child: const Text('Continue'),
          ),
        ],
      ),
    );
    reasonController.dispose();
    if (!mounted || reason == null) return;
    if (reason.trim().isEmpty) {
      _showError('Enter a reason before rejecting the registration.');
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Confirm rejection'),
        content: const Text(
          'Rejecting will remove this pending account and revoke its active sessions.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red.shade700),
            child: const Text('Reject registration'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _isUpdating = true);
    try {
      await widget.service.rejectResident(
        residentId: widget.resident.id,
        reason: reason,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Registration rejected.')));
      Navigator.of(context).pop(true);
    } catch (error) {
      if (mounted) _showError(error);
    } finally {
      if (mounted) setState(() => _isUpdating = false);
    }
  }

  void _showError(Object error) {
    final message = error is ApiException
        ? error.message
        : 'The action could not be completed. Check your connection and try again.';
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red.shade700),
    );
  }

  Future<void> _viewEvidence({
    required String title,
    required String? path,
    required String fieldName,
  }) async {
    if (path == null || path.isEmpty) return;
    await ResidentEvidenceViewerDialog.show(
      context,
      title: title,
      loadImage: () =>
          widget.service.fetchEvidence(widget.resident.id, fieldName),
    );
  }

  Widget _detail(String label, String? value) {
    final display = value?.trim();
    if (display == null || display.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(
              label,
              style: const TextStyle(color: Color(0xFF64748B), fontSize: 13),
            ),
          ),
          Expanded(
            child: Text(
              display,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final resident = widget.resident;
    final evidence = <({String title, String? path, String field})>[
      (
        title: 'PhilSys National ID',
        path: resident.philsysIdPhoto,
        field: 'philsys_id_photo',
      ),
      (
        title: resident.secondaryIdType?.isNotEmpty == true
            ? resident.secondaryIdType!
            : 'Secondary ID',
        path: resident.secondaryIdPhoto,
        field: 'secondary_id_photo',
      ),
      (
        title: resident.utilityBillingType?.isNotEmpty == true
            ? resident.utilityBillingType!
            : 'Utility billing proof',
        path: resident.utilityBillingPhoto,
        field: 'utility_billing_photo',
      ),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        title: Text(
          resident.fullName,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            elevation: 0,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(
                        Icons.person_outline,
                        color: AppColors.primaryNavy,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          resident.fullName,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                      _StatusChip(verified: resident.isVerified),
                    ],
                  ),
                  const Divider(height: 24),
                  _detail('Username', resident.username),
                  _detail('Email', resident.email),
                  _detail('Birth date', resident.birthDate),
                  _detail('Contact number', resident.contactNumber),
                  _detail('Purok', resident.purok),
                  _detail('Address', resident.addressDetails),
                  _detail('PhilSys ID number', resident.philsysIdNumber),
                  _detail(
                    'Voter status',
                    resident.voterStatus ? 'Registered' : 'Not registered',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            elevation: 0,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Identity and residency evidence',
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'These files are loaded through the authenticated, barangay-scoped media endpoint.',
                    style: TextStyle(color: Color(0xFF64748B), fontSize: 12),
                  ),
                  const SizedBox(height: 10),
                  ...evidence.map((item) {
                    final available = item.path?.isNotEmpty == true;
                    return ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: Icon(
                        available
                            ? Icons.image_outlined
                            : Icons.image_not_supported_outlined,
                        color: available
                            ? AppColors.primaryNavy
                            : Colors.blueGrey,
                      ),
                      title: Text(item.title),
                      subtitle: Text(
                        available ? 'Document provided' : 'No image provided',
                      ),
                      trailing: available
                          ? const Icon(Icons.open_in_new_rounded)
                          : null,
                      onTap: available
                          ? () => _viewEvidence(
                              title: item.title,
                              path: item.path,
                              fieldName: item.field,
                            )
                          : null,
                    );
                  }),
                ],
              ),
            ),
          ),
          if (!resident.isVerified) ...[
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _isUpdating ? null : _verify,
              icon: _isUpdating
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.verified_user_outlined),
              label: const Text('Approve and verify resident'),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF047857),
                minimumSize: const Size.fromHeight(50),
              ),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _isUpdating ? null : _reject,
              icon: const Icon(Icons.person_off_outlined),
              label: const Text('Reject registration'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.red.shade700,
                minimumSize: const Size.fromHeight(50),
              ),
            ),
          ],
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final bool verified;

  const _StatusChip({required this.verified});

  @override
  Widget build(BuildContext context) {
    final color = verified ? const Color(0xFF047857) : const Color(0xFFB45309);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(30),
      ),
      child: Text(
        verified ? 'VERIFIED' : 'PENDING',
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}
