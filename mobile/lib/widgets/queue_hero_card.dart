import 'package:flutter/material.dart';
import '../core/localization/app_language.dart';

/// Primary hero card displaying the currently served queue ticket at the counter
class QueueHeroCard extends StatelessWidget {
  final String? currentTicket;
  final String serviceType;
  final String location;

  const QueueHeroCard({
    super.key,
    required this.currentTicket,
    this.serviceType = 'Document Issuance',
    this.location = 'Barangay Office',
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 26.0),
      decoration: BoxDecoration(
        color: const Color(0xFF0A3E82),
        borderRadius: BorderRadius.circular(26),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0A3E82).withValues(alpha: 0.25),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top Row: Status Tag + Live Broadcast Indicator
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  context.tr('CURRENTLY AT COUNTER'),
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 10.5,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.8,
                  ),
                ),
              ),
              const Icon(
                Icons.sensors_rounded,
                color: Colors.white,
                size: 24,
              ),
            ],
          ),

          const SizedBox(height: 22),

          // Main Serving Ticket Identifier
          Text(
            currentTicket ?? '---',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 54,
              fontWeight: FontWeight.w900,
              letterSpacing: -1.2,
              height: 1.0,
            ),
          ),

          const SizedBox(height: 10),

          // Service Description
          Text(
            serviceType,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.1,
            ),
          ),

          const SizedBox(height: 6),

          // Location Tag
          Row(
            children: [
              Icon(
                Icons.location_on_outlined,
                color: Colors.white.withValues(alpha: 0.75),
                size: 15,
              ),
              const SizedBox(width: 4),
              Text(
                location,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.8),
                  fontSize: 13.5,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
