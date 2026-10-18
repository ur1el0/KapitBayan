import 'dart:convert';
import 'package:flutter/material.dart';
import '../core/network/api_client.dart';
import '../core/theme/app_colors.dart';
import '../models/user_model.dart';
import '../services/storage_service.dart';
import 'field_official_screen.dart';
import 'login_screen.dart';
import 'queue_screen.dart';

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  UserModel? _currentUser;
  bool _isLoading = true;

  // Executive Metrics from /dashboard/summary/
  int _totalResidents = 0;
  int _pendingDocuments = 0;
  int _waitingQueue = 0;
  String? _servingNow;
  int _pendingIssues = 0;

  @override
  void initState() {
    super.initState();
    _loadExecutiveDashboard();
  }

  Future<void> _loadExecutiveDashboard() async {
    final storage = await StorageService.init();
    _currentUser = storage.getUser();

    final apiClient = ApiClient();
    final token = storage.getAccessToken();
    if (token != null) {
      apiClient.setAuthCredentials(accessToken: token);
    }

    try {
      final response = await apiClient.get('/dashboard/summary/', requiresAuth: true);
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        setState(() {
          _totalResidents = data['total_residents'] as int? ?? 0;
          
          final docs = data['document_requests'] as Map<String, dynamic>?;
          _pendingDocuments = docs?['pending'] as int? ?? 0;

          final queue = data['queue_activity'] as Map<String, dynamic>?;
          _waitingQueue = queue?['waiting_count'] as int? ?? 0;
          _servingNow = queue?['serving_now'] as String?;

          final issues = data['issue_reports'] as Map<String, dynamic>?;
          _pendingIssues = issues?['pending'] as int? ?? 0;
          
          _isLoading = false;
        });
        return;
      }
    } catch (_) {}

    if (mounted) setState(() => _isLoading = false);
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
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: const Color(0xFF091B35),
        elevation: 0,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Executive Console',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: Colors.white),
            ),
            Text(
              _currentUser?.fullName.isNotEmpty == true ? _currentUser!.fullName : 'Barangay Captain',
              style: const TextStyle(fontSize: 12, color: Color(0xFF38BDF8), fontWeight: FontWeight.w600),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: Colors.white),
            tooltip: 'Logout',
            onPressed: _handleLogout,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(valueColor: AlwaysStoppedAnimation<Color>(AppColors.primaryNavy)))
          : RefreshIndicator(
              onRefresh: _loadExecutiveDashboard,
              color: AppColors.primaryNavy,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(20.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Show the current admin mode without offering resident-view switching.
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.admin_panel_settings_rounded, color: AppColors.primaryNavy, size: 20),
                          SizedBox(width: 8),
                          Text(
                            'Executive Mode Active',
                            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: AppColors.textPrimary),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 20),

                    // Executive Metric Cards (Aligned with Web Admin)
                    const Text(
                      'OVERVIEW METRICS',
                      style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF64748B), letterSpacing: 1.2),
                    ),
                    const SizedBox(height: 12),

                    GridView.count(
                      crossAxisCount: 2,
                      crossAxisSpacing: 14,
                      mainAxisSpacing: 14,
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      children: [
                        _buildMetricCard(
                          title: 'Total Residents',
                          value: '$_totalResidents',
                          icon: Icons.people_alt_outlined,
                          iconColor: const Color(0xFF0284C7),
                          bgColor: const Color(0xFFF0F9FF),
                        ),
                        _buildMetricCard(
                          title: 'Pending Docs',
                          value: '$_pendingDocuments',
                          icon: Icons.assignment_outlined,
                          iconColor: const Color(0xFFF59E0B),
                          bgColor: const Color(0xFFFFFBEB),
                        ),
                        _buildMetricCard(
                          title: 'Waiting Queue',
                          value: '$_waitingQueue',
                          subtitle: _servingNow != null ? 'Serving: $_servingNow' : null,
                          icon: Icons.confirmation_number_outlined,
                          iconColor: const Color(0xFF10B981),
                          bgColor: const Color(0xFFECFDF5),
                        ),
                        _buildMetricCard(
                          title: 'Active Reports',
                          value: '$_pendingIssues',
                          icon: Icons.warning_amber_rounded,
                          iconColor: const Color(0xFFEF4444),
                          bgColor: const Color(0xFFFEF2F2),
                        ),
                      ],
                    ),

                    const SizedBox(height: 24),

                    // Executive Management Actions
                    const Text(
                      'EXECUTIVE OPERATIONS',
                      style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF64748B), letterSpacing: 1.2),
                    ),
                    const SizedBox(height: 12),

                    _buildActionTile(
                      icon: Icons.shield_rounded,
                      iconBg: const Color(0xFF091B35),
                      title: 'Field Operations Desk',
                      subtitle: 'Advance queue ticker, verify clearance QR, triage incidents',
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const FieldOfficialScreen()),
                        );
                      },
                    ),

                    const SizedBox(height: 10),

                    _buildActionTile(
                      icon: Icons.confirmation_number_rounded,
                      iconBg: const Color(0xFF0284C7),
                      title: 'Live Queue Desk',
                      subtitle: 'Monitor tickets, manage priority lane',
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const QueueScreen()),
                        );
                      },
                    ),
                  ],
                ),
              ),
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
            decoration: BoxDecoration(color: bgColor, borderRadius: BorderRadius.circular(10)),
            child: Icon(icon, color: iconColor, size: 20),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                value,
                style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900, color: AppColors.primaryNavy),
              ),
              const SizedBox(height: 2),
              Text(
                title,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF64748B)),
              ),
              if (subtitle != null) ...[
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: iconColor),
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
              decoration: BoxDecoration(color: iconBg, borderRadius: BorderRadius.circular(12)),
              child: Icon(icon, color: Colors.white, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w800, color: AppColors.textPrimary)),
                  const SizedBox(height: 2),
                  Text(subtitle, style: const TextStyle(fontSize: 11.5, color: Color(0xFF64748B))),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: Color(0xFF94A3B8)),
          ],
        ),
      ),
    );
  }
}
