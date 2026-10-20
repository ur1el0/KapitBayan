import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';
import '../services/issue_service.dart';

class FieldReportsTab extends StatelessWidget {
  final bool isLoading;
  final List<IssueReport> reports;
  final Future<void> Function() onRefresh;
  final void Function(int reportId, String status) onUpdateStatus;
  final void Function(int reportId, String urgency) onUpdateUrgency;

  const FieldReportsTab({
    super.key,
    required this.isLoading,
    required this.reports,
    required this.onRefresh,
    required this.onUpdateStatus,
    required this.onUpdateUrgency,
  });

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(AppColors.primaryNavy),
        ),
      );
    }

    if (reports.isEmpty) {
      return RefreshIndicator(
        onRefresh: onRefresh,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(32),
          child: SizedBox(
            width: double.infinity,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SizedBox(height: 40),
                Icon(
                  Icons.check_circle_outline_rounded,
                  size: 48,
                  color: Colors.green.shade400,
                ),
                const SizedBox(height: 12),
                const Text(
                  'No active community issues',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
                const SizedBox(height: 6),
                const Text(
                  'All citizen reports in your barangay are resolved.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Color(0xFF64748B), fontSize: 13),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: reports.length,
        separatorBuilder: (_, _) => const SizedBox(height: 14),
        itemBuilder: (context, index) => _FieldReportCard(
          report: reports[index],
          onUpdateStatus: onUpdateStatus,
          onUpdateUrgency: onUpdateUrgency,
        ),
      ),
    );
  }
}

class _FieldReportCard extends StatelessWidget {
  final IssueReport report;
  final void Function(int reportId, String status) onUpdateStatus;
  final void Function(int reportId, String urgency) onUpdateUrgency;

  const _FieldReportCard({
    required this.report,
    required this.onUpdateStatus,
    required this.onUpdateUrgency,
  });

  void _showPhoto(BuildContext context, String imageUrl) {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => Dialog(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Report photo',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Close photo',
                    onPressed: () => Navigator.of(dialogContext).pop(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              SizedBox(
                height: MediaQuery.sizeOf(dialogContext).height * 0.6,
                width: double.infinity,
                child: InteractiveViewer(
                  child: Image.network(
                    imageUrl,
                    fit: BoxFit.contain,
                    semanticLabel: 'Photo for report ${report.title}',
                    errorBuilder: (_, _, _) => const Center(
                      child: Text('Report photo could not be loaded.'),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isResolved = report.status.toUpperCase() == 'RESOLVED';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
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
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: isResolved
                      ? const Color(0xFFECFDF5)
                      : const Color(0xFFFEF3C7),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  report.status.toUpperCase(),
                  style: TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w800,
                    color: isResolved
                        ? const Color(0xFF059669)
                        : const Color(0xFFD97706),
                  ),
                ),
              ),
              Text(
                report.category,
                style: const TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF64748B),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _UrgencyBadge(urgency: report.urgency),
              const Spacer(),
              PopupMenuButton<String>(
                tooltip: 'Change urgency',
                onSelected: (urgency) => onUpdateUrgency(report.id, urgency),
                itemBuilder: (context) => const [
                  PopupMenuItem(value: 'EMERGENCY', child: Text('Emergency')),
                  PopupMenuItem(value: 'HAZARD', child: Text('Hazard')),
                  PopupMenuItem(value: 'MODERATE', child: Text('Moderate')),
                  PopupMenuItem(value: 'MINOR', child: Text('Minor')),
                ],
                child: const Padding(
                  padding: EdgeInsets.all(8),
                  child: Icon(Icons.edit_outlined, size: 18),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            report.title,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            report.description,
            style: const TextStyle(fontSize: 13, color: Color(0xFF475569)),
          ),
          if (report.imageUrl?.trim().isNotEmpty ?? false) ...[
            const SizedBox(height: 12),
            Semantics(
              button: true,
              label: 'View photo for report ${report.title}',
              child: InkWell(
                onTap: () => _showPhoto(context, report.imageUrl!),
                borderRadius: BorderRadius.circular(12),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.network(
                    report.imageUrl!,
                    height: 160,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    semanticLabel: 'Photo for report ${report.title}',
                    errorBuilder: (_, _, _) => Container(
                      height: 160,
                      width: double.infinity,
                      color: const Color(0xFFF1F5F9),
                      alignment: Alignment.center,
                      child: const Text('Report photo could not be loaded.'),
                    ),
                  ),
                ),
              ),
            ),
          ],
          const SizedBox(height: 10),
          Row(
            children: [
              const Icon(
                Icons.location_on_outlined,
                size: 14,
                color: AppColors.accentBlue,
              ),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  report.location,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF64748B),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              if (!isResolved) ...[
                OutlinedButton(
                  onPressed: () => onUpdateStatus(report.id, 'IN_PROGRESS'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  child: const Text(
                    'In-Progress',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () => onUpdateStatus(report.id, 'RESOLVED'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF10B981),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  child: const Text(
                    'Resolve',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

class _UrgencyBadge extends StatelessWidget {
  final String urgency;

  const _UrgencyBadge({required this.urgency});

  @override
  Widget build(BuildContext context) {
    final normalized = urgency.toUpperCase();
    final color = switch (normalized) {
      'EMERGENCY' => const Color(0xFFB91C1C),
      'HAZARD' => const Color(0xFFC2410C),
      'MODERATE' => const Color(0xFFB45309),
      _ => const Color(0xFF1D4ED8),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        normalized,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.3,
        ),
      ),
    );
  }
}
