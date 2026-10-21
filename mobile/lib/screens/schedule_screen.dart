import 'package:flutter/material.dart';
import '../core/localization/app_language.dart';
import '../core/network/api_client.dart';
import '../core/theme/app_colors.dart';
import '../core/theme/app_tokens.dart';
import '../models/activity_schedule_model.dart';
import '../models/document_request_model.dart';
import '../models/user_model.dart';
import '../services/activity_calendar_service.dart';
import '../services/auth_service.dart';
import '../services/schedule_service.dart';
import '../services/storage_service.dart';
import '../widgets/appointment_schedule_card.dart';
import '../widgets/calendar_day_strip.dart';
import '../widgets/custom_bottom_nav.dart';
import '../widgets/schedule_event_card.dart';
import '../widgets/schedule_detail_dialogs.dart';
import '../widgets/app_surface.dart';
import 'dashboard_screen.dart';
import 'documents_screen.dart';
import 'queue_screen.dart';
import 'profile_screen.dart';

/// Community & Appointments Schedule Screen matching the exact reference UI
class ScheduleScreen extends StatefulWidget {
  final ScheduleService? scheduleService;
  final AuthService? authService;
  final ActivityCalendarService? calendarService;

  const ScheduleScreen({
    super.key,
    this.scheduleService,
    this.authService,
    this.calendarService,
  });

  @override
  State<ScheduleScreen> createState() => _ScheduleScreenState();
}

class _ScheduleScreenState extends State<ScheduleScreen> {
  ScheduleService? _scheduleService;
  AuthService? _authService;
  ScheduleData _data = const ScheduleData();
  DateTime _selectedDate = DateTime.now();
  bool _isLoading = true;
  bool _showAllEvents = false;
  bool _hasError = false;
  String? _errorMessage;
  bool _isRetrying = false;
  final int _selectedNavIndex = 3;

  @override
  void initState() {
    super.initState();
    _initializeAndLoad();
  }

  Future<void> _initializeAndLoad() async {
    _scheduleService = widget.scheduleService;
    _authService = widget.authService;

    if (_scheduleService == null || _authService == null) {
      final storage = await StorageService.init();
      final apiClient = ApiClient();
      _authService ??= AuthService(
        apiClient: apiClient,
        storageService: storage,
      );
      _scheduleService ??= ScheduleService(
        apiClient: apiClient,
        storageService: storage,
      );
    }

    await _loadScheduleData();
  }

  Future<void> _loadScheduleData() async {
    if (_scheduleService == null) return;
    if (mounted && _hasError) {
      setState(() {
        _isRetrying = true;
      });
    }

    try {
      final freshData = await _scheduleService!.fetchScheduleData();
      if (mounted) {
        setState(() {
          _data = freshData;
          _isLoading = false;
          _hasError = false;
          _errorMessage = null;
          _isRetrying = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _hasError = true;
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
          _isRetrying = false;
        });
      }
    }
  }

