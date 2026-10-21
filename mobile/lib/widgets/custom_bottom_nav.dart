import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';
import '../core/localization/app_language.dart';

/// Floating pill bottom navigation bar matching reference design
class CustomBottomNav extends StatelessWidget {
  final int currentIndex;
  final Function(int) onTap;

  const CustomBottomNav({
    super.key,
    required this.currentIndex,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0F172A).withValues(alpha: 0.08),
            blurRadius: 20,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _NavItem(
              index: 0,
              selectedIndex: currentIndex,
              icon: Icons.grid_view_rounded,
              label: context.tr('DASHBOARD'),
              onTap: () => onTap(0),
            ),
            _NavItem(
              index: 1,
              selectedIndex: currentIndex,
              icon: Icons.confirmation_number_outlined,
              label: context.tr('QUEUE'),
              onTap: () => onTap(1),
            ),
            _NavItem(
              index: 2,
              selectedIndex: currentIndex,
              icon: Icons.description_outlined,
              label: context.tr('DOCUMENTS'),
              onTap: () => onTap(2),
            ),
            _NavItem(
              index: 3,
              selectedIndex: currentIndex,
              icon: Icons.calendar_today_outlined,
              label: context.tr('SCHEDULE'),
              onTap: () => onTap(3),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final int index;
  final int selectedIndex;
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _NavItem({
    required this.index,
    required this.selectedIndex,
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final bool isSelected = index == selectedIndex;

    final Widget visualItem;

    if (isSelected) {
      // Active tab: Solid dark navy capsule pill
      visualItem = GestureDetector(
        excludeFromSemantics: true,
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: AppColors.primaryNavy,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: Colors.white, size: 20),
              const SizedBox(height: 3),
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
        ),
      );
    } else {
      // Inactive tab: Vertical Icon + Label in muted slate
      visualItem = GestureDetector(
        excludeFromSemantics: true,
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: AppColors.textMuted, size: 20),
              const SizedBox(height: 3),
              Text(
                label,
                style: const TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Semantics(
      container: true,
      label: label,
      button: true,
      selected: isSelected,
      onTap: onTap,
      child: ExcludeSemantics(child: visualItem),
    );
  }
}
