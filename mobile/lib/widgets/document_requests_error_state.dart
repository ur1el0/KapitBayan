import 'package:flutter/material.dart';

import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';

class DocumentRequestsErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  final bool retrying;

  const DocumentRequestsErrorState({
    super.key,
    required this.message,
    required this.onRetry,
    this.retrying = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFFECACA)),
      ),
      child: Column(
        children: [
          const Icon(
            Icons.cloud_off_outlined,
            color: Color(0xFFB91C1C),
            size: 28,
            semanticLabel: 'Unable to load document requests',
          ),
          const SizedBox(height: 10),
          Semantics(
            liveRegion: true,
            child: Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: retrying ? null : onRetry,
            icon: retrying
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh_rounded),
            label: Text(retrying ? context.tr('Trying again…') : context.tr('Try again')),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.primaryNavy,
              minimumSize: const Size(0, 48),
              padding: const EdgeInsets.symmetric(horizontal: 18),
              side: const BorderSide(color: AppColors.primaryNavy),
            ),
          ),
        ],
      ),
    );
  }
}