  void _navigateToProfile() {
    final user = _data.user;
    if (user == null || _authService == null) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ProfileScreen(user: user, authService: _authService!),
      ),
    );
  }

  Future<void> _onAddToCalendar(ActivityScheduleModel activity) async {
    var calendarOpened = false;
    try {
      calendarOpened = await (widget.calendarService ?? ActivityCalendarService())
          .addActivity(activity);
    } catch (_) {
      // A device may have no calendar app or the platform handoff may fail.
    }

    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          calendarOpened
              ? context.tr('Calendar opened. Review and save the event there.')
              : context.tr('Could not open your device calendar.'),
        ),
        backgroundColor: AppColors.primaryNavy,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        duration: const Duration(seconds: 3),
      ),
    );
  }

  void _showEventDetails(ActivityScheduleModel activity) {
    showDialog(
      context: context,
      builder: (_) => ActivityDetailsDialog(
        activity: activity,
        onAddToCalendar: () => _onAddToCalendar(activity),
      ),
    );
  }

  void _showAppointmentDetails(DocumentRequestModel request) {
    showDialog(
      context: context,
      builder: (_) => AppointmentDetailsDialog(request: request),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline_rounded,
              color: AppColors.error,
              size: 56,
            ),
            const SizedBox(height: 16),
            Text(
              context.tr('Unable to load schedule data'),
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              context.tr(_errorMessage ?? 'Please check your internet connection and try again.'),
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 13.5,
                color: Color(0xFF64748B),
              ),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: _isRetrying ? null : _loadScheduleData,
              icon: _isRetrying
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.refresh_rounded, size: 18),
              label: Text(_isRetrying ? context.tr('Retrying...') : context.tr('Try again')),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primaryNavy,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final UserModel? user = _data.user;

    // Filter appointments strictly for selected date
    final appointmentsForDate = _data.getAppointmentsForDate(_selectedDate);

    // Active ongoing requests rendered in dedicated active section
    final activeAppointments = _data.activeAppointments;

    // Filter upcoming events strictly for selected date, or all if toggled
    final filteredActivities = _data.getActivitiesForDate(_selectedDate);
    final displayedActivities = _showAllEvents
        ? _data.activities
        : filteredActivities;

    // Event dates for calendar dot indicators
    final eventDates = _data.activities.map((a) => a.eventDatetime).toList();

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
                  onTap: _navigateToProfile,
                  child: Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: const Color(0xFFCBD5E1),
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: const Color(0xFF94A3B8),
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
                          fontWeight: FontWeight.w800,
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
                  onRefresh: _loadScheduleData,
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
                        AppPageHeading(
                          eyebrow: context.tr('COMMUNITY CALENDAR'),
                          title: context.tr('Schedule'),
                        ),
                        const SizedBox(height: 20),

                        // 1. Calendar Day Strip Header
                        CalendarDayStrip(
                          selectedDate: _selectedDate,
                          eventDates: eventDates,
                          onDateSelected: (date) {
                            setState(() {
                              _selectedDate = date;
                              _showAllEvents = false;
                            });
                          },
                        ),

                        const SizedBox(height: 24),

                        // 2. "MY APPOINTMENTS" Section
                        Text(
                          context.tr('MY APPOINTMENTS'),
                          style: TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF64748B),
                            letterSpacing: 1.0,
                          ),
                        ),

                        const SizedBox(height: 12),

                        if (_data.hasAppointmentsError)
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: const Color(0xFFFEE2E2)),
                            ),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.info_outline_rounded,
                                  color: AppColors.error,
                                  size: 20,
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    context.tr('Unable to update appointments.'),
                                    style: TextStyle(
                                      fontSize: 13,
                                      color: AppColors.textPrimary,
                                    ),
                                  ),
                                ),
                                TextButton(
                                  onPressed: _loadScheduleData,
                                  child: Text(context.tr('Retry')),
                                ),
                              ],
                            ),
                          )
                        else if (appointmentsForDate.isEmpty)
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(
                              vertical: 24,
                              horizontal: 16,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(
                                color: const Color(0xFFF1F5F9),
                                width: 1.5,
                              ),
                            ),
                            child: Column(
                              children: [
                                Icon(
                                  Icons.event_busy_rounded,
                                  size: 32,
                                  color: const Color(
                                    0xFF94A3B8,
                                  ).withValues(alpha: 0.8),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  context.tr('No appointments scheduled for this date'),
                                  style: TextStyle(
                                    fontSize: 13.5,
                                    fontWeight: FontWeight.w600,
                                    color: Color(0xFF64748B),
                                  ),
                                ),
                              ],
                            ),
                          )
                        else
                          ListView.separated(
                            key: const Key('daily_appointments_list'),
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: appointmentsForDate.length > 2
                                ? 2
                                : appointmentsForDate.length,
                            separatorBuilder: (_, _) => const SizedBox(height: 12),
                            itemBuilder: (context, index) {
                              final req = appointmentsForDate[index];
                              return AppointmentScheduleCard(
                                key: Key('daily_request_card_${req.id}'),
                                request: req,
                                onTap: () => _showAppointmentDetails(req),
                              );
                            },
                          ),

                        // 2b. "ACTIVE ONGOING REQUESTS" (Kept in a clearly separate section)
                        if (activeAppointments.isNotEmpty) ...[
                          const SizedBox(height: 24),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                context.tr('ACTIVE ONGOING REQUESTS'),
                                style: TextStyle(
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF64748B),
                                  letterSpacing: 1.0,
                                ),
                              ),
                              Text(
                                '${activeAppointments.length} ${context.tr('Active')}',
                                style: const TextStyle(
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.primaryNavy,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          ListView.separated(
                            key: const Key('active_ongoing_requests_list'),
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: activeAppointments.length,
                            separatorBuilder: (_, _) => const SizedBox(height: 12),
                            itemBuilder: (context, index) {
                              final req = activeAppointments[index];
                              return AppointmentScheduleCard(
                                key: Key('active_request_card_${req.id}'),
                                request: req,
                                onTap: () => _showAppointmentDetails(req),
                              );
                            },
                          ),
                        ],

                        const SizedBox(height: 26),

                        // 3. "Upcoming Events" Section Header
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              context.tr('Upcoming Events'),
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w900,
                                color: AppColors.textPrimary,
                                letterSpacing: -0.3,
                              ),
                            ),
                            GestureDetector(
                              onTap: () {
                                setState(() {
                                  _showAllEvents = !_showAllEvents;
                                });
                              },
                              child: Text(
                                context.tr(_showAllEvents ? 'Show Date' : 'View All'),
                                style: const TextStyle(
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w800,
                                  color: AppColors.primaryNavy,
                                ),
                              ),
                            ),
                          ],
                        ),

                        const SizedBox(height: 14),

                        // Upcoming Events List
                        if (_data.hasActivitiesError)
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: const Color(0xFFFEE2E2)),
                            ),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.info_outline_rounded,
                                  color: AppColors.error,
                                  size: 20,
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    context.tr('Unable to update community events.'),
                                    style: TextStyle(
                                      fontSize: 13,
                                      color: AppColors.textPrimary,
                                    ),
                                  ),
                                ),
                                TextButton(
                                  onPressed: _loadScheduleData,
                                  child: Text(context.tr('Retry')),
                                ),
                              ],
                            ),
                          )
                        else if (displayedActivities.isEmpty)
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(
                              vertical: 28,
                              horizontal: 16,
                            ),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF8FAFC),
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(
                                color: const Color(0xFFE2E8F0),
                                width: 1.0,
                              ),
                            ),
                            child: Column(
                              children: [
                                const Icon(
                                  Icons.calendar_today_outlined,
                                  size: 32,
                                  color: Color(0xFF94A3B8),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  context.tr('No community events scheduled'),
                                  style: TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                    color: Color(0xFF64748B),
                                  ),
                                ),
                                const SizedBox(height: 6),
                                TextButton(
                                  onPressed: () {
                                    setState(() {
                                      _showAllEvents = true;
                                    });
                                  },
                                  child: Text(context.tr('View All Activities')),
                                ),
                              ],
                            ),
                          )
                        else
                          ListView.separated(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: displayedActivities.length,
                            separatorBuilder: (_, _) => const SizedBox(height: 16),
                            itemBuilder: (context, index) {
                              final activity = displayedActivities[index];
                              return ScheduleEventCard(
                                activity: activity,
                                onAddToCalendar: () => _onAddToCalendar(activity),
                                onTap: () => _showEventDetails(activity),
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
          if (index == 0) {
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(builder: (_) => const DashboardScreen()),
            );
          } else if (index == 1) {
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(builder: (_) => const QueueScreen()),
            );
          } else if (index == 2) {
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(builder: (_) => const DocumentsScreen()),
            );
          }
        },
      ),
    );
  }
}
