import 'package:flutter/material.dart';
import '../models/user_model.dart';
import '../core/localization/app_language.dart';

/// Hero status banner displaying resident verification badge, dynamic greeting,
/// and review notice with deep navy gradient styling.
class ResidentHeroCard extends StatelessWidget {
  final UserModel? user;
  final int pendingCount;

  const ResidentHeroCard({
    super.key,
    this.user,
    this.pendingCount = 2,
  });

  @override
  Widget build(BuildContext context) {
    final String displayName = user != null && user!.fullName.isNotEmpty
        ? user!.fullName.split(' ').first
        : (user != null && user!.username.isNotEmpty ? user!.username : 'Citizen');

    final bool isVerified = user?.isVerified ?? true;

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF082B66),
            Color(0xFF0F4C81),
            Color(0xFF1B59B0),
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF082B66).withValues(alpha: 0.3),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Stack(
          children: [
            // Subtle geometric background watermark shapes
            Positioned(
              right: -20,
              bottom: -30,
              child: Opacity(
                opacity: 0.12,
                child: CustomPaint(
                  size: const Size(180, 180),
                  painter: _BuildingPatternPainter(),
                ),
              ),
            ),

            // Main Content
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: 24.0,
                vertical: 24.0,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Verification Tag
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        isVerified
                            ? context.tr('VERIFIED RESIDENT')
                            : context.tr('PENDING VERIFICATION'),
                        style: TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w700,
                          color: isVerified
                              ? const Color(0xFF93C5FD)
                              : const Color(0xFFFCD34D),
                          letterSpacing: 1.2,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),

                  // Greeting Headline
                  Text(
                    '${context.tr('Welcome back')}, $displayName',
                    style: const TextStyle(
                      fontSize: 22.0,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                      letterSpacing: -0.4,
                    ),
                  ),
                  const SizedBox(height: 8),

                  // Status & Pending Actions Subtitle
                  Text(
                    pendingCount > 0
                        ? '${context.tr('Your status is current. There are')} $pendingCount ${context.tr('pending actions for your review.')}'
                        : context.tr('Your status is current. All your records are up to date.'),
                    style: TextStyle(
                      fontSize: 13.5,
                      fontWeight: FontWeight.w400,
                      color: Colors.white.withValues(alpha: 0.85),
                      height: 1.35,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Custom painter for subtle architectural geometric watermark lines
class _BuildingPatternPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    final path = Path();
    // Skyscraper architectural lines
    path.moveTo(size.width * 0.2, size.height);
    path.lineTo(size.width * 0.2, size.height * 0.3);
    path.lineTo(size.width * 0.5, size.height * 0.1);
    path.lineTo(size.width * 0.8, size.height * 0.25);
    path.lineTo(size.width * 0.8, size.height);

    path.moveTo(size.width * 0.5, size.height * 0.1);
    path.lineTo(size.width * 0.5, size.height);

    path.moveTo(size.width * 0.35, size.height * 0.2);
    path.lineTo(size.width * 0.35, size.height);

    path.moveTo(size.width * 0.65, size.height * 0.18);
    path.lineTo(size.width * 0.65, size.height);

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
