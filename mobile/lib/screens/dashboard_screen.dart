import 'dart:async';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';

import '../core/navigation/app_navigation_keys.dart';
import 'hotlines_screen.dart';
import 'report_issue_screen.dart';
import '../services/push_notification_service.dart';

import '../core/network/api_client.dart';
import '../core/theme/app_colors.dart';
import '../core/theme/app_tokens.dart';
import '../models/user_model.dart';
import '../models/notification_item_model.dart';
import '../services/auth_service.dart';
import '../services/dashboard_service.dart';
import '../widgets/community_schedule_section.dart';
import '../widgets/dashboard_notification_sheets.dart';
import '../widgets/custom_bottom_nav.dart';
import '../widgets/metric_summary_card.dart';
import '../widgets/quick_services_section.dart';
import '../widgets/recent_notifications_section.dart';
import '../widgets/resident_hero_card.dart';
import 'documents_screen.dart';
import 'queue_screen.dart';
import 'schedule_screen.dart';
import '../services/storage_service.dart';
import 'profile_screen.dart';
import 'my_issues_screen.dart';
import 'announcements_screen.dart';
import 'aid_requests_screen.dart';
import 'resident_help_screen.dart';

void _openNotificationDestination(RemoteMessage message) {
  final navigator = appNavigatorKey.currentState;
  if (navigator == null) return;

  final data = message.data;
  final type =
      data['type']?.toString() ??
      (data.containsKey('ticket_id')
          ? 'queue'
          : data.containsKey('request_id')
          ? 'document'
          : data.containsKey('report_id')
          ? 'issue'
          : data.containsKey('announcement_id')
          ? 'announcement'
          : '');
  final Widget? destination = switch (type) {
    'queue' => const QueueScreen(),
    'document' => const DocumentsScreen(),
    'issue' => const MyIssuesScreen(),
    'announcement' => const AnnouncementsScreen(),
    _ => null,
  };
  if (destination == null) return;

  navigator.push(MaterialPageRoute<void>(builder: (_) => destination));
}

class DashboardScreen extends StatefulWidget {
  final DashboardService? dashboardService;
  final AuthService? authService;

  const DashboardScreen({super.key, this.dashboardService, this.authService});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  DashboardService? _dashboardService;
  AuthService? _authService;
  PushNotificationService? _pushNotificationService;
  DashboardData _data = const DashboardData();
  bool _isLoading = true;
  final int _selectedNavIndex = 0;

  @override
  void initState() {
    super.initState();
    _initializeAndLoad();
  }

  Future<void> _initializeAndLoad() async {
    _dashboardService = widget.dashboardService;
    _authService = widget.authService;

    final storage = await StorageService.init();
    final cachedUser = storage.getUser();
    final token = storage.getAccessToken();
    final cookie = storage.getRefreshCookie();

    // Instant Cache Render: Eliminate screen freeze by populating cached user immediately
    if (cachedUser != null && mounted) {
      setState(() {
        _data = DashboardData(user: cachedUser);
        _isLoading = false;
      });
    }

    final apiClient = ApiClient();
    if (token != null) {
      apiClient.setAuthCredentials(accessToken: token, cookieHeader: cookie);
    }

    if (_dashboardService == null || _authService == null) {
      _authService ??= AuthService(
        apiClient: apiClient,
        storageService: storage,
      );
      _dashboardService ??= DashboardService(
        apiClient: apiClient,
        storageService: storage,
      );
    }

    // Keep push listeners alive while the resident navigates through the app.
    _pushNotificationService = PushNotificationService.shared(apiClient: apiClient);
    unawaited(
      _pushNotificationService!.initialize(
        onNotificationOpened: _openNotificationDestination,
      ),
    );

    await _loadDashboardData();
  }

  @override
  void dispose() {
    super.dispose();
  }

