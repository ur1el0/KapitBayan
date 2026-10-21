import 'package:flutter/material.dart';

import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';

class EmptyDocumentRequests extends StatelessWidget {
  final String searchQuery;

  const EmptyDocumentRequests({super.key, required this.searchQuery});

  @override
  Widget build(BuildContext context) {
    final isSearching = searchQuery.isNotEmpty;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFF1F5F9), width: 1.2),
      ),
      child: Column(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: const BoxDecoration(
              color: Color(0xFFF1F5F9),
              shape: BoxShape.circle,
            ),
            child: const Center(
              child: Icon(
                Icons.folder_open_rounded,
                color: Color(0xFF64748B),
                size: 26,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            isSearching
                ? '${context.tr('No requests matching')} "$searchQuery"'
                : context.tr('No active document requests'),
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            isSearching
                ? context.tr('Try adjusting your search query or clear the filter.')
                : context.tr('Tap any certificate above to submit a new request.'),
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }
}
