import 'dart:async';

import 'package:flutter/material.dart';
import '../core/network/api_client.dart';
import '../core/theme/app_colors.dart';
import '../core/theme/app_tokens.dart';
import '../models/queue_ticket_model.dart';
import '../models/user_model.dart';
import '../services/auth_service.dart';
import '../services/queue_service.dart';
import '../services/storage_service.dart';
import '../widgets/custom_bottom_nav.dart';
import '../widgets/queue_hero_card.dart';
import '../widgets/queue_metric_cards.dart';
import '../widgets/recent_completions_section.dart';
import '../widgets/request_queue_ticket_sheet.dart';
import '../widgets/user_ticket_card.dart';
import '../widgets/app_surface.dart';
import 'dashboard_screen.dart';
import 'documents_screen.dart';
import 'schedule_screen.dart';
import 'profile_screen.dart';

/// Screen presenting the live queue status matching the exact reference UI
class QueueScreen extends StatefulWidget {
  final QueueService? queueService;
  final AuthService? authService;

  const QueueScreen({super.key, this.queueService, this.authService});

  @override
  State<QueueScreen> createState() => _QueueScreenState();
}

class _QueueScreenState extends State<QueueScreen> with WidgetsBindingObserver {
  QueueService? _queueService;
  AuthService? _authService;
  UserModel? _currentUser;
  QueueLiveStatusModel _queueStatus = const QueueLiveStatusModel();
  bool _isLoading = true;
  bool _hasError = false;
  String? _errorMessage;
  bool _isRetrying = false;
  final int _selectedNavIndex = 1;
  bool _isRequestingTicket = false;
  bool _isLoadingQueueData = false;
  Timer? _queueRefreshTimer;

