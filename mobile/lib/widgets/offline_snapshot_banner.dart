import 'package:flutter/material.dart';

import '../core/localization/app_language.dart';

class OfflineSnapshotBanner extends StatelessWidget {
  final DateTime? savedAt;
  final bool truncated;
  final String? message;

  const OfflineSnapshotBanner({
    super.key,
    this.savedAt,
    this.truncated = false,
    this.message,
  });

  @override
  Widget build(BuildContext context) {
    final localizations = MaterialLocalizations.of(context);
    final savedDate = savedAt?.toLocal();
    final updatedText = savedDate == null
        ? null
        : '${context.tr('Saved copy updated')}: ${localizations.formatMediumDate(savedDate)}';

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7E6),
        border: Border.all(color: const Color(0xFFF4D38A)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.wifi_off_rounded, color: Color(0xFF946200)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.tr(
                    message ??
                        'Offline: showing saved information that may be out of date.',
                  ),
                  style: const TextStyle(
                    color: Color(0xFF694900),
                    fontWeight: FontWeight.w700,
                  ),
                ),
                if (updatedText != null) ...[
                  const SizedBox(height: 3),
                  Text(
                    updatedText,
                    style: const TextStyle(color: Color(0xFF694900)),
                  ),
                ],
                if (truncated) ...[
                  const SizedBox(height: 3),
                  Text(
                    context.tr(
                      'Only the 100 most recent requests are saved for offline viewing.',
                    ),
                    style: const TextStyle(color: Color(0xFF694900)),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
