import 'package:flutter/material.dart';
import '../core/localization/app_language.dart';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../services/issue_service.dart';
import '../services/storage_service.dart';
import '../widgets/offline_snapshot_banner.dart';

class MyIssuesScreen extends StatefulWidget {
  final IssueService? issueService;

  const MyIssuesScreen({super.key, this.issueService});

  @override
  State<MyIssuesScreen> createState() => _MyIssuesScreenState();
}

class _MyIssuesScreenState extends State<MyIssuesScreen> {
  static const int _pageSize = IssueService.defaultPageSize;

  static const List<MapEntry<String, String>> _statusOptions = [
    MapEntry('ALL', 'All'),
    MapEntry('PENDING', 'Pending'),
    MapEntry('IN_PROGRESS', 'In Progress'),
    MapEntry('RESOLVED', 'Resolved'),
    MapEntry('REJECTED', 'Rejected'),
  ];

  static const List<MapEntry<String, String>> _categoryOptions = [
    MapEntry('ALL', 'All Categories'),
    MapEntry('PEACE_AND_ORDER', 'Peace and Order'),
    MapEntry('PUBLIC_HEALTH', 'Public Health'),
    MapEntry('INFRASTRUCTURE', 'Infrastructure'),
    MapEntry('ENVIRONMENT', 'Environment'),
    MapEntry('OTHER', 'Other'),
  ];

  IssueService? _issueService;
  Future<PaginatedIssueResult>? _issuesFuture;
  final TextEditingController _searchController = TextEditingController();
  String _selectedStatus = 'ALL';
  String _selectedCategory = 'ALL';
  String _searchQuery = '';
  int _currentPage = 1;

