import 'package:flutter/material.dart';

import '../core/localization/app_language.dart';
import '../core/network/api_client.dart';
import '../core/theme/app_colors.dart';
import '../models/document_request_model.dart';
import '../models/user_model.dart';
import '../services/auth_service.dart';
import '../services/field_official_service.dart';
import '../services/issue_service.dart';
import '../services/storage_service.dart';
import '../widgets/clearance_validator_tab.dart';
import '../widgets/field_reports_tab.dart';
import '../widgets/queue_ticker_tab.dart';
import 'login_screen.dart';

class FieldOfficialScreen extends StatefulWidget {
  final FieldOfficialService? fieldOfficialService;
  final int initialTabIndex;

  const FieldOfficialScreen({
    super.key,
    this.fieldOfficialService,
    this.initialTabIndex = 0,
  });

  @override
  State<FieldOfficialScreen> createState() => _FieldOfficialScreenState();
}

class _FieldOfficialScreenState extends State<FieldOfficialScreen>
    with SingleTickerProviderStateMixin {
  static const Map<String, int> _urgencyPriority = {
    'EMERGENCY': 0,
    'HAZARD': 1,
    'MODERATE': 2,
    'MINOR': 3,
  };

  late TabController _tabController;
  FieldOfficialService? _service;
  AuthService? _authService;
  UserModel? _currentUser;
  bool _isLoading = true;

  // Queue State
  String? _currentTicket;
  int _totalWaiting = 0;
  bool _isCallingTicket = false;

  // Clearance Validation State
  final TextEditingController _trackingIdController = TextEditingController();
  DocumentRequestModel? _verifiedClearance;
  bool _isVerifying = false;
  String? _verificationError;

  // Incident Reports State
  List<IssueReport> _reports = [];
  bool _isLoadingReports = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: 3,
      vsync: this,
      initialIndex: widget.initialTabIndex.clamp(0, 2).toInt(),
    );
    _initializeService();
  }

  Future<void> _initializeService() async {
    _service = widget.fieldOfficialService;
    final storage = await StorageService.init();
    _currentUser = storage.getUser();
    final apiClient = _service?.apiClient ?? ApiClient();
    _authService = AuthService(apiClient: apiClient, storageService: storage);

    _service ??= FieldOfficialService(
      apiClient: apiClient,
      storageService: storage,
    );

    await Future.wait([_loadQueueStatus(), _loadBarangayReports()]);

    if (mounted) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _logout() async {
    final authService = _authService;
    if (authService == null) return;

    await authService.logout();
    if (!mounted) return;

    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  Future<void> _loadQueueStatus() async {
    if (_service == null) return;
    try {
      final data = await _service!.fetchLiveQueueStatus();
      if (mounted) {
        setState(() {
          _currentTicket = data['current_ticket'] as String?;
          _totalWaiting = data['total_waiting'] as int? ?? 0;
        });
      }
    } catch (_) {}
  }

  Future<void> _callNextTicket() async {
    if (_service == null || _isCallingTicket) return;
    setState(() => _isCallingTicket = true);

    try {
      final result = await _service!.callNextTicket();
      if (mounted) {
        setState(() {
          _currentTicket = result['current_ticket'] as String?;
          _totalWaiting = result['remaining_waiting'] as int? ?? 0;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Now serving: $_currentTicket'),
            backgroundColor: const Color(0xFF10B981),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(e.toString().replaceAll('Exception: ', '')),
            backgroundColor: const Color(0xFFEF4444),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isCallingTicket = false);
    }
  }

  Future<void> _verifyClearance() async {
    final text = _trackingIdController.text.trim();
    if (text.isEmpty || _service == null) return;

    setState(() {
      _isVerifying = true;
      _verificationError = null;
      _verifiedClearance = null;
    });

    try {
      final result = await _service!.verifyClearance(text);
      if (mounted) {
        setState(() {
          _verifiedClearance = result;
          if (result == null) {
            _verificationError =
                'No document or O.R. record found for "$text" in this Barangay.';
          }
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _verificationError = 'Network error verifying the record.');
      }
    } finally {
      if (mounted) setState(() => _isVerifying = false);
    }
  }

  Future<void> _loadBarangayReports() async {
    if (_service == null) return;
    setState(() => _isLoadingReports = true);
    try {
      final items = await _service!.fetchBarangayIssues();
      items.sort((first, second) {
        final firstPriority =
            _urgencyPriority[first.urgency.toUpperCase()] ?? 4;
        final secondPriority =
            _urgencyPriority[second.urgency.toUpperCase()] ?? 4;
        final urgencyOrder = firstPriority.compareTo(secondPriority);
        if (urgencyOrder != 0) return urgencyOrder;

        final firstCreatedAt = DateTime.tryParse(first.createdAt);
        final secondCreatedAt = DateTime.tryParse(second.createdAt);
        if (firstCreatedAt != null && secondCreatedAt != null) {
          return firstCreatedAt.compareTo(secondCreatedAt);
        }

        return first.id.compareTo(second.id);
      });

      if (mounted) {
        setState(() {
          _reports = items;
          _isLoadingReports = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoadingReports = false);
    }
  }

  Future<void> _updateReportStatus(int reportId, String newStatus) async {
    if (_service == null) return;
    try {
      await _service!.updateIssueStatus(reportId: reportId, status: newStatus);
      await _loadBarangayReports();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Report #$reportId updated to $newStatus'),
            backgroundColor: const Color(0xFF10B981),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to update report status.'),
            backgroundColor: Color(0xFFEF4444),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  Future<void> _updateReportUrgency(int reportId, String newUrgency) async {
    if (_service == null) return;
    try {
      await _service!.updateIssueUrgency(
        reportId: reportId,
        urgency: newUrgency,
      );
      await _loadBarangayReports();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Report #$reportId urgency updated to $newUrgency.'),
            backgroundColor: const Color(0xFF10B981),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to update report urgency.'),
            backgroundColor: Color(0xFFEF4444),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _trackingIdController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF1F5F9),
      appBar: AppBar(
        backgroundColor: const Color(0xFF091B35),
        elevation: 0,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Field Operations',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
                color: Colors.white,
              ),
            ),
            Text(
              _currentUser?.roleDisplay ?? 'Barangay Official',
              style: const TextStyle(
                fontSize: 12,
                color: Color(0xFF38BDF8),
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        actions: [
          if (_currentUser?.role.toUpperCase() == 'ADMIN')
            IconButton(
              tooltip: context.tr('Return to Executive Console'),
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(
                Icons.space_dashboard_rounded,
                color: Colors.white,
              ),
            ),
          IconButton(
            tooltip: 'Log out',
            onPressed: _authService == null ? null : _logout,
            icon: const Icon(Icons.logout_rounded, color: Colors.white),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: const Color(0xFF38BDF8),
          indicatorWeight: 3,
          labelColor: Colors.white,
          unselectedLabelColor: const Color(0xFF94A3B8),
          tabs: const [
            Tab(
              icon: Icon(Icons.confirmation_number_outlined),
              text: 'Queue Ticker',
            ),
            Tab(
              icon: Icon(Icons.qr_code_scanner_rounded),
              text: 'Verify Clearance',
            ),
            Tab(
              icon: Icon(Icons.assignment_late_outlined),
              text: 'Field Reports',
            ),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(
                  AppColors.primaryNavy,
                ),
              ),
            )
          : TabBarView(
              controller: _tabController,
              children: [
                QueueTickerTab(
                  currentTicket: _currentTicket,
                  totalWaiting: _totalWaiting,
                  isCallingTicket: _isCallingTicket,
                  onRefresh: _loadQueueStatus,
                  onCallNext: _callNextTicket,
                ),
                ClearanceValidatorTab(
                  trackingIdController: _trackingIdController,
                  isVerifying: _isVerifying,
                  verificationError: _verificationError,
                  verifiedClearance: _verifiedClearance,
                  onVerify: _verifyClearance,
                ),
                FieldReportsTab(
                  isLoading: _isLoadingReports,
                  reports: _reports,
                  onRefresh: _loadBarangayReports,
                  onUpdateStatus: _updateReportStatus,
                  onUpdateUrgency: _updateReportUrgency,
                ),
              ],
            ),
    );
  }
}