  void _showRequestTicketModal() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => RequestQueueTicketSheet(
        isSubmitting: _isRequestingTicket,
        onSubmit: _requestTicket,
      ),
    );
  }

  Future<void> _requestTicket({
    required String serviceType,
    required String? notes,
  }) async {
    final service = _queueService;
    if (service == null || _isRequestingTicket) return;

    final messenger = ScaffoldMessenger.of(context);
    setState(() => _isRequestingTicket = true);
    try {
      final ticket = await service.requestTicket(
        serviceType: serviceType,
        notes: notes,
      );
      if (mounted) {
        messenger.showSnackBar(
          SnackBar(content: Text('Ticket ${ticket.ticketNumber} generated!')),
        );
        _loadQueueData();
      }
    } catch (error) {
      if (mounted) {
        messenger.showSnackBar(
          SnackBar(content: Text('Failed to get ticket: $error')),
        );
      }
    } finally {
      if (mounted) setState(() => _isRequestingTicket = false);
    }
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeAndLoad();
  }

  Future<void> _initializeAndLoad() async {
    _queueService = widget.queueService;
    _authService = widget.authService;

    final storage = await StorageService.init();
    _currentUser = storage.getUser();

    final apiClient = ApiClient();
    _authService ??= AuthService(apiClient: apiClient, storageService: storage);
    _queueService ??= QueueService(
      apiClient: apiClient,
      storageService: storage,
    );

    await _loadQueueData();
    _startQueuePolling();
  }

  void _startQueuePolling() {
    if (_queueRefreshTimer != null ||
        WidgetsBinding.instance.lifecycleState != AppLifecycleState.resumed) {
      return;
    }

    _queueRefreshTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (!mounted ||
          WidgetsBinding.instance.lifecycleState != AppLifecycleState.resumed ||
          ModalRoute.of(context)?.isCurrent != true) {
        return;
      }
      _loadQueueData();
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _startQueuePolling();
      if (ModalRoute.of(context)?.isCurrent == true) {
        _loadQueueData();
      }
    } else {
      _queueRefreshTimer?.cancel();
      _queueRefreshTimer = null;
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _queueRefreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadQueueData({bool isRetry = false}) async {
    if (_queueService == null || _isLoadingQueueData) return;

    _isLoadingQueueData = true;
    if (isRetry && mounted) {
      setState(() => _isRetrying = true);
    }

    try {
      final freshStatus = await _queueService!.fetchQueueStatus();
      if (mounted) {
        setState(() {
          _queueStatus = freshStatus;
          _isLoading = false;
          _hasError = false;
          _errorMessage = null;
          _isRetrying = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _hasError = true;
          _errorMessage = e is QueueServiceException
              ? e.message
              : 'Unable to load live queue status. Please check your connection.';
          _isLoading = false;
          _isRetrying = false;
        });
      }
    } finally {
      _isLoadingQueueData = false;
    }
  }

  void _navigateToProfile() {
    if (_currentUser == null || _authService == null) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) =>
            ProfileScreen(user: _currentUser!, authService: _authService!),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = _currentUser;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(64),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: 20.0,
              vertical: 8.0,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // KapitBayan Brand Logo + Text
                Row(
                  children: [
                    Image.asset(
                      'assets/images/kapitbayan_symbol.png',
                      width: 38,
                      height: 38,
                      fit: BoxFit.contain,
                    ),
                    const SizedBox(width: 10),
                    const Text(
                      'KapitBayan',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w900,
                        color: AppColors.primaryNavy,
                        letterSpacing: -0.3,
                      ),
                    ),
                  ],
                ),

                // Right Profile Avatar Circle
                GestureDetector(
                  onTap: _navigateToProfile,
                  child: Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: const Color(0xFFE2E8F0),
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: const Color(0xFFCBD5E1),
                        width: 1.5,
                      ),
                    ),
                    child: Center(
                      child: Text(
                        user != null && user.fullName.isNotEmpty
                            ? user.fullName[0].toUpperCase()
                            : (user != null && user.username.isNotEmpty
                                  ? user.username[0].toUpperCase()
                                  : 'R'),
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: AppColors.primaryNavy,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
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
          : _hasError
              ? _buildErrorState()
              : RefreshIndicator(
                  onRefresh: _loadQueueData,
                  color: AppColors.primaryNavy,
                  child: SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.pageHorizontal,
                      vertical: AppSpacing.pageVertical,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const AppPageHeading(
                          eyebrow: 'LIVE QUEUE STATUS',
                          title: "Today's Queue",
                        ),

                        const SizedBox(height: 20),

                        // 1. Hero Card: Currently at Counter or Live Status Error Notice
                        if (_queueStatus.hasLiveStatusError) ...[
                          _buildLiveStatusErrorCard(),
                          const SizedBox(height: 18),
                        ] else ...[
                          QueueHeroCard(
                            currentTicket: _queueStatus.currentTicket,
                            serviceType: _queueStatus.currentService,
                          ),
                          const SizedBox(height: 18),
                        ],

                        // 2. User's Active Ticket Card
                        UserTicketCard(
                          ticket: _queueStatus.userTicket,
                          hasError: _queueStatus.hasUserTicketsError,
                          errorMessage: _queueStatus.userTicketsErrorMessage ?? _queueStatus.errorMessage,
                          onRetry: () => _loadQueueData(isRetry: true),
                        ),

                        const SizedBox(height: 18),

                        // 3. Side-by-Side Metric Cards: Estimated Call & Live Capacity
                        if (!_queueStatus.hasLiveStatusError) ...[
                          QueueMetricCards(
                            estimatedCallTime:
                                _queueStatus.estimatedCallTimeFormatted,
                            liveCapacity: _queueStatus.capacityLabel,
                          ),

                          const SizedBox(height: 28),

                          // 4. Recent Completions List
                          RecentCompletionsSection(
                            completedTickets: _queueStatus.recentCompleted,
                            onViewAll: () {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Viewing complete queue history'),
                                  behavior: SnackBarBehavior.floating,
                                ),
                              );
                            },
                          ),

                          const SizedBox(height: 32),
                        ],
                      ],
                    ),
                  ),
                ),
      bottomNavigationBar: CustomBottomNav(
        currentIndex: _selectedNavIndex,
        onTap: (index) {
          if (index == 0) {
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(builder: (_) => const DashboardScreen()),
            );
          } else if (index == 2) {
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(builder: (_) => const DocumentsScreen()),
            );
          } else if (index == 3) {
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(builder: (_) => const ScheduleScreen()),
            );
          }
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showRequestTicketModal,
        backgroundColor: const Color(0xFF0047BA),
        icon: const Icon(
          Icons.confirmation_number_outlined,
          color: Colors.white,
        ),
        label: const Text(
          'Get Ticket',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
      ),
    );
  }

  Widget _buildLiveStatusErrorCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 18.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFFFECACA)),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0F172A).withValues(alpha: 0.05),
            blurRadius: 15,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'CURRENTLY AT COUNTER',
                  style: TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Live Queue Unavailable',
                  style: TextStyle(
                    color: Color(0xFFB91C1C),
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.3,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _queueStatus.liveStatusErrorMessage ?? 'Unable to connect to live queue desk.',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: _isRetrying ? null : () => _loadQueueData(isRetry: true),
            tooltip: 'Retry loading live queue status',
            icon: _isRetrying
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(
                    Icons.refresh_rounded,
                    color: AppColors.primaryNavy,
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 32.0),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(24.0),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: const Color(0xFFFECACA)),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF0F172A).withValues(alpha: 0.05),
                blurRadius: 15,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.cloud_off_outlined,
                color: Color(0xFFB91C1C),
                size: 36,
                semanticLabel: 'Unable to load live queue status',
              ),
              const SizedBox(height: 12),
              const Text(
                'Live Queue Unavailable',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: AppColors.primaryNavy,
                ),
              ),
              const SizedBox(height: 8),
              Semantics(
                liveRegion: true,
                child: Text(
                  _errorMessage ?? 'Unable to connect to queue system.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 13.5,
                    color: Color(0xFF64748B),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const SizedBox(height: 20),
              OutlinedButton.icon(
                onPressed: _isRetrying ? null : () => _loadQueueData(isRetry: true),
                icon: _isRetrying
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.refresh_rounded),
                label: Text(_isRetrying ? 'Retrying…' : 'Try again'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.primaryNavy,
                  side: const BorderSide(color: AppColors.primaryNavy),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 12,
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