  Future<void> _loadDashboardData() async {
    if (_dashboardService == null) return;

    try {
      final freshData = await _dashboardService!.fetchDashboardData();
      if (mounted) {
        setState(() {
          _data = freshData;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final UserModel? user = _data.user;

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
                // Brand Logo & Title Header
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
                  onTap: () {
                    if (_data.user != null && _authService != null) {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => ProfileScreen(
                            user: _data.user!,
                            authService: _authService!,
                            pushNotificationService: _pushNotificationService,
                          ),
                        ),
                      );
                    }
                  },
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
                                  : 'C'),
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
          : RefreshIndicator(
              onRefresh: _loadDashboardData,
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
                    // 1. Verified Resident Hero Banner Card
                    ResidentHeroCard(
                      user: _data.user,
                      pendingCount: _data.pendingRequestsCount,
                    ),

                    const SizedBox(height: 18),

                    // 2. Metric Counters Row (Announcements & Pending Requests)
                    MetricSummaryRow(
                      announcementCount: _data.announcements.length,
                      pendingRequestCount: _data.pendingRequestsCount,
                      hasNewAnnouncements: _data.announcements.isNotEmpty,
                      onAnnouncementsTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const AnnouncementsScreen(),
                          ),
                        );
                      },
                      onPendingRequestsTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const DocumentsScreen(),
                          ),
                        );
                      },
                    ),

                    const SizedBox(height: 24),

                    // 3. Quick Services Action Cards (MOVED UP FOR FAST EMERGENCY & HOTLINE ACCESS)
                    QuickServicesSection(
                      onRequestDocument: () {
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => const DocumentsScreen(),
                          ),
                        );
                      },
                      onReportIssue: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const ReportIssueScreen(),
                          ),
                        );
                      },
                      onBarangayHotline: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const HotlinesScreen(),
                          ),
                        );
                      },
                      onMyReports: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const MyIssuesScreen(),
                          ),
                        );
                      },
                      onRequestAid: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const AidRequestsScreen(),
                          ),
                        );
                      },
                      onHelpFAQs: () {
                        final apiClient = _dashboardService?.apiClient;
                        if (apiClient == null) return;
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) =>
                                ResidentHelpScreen(apiClient: apiClient),
                          ),
                        );
                      },
                    ),
                    const SizedBox(height: 24),

                    // 4. Recent Notifications Section (WIRED ONNOTIFICATIONTAP)
                    RecentNotificationsSection(
                      notifications: _data.notifications,
                      hasError: _data.hasNotificationsError,
                      errorMessage: _data.notificationsErrorMessage,
                      onRetry: _loadDashboardData,
                      onViewAll: () => _showNotificationModalSheet(context),
                      onNotificationTap: (item) =>
                          _showNotificationDetailModal(context, item),
                    ),

                    const SizedBox(height: 24),

                    // 5. Community Schedule Timeline
                    CommunityScheduleSection(
                      activities: _data.activities,
                      onActivityTap: (activity) {
                        showDialog(
                          context: context,
                          builder: (ctx) => AlertDialog(
                            title: Text(activity.title),
                            content: Column(
                              mainAxisSize: MainAxisSize.min,
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Location: ${activity.location}',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  activity.description.isNotEmpty
                                      ? activity.description
                                      : 'No additional details provided.',
                                ),
                              ],
                            ),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(ctx),
                                child: const Text('OK'),
                              ),
                            ],
                          ),
                        );
                      },
                    ),

                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ),
      bottomNavigationBar: CustomBottomNav(
        currentIndex: _selectedNavIndex,
        onTap: (index) {
          if (index == 1) {
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(builder: (_) => const QueueScreen()),
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
    );
  }

  void _showNotificationModalSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.4,
        maxChildSize: 0.85,
        expand: false,
        builder: (context, scrollController) => NotificationCenterSheet(
          notifications: _data.notifications,
          hasError: _data.hasNotificationsError,
          errorMessage: _data.notificationsErrorMessage,
          onRetry: () {
            Navigator.pop(context);
            _loadDashboardData();
          },
          scrollController: scrollController,
        ),
      ),
    );
  }

  void _showNotificationDetailModal(
    BuildContext context,
    NotificationItemModel item,
  ) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => NotificationDetailSheet(item: item),
    );
  }
}
