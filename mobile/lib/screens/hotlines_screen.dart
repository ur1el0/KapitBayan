import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/config/app_config.dart';
import '../core/network/api_client.dart';
import '../core/theme/app_colors.dart';
import '../models/hotline_model.dart';
import '../services/hotline_caller.dart';
import '../services/hotline_services.dart';
import '../services/storage_service.dart';

class HotlinesScreen extends StatefulWidget {
  const HotlinesScreen({super.key});

  @override
  State<HotlinesScreen> createState() => _HotlinesScreenState();
}

class _HotlinesScreenState extends State<HotlinesScreen> {
  final HotlineCaller _hotlineCaller = HotlineCaller();
  HotlineService? _service;
  List<HotlineModel> _hotlines = [];
  String _selectedCategory = 'ALL';
  String _searchQuery = '';
  bool _isLoading = true;

  // National emergency defaults so residents are NEVER without help
  static final List<HotlineModel> _nationalFallbacks = [
    HotlineModel(
      id: 901,
      name: 'National Emergency Hotline',
      number: '911',
      category: 'MEDICAL',
      categoryDisplay: 'Emergency Services',
      isActive: true,
    ),
    HotlineModel(
      id: 902,
      name: 'Philippine National Police (PNP)',
      number: '117',
      category: 'POLICE',
      categoryDisplay: 'Police Department',
      isActive: true,
    ),
    HotlineModel(
      id: 903,
      name: 'Bureau of Fire Protection (BFP)',
      number: '(02) 8426-0219',
      category: 'FIRE',
      categoryDisplay: 'Fire Department',
      isActive: true,
    ),
    HotlineModel(
      id: 904,
      name: 'Philippine Red Cross',
      number: '143',
      category: 'MEDICAL',
      categoryDisplay: 'Ambulance & Rescue',
      isActive: true,
    ),
  ];

  @override
  void initState() {
    super.initState();
    _initializeAndLoad();
  }

  Future<void> _initializeAndLoad() async {
    try {
      final storage = await StorageService.init();
      final client = ApiClient(baseUrl: AppConfig.baseUrl);
      final token = storage.getAccessToken();
      if (token != null) {
        client.setAuthCredentials(accessToken: token);
      }
      _service = HotlineService(apiClient: client);
      await _loadHotlines();
    } catch (_) {
      if (mounted) {
        setState(() {
          _hotlines = _nationalFallbacks;
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _loadHotlines() async {
    if (_service == null) return;
    try {
      final data = await _service!.fetchHotlines();
      if (mounted) {
        setState(() {
          _hotlines = data.isNotEmpty ? data : _nationalFallbacks;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _hotlines = _nationalFallbacks;
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _makePhoneCall(String phoneNumber) async {
    var launched = false;
    try {
      launched = await _hotlineCaller.call(phoneNumber);
    } catch (_) {
      // Phone handlers can be unavailable or reject the URI on this device.
    }

    if (!launched && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not launch phone dialer')),
      );
    }
  }

  Color _categoryColor(String category) {
    switch (category.toUpperCase()) {
      case 'POLICE':
        return const Color(0xFF1D4ED8);
      case 'FIRE':
        return const Color(0xFFEA580C);
      case 'MEDICAL':
        return const Color(0xFF059669);
      case 'BARANGAY':
        return const Color(0xFF4F46E5);
      default:
        return const Color(0xFF475569);
    }
  }

  IconData _categoryIcon(String category) {
    switch (category.toUpperCase()) {
      case 'POLICE':
        return Icons.local_police_rounded;
      case 'FIRE':
        return Icons.local_fire_department_rounded;
      case 'MEDICAL':
        return Icons.local_hospital_rounded;
      case 'BARANGAY':
        return Icons.account_balance_rounded;
      default:
        return Icons.phone_rounded;
    }
  }

  List<HotlineModel> get _filteredHotlines {
    return _hotlines.where((h) {
      final matchesCategory = _selectedCategory == 'ALL' || h.category.toUpperCase() == _selectedCategory;
      final matchesSearch = _searchQuery.isEmpty ||
          h.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          h.number.contains(_searchQuery);
      return matchesCategory && matchesSearch;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final categories = ['ALL', 'POLICE', 'FIRE', 'MEDICAL', 'BARANGAY'];

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text(
          'Emergency Hotlines',
          style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
        ),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: Color(0xFF0F172A)),
      ),
      body: Column(
        children: [
          // Search & Filters Header
          Container(
            color: Colors.white,
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            child: Column(
              children: [
                // Search Field
                Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: TextField(
                    onChanged: (val) => setState(() => _searchQuery = val),
                    decoration: const InputDecoration(
                      hintText: 'Search hotlines, departments...',
                      hintStyle: TextStyle(fontSize: 13, color: Color(0xFF94A3B8)),
                      prefixIcon: Icon(Icons.search, size: 20, color: Color(0xFF64748B)),
                      border: InputBorder.none,
                      contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                
                // Category Filter Chips
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: categories.map((cat) {
                      final isSelected = _selectedCategory == cat;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(
                          label: Text(
                            cat == 'ALL' ? 'All Services' : cat,
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: isSelected ? Colors.white : const Color(0xFF475569),
                            ),
                          ),
                          selected: isSelected,
                          selectedColor: AppColors.primaryNavy,
                          backgroundColor: const Color(0xFFF1F5F9),
                          onSelected: (_) => setState(() => _selectedCategory = cat),
                        ),
                      );
                    }).toList(),
                  ),
                ),
              ],
            ),
          ),

          // Hotlines List
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _filteredHotlines.isEmpty
                    ? Center(
                        child: Text(
                          'No matching emergency contacts found.',
                          style: TextStyle(color: Colors.grey.shade500, fontSize: 14),
                        ),
                      )
                    : ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemCount: _filteredHotlines.length,
                        separatorBuilder: (_, _) => const SizedBox(height: 12),
                        itemBuilder: (context, index) {
                          final h = _filteredHotlines[index];
                          final color = _categoryColor(h.category);
                          return Container(
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: const Color(0xFFE2E8F0)),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.02),
                                  blurRadius: 6,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: ListTile(
                              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                              leading: Container(
                                width: 44,
                                height: 44,
                                decoration: BoxDecoration(
                                  color: color.withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Icon(_categoryIcon(h.category), color: color, size: 22),
                              ),
                              title: Text(
                                h.name,
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF0F172A)),
                              ),
                              subtitle: Text(
                                h.categoryDisplay,
                                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                              ),
                              trailing: Material(
                                color: Colors.transparent,
                                child: InkWell(
                                  onTap: () => _makePhoneCall(h.number),
                                  onLongPress: () {
                                    Clipboard.setData(ClipboardData(text: h.number));
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(content: Text('Number copied to clipboard')),
                                    );
                                  },
                                  borderRadius: BorderRadius.circular(10),
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                    decoration: BoxDecoration(
                                      color: color.withValues(alpha: 0.08),
                                      borderRadius: BorderRadius.circular(10),
                                      border: Border.all(color: color.withValues(alpha: 0.2)),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.call, color: color, size: 16),
                                        const SizedBox(width: 6),
                                        Text(
                                          h.number,
                                          style: TextStyle(
                                            color: color,
                                            fontWeight: FontWeight.bold,
                                            fontSize: 14,
                                            fontFamily: 'monospace',
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
