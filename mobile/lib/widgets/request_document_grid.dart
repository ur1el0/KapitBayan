import 'package:flutter/material.dart';
import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';

/// Item definition for the Request New catalog
class RequestDocumentItem {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color iconBgColor;
  final Color iconColor;

  const RequestDocumentItem({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.iconBgColor,
    required this.iconColor,
  });
}

/// 2x2 grid representing the "Request New" section from reference UI
class RequestDocumentGrid extends StatelessWidget {
  final Function(String documentType) onSelectDocument;
  final VoidCallback? onViewAll;
  final String searchQuery;

  const RequestDocumentGrid({
    super.key,
    required this.onSelectDocument,
    this.onViewAll,
    this.searchQuery = '',
  });

  static const List<RequestDocumentItem> defaultItems = [
    RequestDocumentItem(
      title: 'Barangay\nClearance',
      subtitle: 'Standard residency proof',
      icon: Icons.verified_user_outlined,
      iconBgColor: Color(0xFFEEF2FF),
      iconColor: Color(0xFF4F46E5),
    ),
    RequestDocumentItem(
      title: 'Certificate of\nIndigency',
      subtitle: 'For social service aid',
      icon: Icons.volunteer_activism_outlined,
      iconBgColor: Color(0xFFFFEDD5),
      iconColor: Color(0xFFEA580C),
    ),
    RequestDocumentItem(
      title: 'Residency\nCertificate',
      subtitle: 'Address verification',
      icon: Icons.location_on_outlined,
      iconBgColor: Color(0xFFF1F5F9),
      iconColor: Color(0xFF475569),
    ),
    RequestDocumentItem(
      title: 'Business Permit',
      subtitle: 'Local trade registration',
      icon: Icons.storefront_outlined,
      iconBgColor: Color(0xFFEDE9FE),
      iconColor: Color(0xFF4338CA),
    ),
  ];

  @override
  Widget build(BuildContext context) {
    // Filter items if search query is provided
    final query = searchQuery.trim().toLowerCase();
    final items = query.isEmpty
        ? defaultItems
        : defaultItems.where((item) {
            final t = item.title.replaceAll('\n', ' ').toLowerCase();
            final s = item.subtitle.toLowerCase();
            return t.contains(query) || s.contains(query);
          }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section Header: "Request New" on left, "View All" on right
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              context.tr('Request New'),
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
                letterSpacing: -0.3,
              ),
            ),
            GestureDetector(
              onTap: onViewAll,
              child: Text(
                context.tr('View All'),
                style: TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF2563EB),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),

        if (items.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFF1F5F9), width: 1.2),
            ),
            child: Center(
              child: Text(
                context.tr('No matching certificate or permit type found.'),
                style: TextStyle(
                  fontSize: 13,
                  color: AppColors.textMuted,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          )
        else
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: items.length,
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              crossAxisSpacing: 14,
              mainAxisSpacing: 14,
              childAspectRatio: 1.05,
            ),
            itemBuilder: (context, index) {
              final item = items[index];
              return _RequestCard(
                item: item,
                onTap: () {
                  final cleanTitle = item.title.replaceAll('\n', ' ');
                  onSelectDocument(cleanTitle);
                },
              );
            },
          ),
      ],
    );
  }
}

class _RequestCard extends StatelessWidget {
  final RequestDocumentItem item;
  final VoidCallback onTap;

  const _RequestCard({
    required this.item,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0F172A).withValues(alpha: 0.03),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
        border: Border.all(
          color: const Color(0xFFF1F5F9),
          width: 1.2,
        ),
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(18),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(18),
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Icon pill box
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: item.iconBgColor,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Center(
                    child: Icon(
                      item.icon,
                      color: item.iconColor,
                      size: 22,
                    ),
                  ),
                ),

                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.tr(item.title),
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                        height: 1.2,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      context.tr(item.subtitle),
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textMuted,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
