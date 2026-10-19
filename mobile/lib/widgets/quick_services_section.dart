import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';
import 'app_surface.dart';

/// Quick services section providing immediate access to common resident actions
class QuickServicesSection extends StatelessWidget {
  final VoidCallback? onRequestDocument;
  final VoidCallback? onReportIssue;
  final VoidCallback? onBarangayHotline;
  final VoidCallback? onMyReports;
  final VoidCallback? onRequestAid;
  final VoidCallback? onHelpFAQs;

  const QuickServicesSection({
    super.key,
    this.onRequestDocument,
    this.onReportIssue,
    this.onBarangayHotline,
    this.onMyReports,
    this.onRequestAid,
    this.onHelpFAQs,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Quick Services', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),

        // Row 1: Request Document & Report Issue
        Row(
          children: [
            Expanded(
              child: _QuickServiceCard(
                icon: Icons.description_outlined,
                title: 'Request Document',
                onTap: onRequestDocument,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _QuickServiceCard(
                icon: Icons.pest_control_outlined,
                title: 'Report Issue',
                onTap: onReportIssue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        _QuickServiceCard(
          icon: Icons.volunteer_activism_outlined,
          title: 'Request Assistance',
          onTap: onRequestAid,
        ),
        const SizedBox(height: 8),

        // Row 2: Barangay Hotline & My Reports
        Row(
          children: [
            Expanded(
              child: _QuickServiceCard(
                icon: Icons.phone_outlined,
                title: 'Barangay Hotline',
                onTap: onBarangayHotline,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _QuickServiceCard(
                icon: Icons.history_outlined,
                title: 'My Reports',
                onTap: onMyReports,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        _QuickServiceCard(
          icon: Icons.help_outline_rounded,
          title: 'Help & FAQs',
          onTap: onHelpFAQs,
        ),
      ],
    );
  }
}

class _QuickServiceCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final VoidCallback? onTap;

  const _QuickServiceCard({
    required this.icon,
    required this.title,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      // Keep the visible cards compact while preserving a generous full-card
      // tap target for residents using smaller phones.
      constraints: const BoxConstraints(minHeight: 80),
      child: AppSurface(
        onTap: onTap,
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                DecoratedBox(
                  decoration: BoxDecoration(
                    color: AppColors.primaryNavy.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: SizedBox(
                    width: 32,
                    height: 32,
                    child: Icon(icon, color: AppColors.primaryNavy, size: 18),
                  ),
                ),
                const Icon(
                  Icons.chevron_right_rounded,
                  size: 20,
                  color: AppColors.textMuted,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              title,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: AppColors.textPrimary,
                height: 1.25,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
