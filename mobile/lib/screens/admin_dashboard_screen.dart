import 'dart:convert';
import 'package:flutter/material.dart';
import '../core/network/api_client.dart';
import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';
import '../models/user_model.dart';
import '../services/storage_service.dart';
import 'field_official_screen.dart';
import 'login_screen.dart';

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  UserModel? _currentUser;
  bool _isLoading = true;
  bool _hasLoadedSummary = false;
  bool _summaryLoadError = false;
  bool _isRetryingSummary = false;

  // Headline metrics aligned with the web Admin Dashboard.
  int _totalResidents = 0;
  int _pendingDocuments = 0;
  int _activeIssues = 0;
  double _clearanceCollections = 0;

  @override
  void initState() {
    super.initState();
    _loadExecutiveDashboard();
  }

  Future<void> _loadExecutiveDashboard({bool isRetry = false}) async {
    if (isRetry && mounted) setState(() => _isRetryingSummary = true);
    try {
      final storage = await StorageService.init();
      final currentUser = storage.getUser();
      final token = storage.getAccessToken();
      if (token == null || token.isEmpty) {
        throw StateError('No active session is available.');
      }

      final apiClient = ApiClient();
      apiClient.setAuthCredentials(accessToken: token);
      final response = await apiClient.get(
        '/dashboard/summary/',
        requiresAuth: true,
      );
      if (response.statusCode != 200) {
        throw StateError('Dashboard summary request failed.');
      }

      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      if (decoded is! Map) {
        throw const FormatException('Dashboard summary must be an object.');
      }
      final data = Map<String, dynamic>.from(decoded);
      final documents = _asMap(data['document_requests']);
      final issues = _asMap(data['issue_reports']);
      final totalResidents = _readRequiredCount(
        data['total_residents'],
        'total_residents',
      );
      final pendingDocuments = _readRequiredCount(
        documents['pending'],
        'document_requests.pending',
      );
      final activeIssues = _readRequiredCount(
        issues['in_progress'],
        'issue_reports.in_progress',
      );
      final revenue = documents['total_revenue'];
      if (revenue != null && (revenue is! num || !revenue.isFinite)) {
        throw const FormatException('Invalid document_requests.total_revenue.');
      }

      if (!mounted) return;
      setState(() {
        _currentUser = currentUser;
        _totalResidents = totalResidents;
        _pendingDocuments = pendingDocuments;
        _activeIssues = activeIssues;
        _clearanceCollections = revenue is num ? revenue.toDouble() : 0;
        _hasLoadedSummary = true;
        _summaryLoadError = false;
        _isLoading = false;
        _isRetryingSummary = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _summaryLoadError = true;
        _isLoading = false;
        _isRetryingSummary = false;
      });
    }
  }

  Map<String, dynamic> _asMap(Object? value) => value is Map
      ? Map<String, dynamic>.from(value)
      : const <String, dynamic>{};

  int _readRequiredCount(Object? value, String field) {
    if (value is! num || !value.isFinite) {
      throw FormatException('Invalid $field in dashboard summary.');
    }
    return value.toInt();
  }

  String _formatCurrency(double value) {
    final amount = value.toStringAsFixed(2);
    final parts = amount.split('.');
    final groupedWhole = parts.first.replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (_) => ',',
    );
    return '₱$groupedWhole.${parts.last}';
  }

  void _handleLogout() async {
    final storage = await StorageService.init();
    await storage.clearAll();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final language = AppLanguageScope.of(context);
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: const Color(0xFF091B35),
        elevation: 0,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.tr('Executive Console'),
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
                color: Colors.white,
              ),
            ),
            Text(
              _currentUser?.fullName.isNotEmpty == true
                  ? _currentUser!.fullName
                  : context.tr('Barangay Captain'),
              style: const TextStyle(
                fontSize: 12,
                color: Color(0xFF38BDF8),
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        actions: [
          PopupMenuButton<String>(
            tooltip: context.tr('Choose language'),
            onSelected: (value) => language.setLanguage(value),
            itemBuilder: (context) => [
              PopupMenuItem(value: 'en', child: Text(context.tr('English'))),
              PopupMenuItem(
                value: 'fil',
                child: Text(context.tr('Filipino (Tagalog)')),
              ),
            ],
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Center(
                child: Text(
                  language.languageCode.toUpperCase(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: Colors.white),
            tooltip: context.tr('Logout'),
            onPressed: _handleLogout,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(
                  AppColors.primaryNavy,
                ),
              ),
            )
          : !_hasLoadedSummary
          ? _buildSummaryErrorState()
          : RefreshIndicator(
              onRefresh: _loadExecutiveDashboard,
              color: AppColors.primaryNavy,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(20.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (_summaryLoadError) ...[
                      _buildRefreshErrorBanner(),
                      const SizedBox(height: 16),
                    ],
                    Text(
                      context.tr('Administrative Overview'),
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w900,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      context.tr('Service summary and community records.'),
                      style: const TextStyle(
                        fontSize: 13,
                        color: Color(0xFF64748B),
                      ),
                    ),
                    const SizedBox(height: 18),
                    // Show the current admin mode without offering resident-view switching.
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 12,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            Icons.admin_panel_settings_rounded,
                            color: AppColors.primaryNavy,
                            size: 20,
                          ),
                          SizedBox(width: 8),
                          Text(
                            context.tr('Executive Mode Active'),
                            style: TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 13,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 20),

                    // Executive Metric Cards (Aligned with Web Admin)
                    Text(
                      context.tr('OVERVIEW METRICS'),
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF64748B),
                        letterSpacing: 1.2,
                      ),
                    ),
                    const SizedBox(height: 12),

                    GridView.count(
                      crossAxisCount: 2,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      childAspectRatio: 0.94,
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      children: [
                        _buildMetricCard(
                          title: 'Total Registered Residents',
                          value: '$_totalResidents',
                          icon: Icons.people_alt_outlined,
                          iconColor: const Color(0xFF0284C7),
                          bgColor: const Color(0xFFF0F9FF),
                        ),
                        _buildMetricCard(
                          title: 'Pending Requests',
                          value: '$_pendingDocuments',
                          icon: Icons.assignment_outlined,
                          iconColor: const Color(0xFFDC2626),
                          bgColor: const Color(0xFFFEF2F2),
                        ),
                        _buildMetricCard(
                          title: 'Active Issues (In Progress)',
                          value: '$_activeIssues',
                          icon: Icons.hourglass_top_rounded,
                          iconColor: const Color(0xFFD97706),
                          bgColor: const Color(0xFFFFFBEB),
                        ),
                        _buildMetricCard(
                          title: 'Clearance Collections',
                          value: _formatCurrency(_clearanceCollections),
                          icon: Icons.account_balance_wallet_outlined,
                          iconColor: const Color(0xFF059669),
                          bgColor: const Color(0xFFECFDF5),
                        ),
                      ],
                    ),

                    const SizedBox(height: 24),

                    // Executive Management Actions
                    Text(
                      context.tr('EXECUTIVE OPERATIONS'),
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF64748B),
                        letterSpacing: 1.2,
                      ),
                    ),
                    const SizedBox(height: 12),

                    _buildActionTile(
                      icon: Icons.shield_rounded,
                      iconBg: const Color(0xFF091B35),
                      title: context.tr('Field Operations Desk'),
                      subtitle: context.tr(
                        'Advance queue ticker, verify clearance QR, triage incidents',
                      ),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const FieldOfficialScreen(),
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildSummaryErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.cloud_off_rounded,
              size: 42,
              color: Color(0xFFDC2626),
            ),
            const SizedBox(height: 12),
            Text(
              context.tr("We couldn't load dashboard summary."),
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              context.tr('Check your connection and try again.'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _isRetryingSummary
                  ? null
                  : () => _loadExecutiveDashboard(isRetry: true),
              icon: _isRetryingSummary
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.refresh_rounded),
              label: Text(
                context.tr(_isRetryingSummary ? 'Retrying…' : 'Retry'),
              ),
              style: FilledButton.styleFrom(
                minimumSize: const Size(120, 48),
                backgroundColor: AppColors.primaryNavy,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRefreshErrorBanner() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFFEF2F2),
        border: Border.all(color: const Color(0xFFFECACA)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.error_outline_rounded,
            color: Color(0xFFB91C1C),
            size: 20,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              context.tr("We couldn't refresh dashboard summary."),
              style: const TextStyle(fontSize: 12, color: Color(0xFF7F1D1D)),
            ),
          ),
          TextButton(
            onPressed: _isRetryingSummary
                ? null
                : () => _loadExecutiveDashboard(isRetry: true),
            child: Text(context.tr(_isRetryingSummary ? 'Retrying…' : 'Retry')),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricCard({
    required String title,
    required String value,
    String? subtitle,
    required IconData icon,
    required Color iconColor,
    required Color bgColor,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFFF1F5F9)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: iconColor, size: 20),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Text(
                  value,
                  maxLines: 1,
                  style: const TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.w900,
                    color: AppColors.primaryNavy,
                  ),
                ),
              ),
              const SizedBox(height: 2),
              Text(
                context.tr(title),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF64748B),
                ),
              ),
              if (subtitle != null) ...[
                const SizedBox(height: 2),
                Text(
                  context.tr(subtitle),
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: iconColor,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildActionTile({
    required IconData icon,
    required Color iconBg,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE2E8F0)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: iconBg,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: Colors.white, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.tr(title),
                    style: const TextStyle(
                      fontSize: 14.5,
                      fontWeight: FontWeight.w800,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    context.tr(subtitle),
                    style: const TextStyle(
                      fontSize: 11.5,
                      color: Color(0xFF64748B),
                    ),
                  ),
                ],
              ),
            ),
            const Icon(
              Icons.arrow_forward_ios_rounded,
              size: 14,
              color: Color(0xFF94A3B8),
            ),
          ],
        ),
      ),
    );
  }
}
