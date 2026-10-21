import 'package:flutter/material.dart';
import '../core/localization/app_language.dart';

/// Side-by-side metric summary cards displaying estimated wait time and live desk capacity
class QueueMetricCards extends StatelessWidget {
  final String? estimatedCallTime;
  final String liveCapacity;

  const QueueMetricCards({
    super.key,
    required this.estimatedCallTime,
    required this.liveCapacity,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        // 1. Estimated Call Card
        Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 16.0,
              vertical: 16.0,
            ),
            decoration: BoxDecoration(
              color: const Color(0xFFEFF4FA),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.access_time_rounded,
                  color: Color(0xFFF97316),
                  size: 22,
                ),
                const SizedBox(height: 12),
                Text(
                  context.tr('ESTIMATED CALL'),
                  style: TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 10.5,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.6,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  estimatedCallTime ?? context.tr('Not available'),
                  style: TextStyle(
                    color: Color(0xFF0F172A),
                    fontSize: estimatedCallTime == null ? 16 : 20,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.4,
                  ),
                ),
              ],
            ),
          ),
        ),

        const SizedBox(width: 14),

        // 2. Live Capacity Card
        Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 16.0,
              vertical: 16.0,
            ),
            decoration: BoxDecoration(
              color: const Color(0xFFFEECE6),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.info_outline_rounded,
                  color: Color(0xFFC2410C),
                  size: 22,
                ),
                const SizedBox(height: 12),
                Text(
                  context.tr('LIVE CAPACITY'),
                  style: TextStyle(
                    color: Color(0xFF9A3412),
                    fontSize: 10.5,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.6,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  liveCapacity,
                  style: const TextStyle(
                    color: Color(0xFF431407),
                    fontSize: 20,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.4,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
