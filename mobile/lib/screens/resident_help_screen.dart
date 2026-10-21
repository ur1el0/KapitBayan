import 'package:flutter/material.dart';

import '../core/localization/app_language.dart';
import '../core/network/api_client.dart';
import '../core/theme/app_colors.dart';
import '../models/faq_model.dart';
import '../services/faq_service.dart';
import 'resident_tutorial_screen.dart';

class ResidentHelpScreen extends StatefulWidget {
  final ApiClient apiClient;

  const ResidentHelpScreen({super.key, required this.apiClient});

  @override
  State<ResidentHelpScreen> createState() => _ResidentHelpScreenState();
}

class _ResidentHelpScreenState extends State<ResidentHelpScreen> {
  late final FAQService _faqService;
  final TextEditingController _searchController = TextEditingController();
  List<FAQModel> _faqs = const [];
  String _query = '';
  String _category = 'ALL';
  bool _isLoading = true;
  bool _hasError = false;

  @override
  void initState() {
    super.initState();
    _faqService = FAQService(apiClient: widget.apiClient);
    _loadFAQs();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadFAQs() async {
    setState(() {
      _isLoading = true;
      _hasError = false;
    });
    try {
      final faqs = await _faqService.fetchResidentFAQs();
      if (!mounted) return;
      setState(() {
        _faqs = faqs;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _faqs = const [];
        _hasError = true;
        _isLoading = false;
      });
    }
  }

  String _categoryLabel(String value) {
    switch (value) {
      case 'GETTING_STARTED':
        return 'Getting started';
      case 'ACCOUNT':
        return 'Account access';
      case 'DOCUMENTS':
        return 'Documents';
      case 'PAYMENTS':
        return 'Fees and payments';
      case 'QUEUE':
        return 'Queue and schedules';
      case 'ASSISTANCE':
        return 'Assistance and programs';
      case 'COMMUNITY':
        return 'Community notices';
      case 'ACCESSIBILITY':
        return 'Accessibility';
      case 'PRIVACY':
        return 'Privacy and safety';
      default:
        return 'Other';
    }
  }

  List<String> get _categories {
    final values = _faqs.map((faq) => faq.category).toSet().toList()..sort();
    return ['ALL', ...values];
  }

  List<FAQModel> get _visibleFAQs {
    final normalizedQuery = _query.trim().toLowerCase();
    return _faqs
        .where((faq) {
          final matchesQuery =
              normalizedQuery.isEmpty ||
              faq.question.toLowerCase().contains(normalizedQuery) ||
              faq.answer.toLowerCase().contains(normalizedQuery);
          return matchesQuery &&
              (_category == 'ALL' || faq.category == _category);
        })
        .toList(growable: false);
  }

  Widget _errorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.cloud_off_outlined,
              size: 42,
              color: AppColors.error,
            ),
            const SizedBox(height: 12),
            Text(
              context.tr('Help could not be loaded.'),
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            Text(
              context.tr('Check your internet connection and try again. If the problem continues, contact your Barangay using verified office information.'),
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 16,
                height: 1.5,
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _loadFAQs,
              icon: const Icon(Icons.refresh),
              label: Text(context.tr('Try again')),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final categories = _categories;
    final visibleFAQs = _visibleFAQs;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(context.tr('Help and FAQs')),
        backgroundColor: Colors.white,
        foregroundColor: AppColors.primaryNavy,
        elevation: 0,
        actions: [
          TextButton.icon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => const ResidentTutorialScreen(),
              ),
            ),
            icon: const Icon(Icons.menu_book_outlined),
            label: Text(context.tr('Tutorial')),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadFAQs,
        color: AppColors.primaryNavy,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
          children: [
            Text(
              context.tr('Find answers about your account and Barangay services. Local steps and programs can differ, so confirm current instructions with your Barangay.'),
              style: TextStyle(
                fontSize: 16,
                height: 1.5,
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _searchController,
              onChanged: (value) => setState(() => _query = value),
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                labelText: context.tr('Search help questions and answers'),
                hintText: context.tr('For example: request a document'),
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _query.isEmpty
                    ? null
                    : IconButton(
                        tooltip: context.tr('Clear search'),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _query = '');
                        },
                        icon: const Icon(Icons.clear),
                      ),
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
            ),
            if (!_isLoading && !_hasError && categories.length > 1) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: categories.map((category) {
                  final selected = _category == category;
                  return ChoiceChip(
                    label: Text(
                      category == 'ALL'
                          ? context.tr('All topics')
                          : context.tr(_categoryLabel(category)),
                    ),
                    selected: selected,
                    onSelected: (_) => setState(() => _category = category),
                    labelStyle: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: selected ? Colors.white : AppColors.textPrimary,
                    ),
                    selectedColor: AppColors.primaryNavy,
                    backgroundColor: Colors.white,
                  );
                }).toList(),
              ),
            ],
            const SizedBox(height: 12),
            if (_isLoading)
              const SizedBox(
                height: 160,
                child: Center(
                  child: CircularProgressIndicator(
                    color: AppColors.primaryNavy,
                  ),
                ),
              )
            else if (_hasError)
              _errorState()
            else if (visibleFAQs.isEmpty)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      const Icon(
                        Icons.help_outline,
                        size: 36,
                        color: AppColors.textMuted,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _faqs.isEmpty
                            ? context.tr('No FAQs are available yet.')
                            : context.tr('No answers match your search.'),
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        context.tr('For current local instructions, contact your Barangay office.'),
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 15, height: 1.5),
                      ),
                    ],
                  ),
                ),
              )
            else
              Card(
                clipBehavior: Clip.antiAlias,
                child: Column(
                  children: visibleFAQs.map((faq) {
                    return ExpansionTile(
                      key: PageStorageKey<int>(faq.id),
                      title: Text(
                        faq.question,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      subtitle: Text(_categoryLabel(faq.category)),
                      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                      expandedCrossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          faq.answer,
                          style: const TextStyle(
                            fontSize: 16,
                            height: 1.6,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    );
                  }).toList(),
                ),
              ),
            const SizedBox(height: 18),
            Card(
              color: const Color(0xFFEAF2FF),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.tr('Want a step-by-step guide?'),
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      context.tr('Open the simple tutorial for help finding services and using your account.'),
                      style: TextStyle(fontSize: 16, height: 1.5),
                    ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => const ResidentTutorialScreen(),
                        ),
                      ),
                      icon: const Icon(Icons.menu_book_outlined),
                      label: Text(context.tr('How to use KapitBayan')),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.shield_outlined, color: AppColors.primaryNavy),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        context.tr('Do not share your password, OTP, or identity documents in personal messages. Confirm local eligibility, fees, required documents, and office hours with your Barangay.'),
                        style: TextStyle(fontSize: 15, height: 1.5),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