  @override
  void initState() {
    super.initState();
    if (widget.issueService != null) {
      _issueService = widget.issueService;
      _issuesFuture = _fetchPage();
    } else {
      _initService();
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _initService() async {
    final storage = await StorageService.init();
    final apiClient = ApiClient();
    final token = storage.getAccessToken();
    if (token != null) {
      apiClient.setAuthCredentials(accessToken: token);
    }
    if (!mounted) return;
    setState(() {
      _issueService = IssueService(
        apiClient: apiClient,
        storageService: storage,
      );
      _issuesFuture = _fetchPage();
    });
  }

  Future<PaginatedIssueResult> _fetchPage() {
    return _issueService!.getMyIssuesPage(
      page: _currentPage,
      pageSize: _pageSize,
      statusFilter: _selectedStatus,
      categoryFilter: _selectedCategory,
      search: _searchQuery,
    );
  }

  Future<void> _refresh() async {
    if (_issueService != null) {
      setState(() {
        _issuesFuture = _fetchPage();
      });
    }
  }

  void _applyFilters({
    String? status,
    String? category,
    String? search,
  }) {
    if (_issueService == null) return;
    setState(() {
      if (status != null) _selectedStatus = status;
      if (category != null) _selectedCategory = category;
      if (search != null) _searchQuery = search;
      _currentPage = 1;
      _issuesFuture = _fetchPage();
    });
  }

  void _goToPage(int page) {
    if (_issueService == null || page < 1) return;
    setState(() {
      _currentPage = page;
      _issuesFuture = _fetchPage();
    });
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

  // Helper to format the ISO timestamp from Django with date and time
  String _formatDate(String isoString) {
    try {
      final date = DateTime.parse(isoString).toLocal();
      final months = [
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
        'Dec',
      ];
      final hour12 = date.hour % 12 == 0 ? 12 : date.hour % 12;
      final minute = date.minute.toString().padLeft(2, '0');
      final period = date.hour >= 12 ? 'PM' : 'AM';
      return "${months[date.month - 1]} ${date.day}, ${date.year} · $hour12:$minute $period";
    } catch (e) {
      return isoString;
    }
  }

  Widget _buildFilterControls() {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchController,
                  textInputAction: TextInputAction.search,
                  onSubmitted: (val) => _applyFilters(search: val),
                  decoration: InputDecoration(
                    hintText: context.tr('Search reports...'),
                    prefixIcon: const Icon(Icons.search, size: 18),
                    suffixIcon: _searchQuery.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear, size: 18),
                            onPressed: () {
                              _searchController.clear();
                              _applyFilters(search: '');
                            },
                          )
                        : null,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              DropdownButtonHideUnderline(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  decoration: BoxDecoration(
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: DropdownButton<String>(
                    value: _selectedCategory,
                    isDense: true,
                    items: _categoryOptions
                        .map(
                          (entry) => DropdownMenuItem(
                            value: entry.key,
                            child: Text(
                              context.tr(entry.value),
                              style: const TextStyle(fontSize: 12),
                            ),
                          ),
                        )
                        .toList(),
                    onChanged: (val) {
                      if (val != null) _applyFilters(category: val);
                    },
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _statusOptions.map((entry) {
                final isSelected = _selectedStatus == entry.key;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(
                      context.tr(entry.value),
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: isSelected
                            ? Colors.white
                            : const Color(0xFF475569),
                      ),
                    ),
                    selected: isSelected,
                    selectedColor: const Color(0xFF0047BA),
                    backgroundColor: const Color(0xFFF1F5F9),
                    onSelected: (_) => _applyFilters(status: entry.key),
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPaginationBar(PaginatedIssueResult pageData) {
    return Container(
      margin: const EdgeInsets.only(top: 4, bottom: 20),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            'Page ${pageData.page} of ${pageData.totalPages} (${pageData.totalCount} total)',
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: Color(0xFF475569),
            ),
          ),
          Row(
            children: [
              TextButton(
                onPressed: pageData.hasPrevious
                    ? () => _goToPage(pageData.page - 1)
                    : null,
                child: Text(context.tr('Previous')),
              ),
              const SizedBox(width: 4),
              ElevatedButton(
                onPressed: pageData.hasNext
                    ? () => _goToPage(pageData.page + 1)
                    : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0047BA),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                ),
                child: Text(context.tr('Next')),
              ),
            ],
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC), // slate-50 background
      appBar: AppBar(
        title: Text(
          context.tr('My Report History'),
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: Color(0xFF0F172A),
            fontSize: 20,
          ),
        ),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: Color(0xFF0F172A)),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(
            color: const Color(0xFFE2E8F0),
            height: 1,
          ), // subtle bottom border
        ),
      ),
      body: _issueService == null || _issuesFuture == null
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                _buildFilterControls(),
                const Divider(height: 1, color: Color(0xFFE2E8F0)),
                Expanded(
                  child: RefreshIndicator(
                    onRefresh: _refresh,
                    color: const Color(0xFF2563EB),
                    child: FutureBuilder<PaginatedIssueResult>(
                      future: _issuesFuture,
                      builder: (context, snapshot) {
                        if (snapshot.connectionState == ConnectionState.waiting) {
                          return const Center(
                            child: CircularProgressIndicator(
                              color: Color(0xFF2563EB),
                            ),
                          );
                        } else if (snapshot.hasError) {
                          return ListView(
                            physics: const AlwaysScrollableScrollPhysics(),
                            padding: const EdgeInsets.all(16),
                            children: [
                              if (snapshot.error is NetworkException)
                                OfflineSnapshotBanner(
                                  message:
                                      'Could not refresh report history. Reconnect and refresh before relying on saved statuses.',
                                ),
                              Text(
                                context.tr('Could not load reports.'),
                                style: const TextStyle(color: Colors.red),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          );
                        } else if (!snapshot.hasData ||
                            snapshot.data!.items.isEmpty) {
                          return ListView(
                            physics: const AlwaysScrollableScrollPhysics(),
                            padding: const EdgeInsets.all(16),
                            children: [
                              if (_issueService!.lastIssuesUsedOfflineSnapshot)
                                OfflineSnapshotBanner(
                                  savedAt: _issueService!.lastSnapshotSavedAt,
                                ),
                              const SizedBox(height: 60),
                              const Icon(
                                Icons.assignment_outlined,
                                size: 64,
                                color: Color(0xFFCBD5E1),
                              ),
                              const SizedBox(height: 16),
                              Text(
                                context.tr(
                                  _selectedStatus != 'ALL' ||
                                          _selectedCategory != 'ALL' ||
                                          _searchQuery.isNotEmpty
                                      ? 'No matching reports found.'
                                      : 'No reports submitted yet.',
                                ),
                                style: const TextStyle(
                                  color: Color(0xFF64748B),
                                  fontSize: 16,
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          );
                        }

                        final pageData = snapshot.data!;
                        final issues = pageData.items;
                        final showOfflineBanner =
                            _issueService!.lastIssuesUsedOfflineSnapshot ||
                            pageData.usedOfflineSnapshot;
                        final offset = showOfflineBanner ? 1 : 0;

                        return ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: issues.length + offset + 1,
                          itemBuilder: (context, index) {
                            if (showOfflineBanner && index == 0) {
                              return OfflineSnapshotBanner(
                                savedAt:
                                    pageData.snapshotSavedAt ??
                                    _issueService!.lastSnapshotSavedAt,
                              );
                            }
                            if (index == issues.length + offset) {
                              return _buildPaginationBar(pageData);
                            }
                            final issue = issues[index - offset];
                            final statusColor = _getStatusColor(issue.status);

                      return Container(
                        margin: const EdgeInsets.only(bottom: 16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(
                                0xFF0F172A,
                              ).withValues(alpha: 0.04),
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
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
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
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 10,
                                      vertical: 4,
                                    ),
                                    decoration: BoxDecoration(
                                      color: statusColor.withValues(alpha: 0.1),
                                      borderRadius: BorderRadius.circular(20),
                                      border: Border.all(
                                        color: statusColor.withValues(
                                          alpha: 0.2,
                                        ),
                                      ),
                                    ),
                                    child: Text(
                                      context.tr(
                                        issue.status.replaceAll('_', ' '),
                                      ),
                                      style: TextStyle(
                                        color: statusColor,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 10,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),

                              // Title
                              Text(
                                issue.title,
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                  color: Color(0xFF0F172A),
                                ),
                              ),
                              const SizedBox(height: 6),

                              // Description
                              Text(
                                issue.description,
                                style: const TextStyle(
                                  color: Color(0xFF475569),
                                  height: 1.4,
                                  fontSize: 14,
                                ),
                              ),

                              // Optional Image
                              if (issue.imageUrl != null &&
                                  issue.imageUrl!.isNotEmpty) ...[
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
                                        color: const Color(
                                          0xFFF1F5F9,
                                        ), // slate-100
                                        child: Column(
                                          mainAxisAlignment:
                                              MainAxisAlignment.center,
                                          children: [
                                            Icon(
                                              Icons.broken_image_outlined,
                                              color: Color(0xFF94A3B8),
                                              size: 32,
                                            ),
                                            const SizedBox(height: 8),
                                            Text(
                                              context.tr('Image unavailable'),
                                              style: TextStyle(
                                                color: Color(0xFF64748B),
                                                fontSize: 12,
                                              ),
                                            ),
                                          ],
                                        ),
                                      );
                                    },
                                  ),
                                ),
                              ],

                              const SizedBox(height: 16),
                              const Divider(
                                color: Color(0xFFF1F5F9),
                                height: 1,
                              ),
                              const SizedBox(height: 12),

                              // Footer: Location
                              Row(
                                children: [
                                  const Icon(
                                    Icons.location_on_outlined,
                                    size: 16,
                                    color: Color(0xFF64748B),
                                  ),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      issue.location,
                                      style: const TextStyle(
                                        color: Color(0xFF64748B),
                                        fontSize: 13,
                                        fontWeight: FontWeight.w500,
                                      ),
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
          ),
        ],
      ),
    );
  }
}
