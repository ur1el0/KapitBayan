import 'package:flutter/material.dart';
import '../core/localization/app_language.dart';
import '../core/network/api_client.dart';
import '../services/issue_service.dart';
import '../services/storage_service.dart';

class MyIssuesScreen extends StatefulWidget {
  const MyIssuesScreen({super.key});

  @override
  State<MyIssuesScreen> createState() => _MyIssuesScreenState();
}

class _MyIssuesScreenState extends State<MyIssuesScreen> {
  IssueService? _issueService;
  late Future<List<IssueReport>> _issuesFuture;

  @override
  void initState() {
    super.initState();
    _initService();
  }

  Future<void> _initService() async {
    final storage = await StorageService.init();
    final apiClient = ApiClient();
    final token = storage.getAccessToken();
    if (token != null) {
      apiClient.setAuthCredentials(accessToken: token);
    }
    setState(() {
      _issueService = IssueService(apiClient: apiClient);
      _issuesFuture = _issueService!.getMyIssues();
    });
  }

  Future<void> _refresh() async {
    if (_issueService != null) {
      setState(() {
        _issuesFuture = _issueService!.getMyIssues();
      });
    }
  }

  // Premium Tailwind UI Color Palette for Statuses
  Color _getStatusColor(String status) {
    switch (status.toUpperCase()) {
      case 'RESOLVED':
        return const Color(0xFF10B981); // Emerald 500
      case 'IN_PROGRESS':
        return const Color(0xFF3B82F6); // Blue 500
      case 'REJECTED':
        return const Color(0xFFEF4444); // Red 500
      default:
        return const Color(0xFFF59E0B); // Amber 500
    }
  }

  // Helper to format the ISO timestamp from Django
  String _formatDate(String isoString) {
    try {
      final date = DateTime.parse(isoString).toLocal();
      final months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return "${months[date.month - 1]} ${date.day}, ${date.year}";
    } catch (e) {
      return isoString;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC), // slate-50 background
      appBar: AppBar(
        title: Text(
          context.tr('My Report History'),
          style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF0F172A), fontSize: 20),
        ),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: Color(0xFF0F172A)),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(color: const Color(0xFFE2E8F0), height: 1), // subtle bottom border
        ),
      ),
      body: _issueService == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _refresh,
              color: const Color(0xFF2563EB),
              child: FutureBuilder<List<IssueReport>>(
                future: _issuesFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(child: CircularProgressIndicator(color: Color(0xFF2563EB)));
                  } else if (snapshot.hasError) {
                    return Center(child: Text('${context.tr('Could not load reports.')}: ${snapshot.error}', style: const TextStyle(color: Colors.red)));
                  } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.assignment_outlined, size: 64, color: Color(0xFFCBD5E1)),
                          const SizedBox(height: 16),
                          Text(context.tr('No reports submitted yet.'), style: TextStyle(color: Color(0xFF64748B), fontSize: 16)),
                        ],
                      ),
                    );
                  }

                  final issues = snapshot.data!;
                  return ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: issues.length,
                    itemBuilder: (context, index) {
                      final issue = issues[index];
                      final statusColor = _getStatusColor(issue.status);

                      return Container(
                        margin: const EdgeInsets.only(bottom: 16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF0F172A).withValues(alpha: 0.04),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Top Row: Date and Status Badge
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    _formatDate(issue.createdAt),
                                    style: const TextStyle(
                                      color: Color(0xFF64748B),
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      letterSpacing: 0.5,
                                    ),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: statusColor.withValues(alpha: 0.1),
                                      borderRadius: BorderRadius.circular(20),
                                      border: Border.all(color: statusColor.withValues(alpha: 0.2)),
                                    ),
                                    child: Text(
                                      context.tr(issue.status.replaceAll('_', ' ')),
                                      style: TextStyle(color: statusColor, fontWeight: FontWeight.bold, fontSize: 10),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              
                              // Title
                              Text(
                                issue.title,
                                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                              ),
                              const SizedBox(height: 6),
                              
                              // Description
                              Text(
                                issue.description,
                                style: const TextStyle(color: Color(0xFF475569), height: 1.4, fontSize: 14),
                              ),
                              
                                                            // Optional Image
                              if (issue.imageUrl != null && issue.imageUrl!.isNotEmpty) ...[
                                const SizedBox(height: 16),
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(12),
                                  child: Image.network(
                                    issue.imageUrl!,
                                    height: 160,
                                    width: double.infinity,
                                    fit: BoxFit.cover,
                                    // Gracefully handle 404s or network failures
                                    errorBuilder: (context, error, stackTrace) {
                                      return Container(
                                        height: 160,
                                        width: double.infinity,
                                        color: const Color(0xFFF1F5F9), // slate-100
                                        child: Column(
                                          mainAxisAlignment: MainAxisAlignment.center,
                                          children: [
                                            Icon(Icons.broken_image_outlined, color: Color(0xFF94A3B8), size: 32),
                                            const SizedBox(height: 8),
                                            Text(
                                              context.tr('Image unavailable'),
                                              style: TextStyle(color: Color(0xFF64748B), fontSize: 12),
                                            ),
                                          ],
                                        ),
                                      );
                                    },
                                  ),
                                ),
                              ],
                              
                              const SizedBox(height: 16),
                              const Divider(color: Color(0xFFF1F5F9), height: 1),
                              const SizedBox(height: 12),
                              
                              // Footer: Location
                              Row(
                                children: [
                                  const Icon(Icons.location_on_outlined, size: 16, color: Color(0xFF64748B)),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      issue.location,
                                      style: const TextStyle(color: Color(0xFF64748B), fontSize: 13, fontWeight: FontWeight.w500),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  );
                },
              ),
            ),
    );
  }
}
