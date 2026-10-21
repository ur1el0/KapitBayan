import 'package:flutter/material.dart';

import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';

class ResidentTutorialScreen extends StatelessWidget {
  const ResidentTutorialScreen({super.key});

  Widget _step({
    required BuildContext context,
    required int number,
    required String title,
    required String description,
    required IconData icon,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CircleAvatar(
              backgroundColor: AppColors.primaryNavy,
              foregroundColor: Colors.white,
              child: Text(
                '$number',
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(icon, color: AppColors.primaryNavy, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          title,
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(fontWeight: FontWeight.w800),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    description,
                    style: const TextStyle(fontSize: 16, height: 1.5),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(context.tr('How to use KapitBayan')),
        backgroundColor: Colors.white,
        foregroundColor: AppColors.primaryNavy,
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
        children: [
          Card(
            color: const Color(0xFFEAF2FF),
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.tr('A simple resident guide'),
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      color: AppColors.primaryNavy,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    context.tr('Take one step at a time. You can open this guide whenever you need it. Button names may vary a little between the mobile app and website.\n\nNew here? On the sign-in screen, choose Register as Resident and follow the instructions. If a message says your account needs review, follow the message or contact your Barangay before making another account. If you already have an account, sign in and start at your Dashboard.'),
                    style: TextStyle(fontSize: 16, height: 1.5),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          _step(
            context: context,
            number: 1,
            title: context.tr('Start at your Dashboard'),
            description: context.tr('After signing in, use the menu or service cards to choose what you need. You can return to the Dashboard whenever you want.'),
            icon: Icons.dashboard_outlined,
          ),
          _step(
            context: context,
            number: 2,
            title: context.tr('Request a document'),
            description: context.tr('Open Documents, choose the service you need, and follow the instructions. Review your information before sending. Return to Documents later to check the request status.'),
            icon: Icons.description_outlined,
          ),
          _step(
            context: context,
            number: 3,
            title: context.tr('Check queue and schedules'),
            description: context.tr('Open Queue for queue information. If your Barangay has posted an appointment or activity schedule, check the date, time, and location before going.'),
            icon: Icons.access_time,
          ),
          _step(
            context: context,
            number: 4,
            title: context.tr('Read community updates'),
            description: context.tr('Open Announcements to read community updates. Check the date and details, and confirm urgent information with your Barangay through a verified contact.'),
            icon: Icons.campaign_outlined,
          ),
          _step(
            context: context,
            number: 5,
            title: context.tr('Find other services'),
            description: context.tr('Use Assistance or Report Issue when you need those services. Follow the instructions shown. Local requirements and service availability can differ.'),
            icon: Icons.volunteer_activism_outlined,
          ),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.tr('Make the app easier and safer to use'),
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    context.tr('• To make text larger, use your phone’s text or display size setting.\n'
                    '• If you use a screen reader, turn on TalkBack in Android Accessibility settings and listen to button labels.\n'
                    '• A trusted person may help you read or navigate while you stay in control. Never share your password or one-time code (OTP).\n'
                    '• If something does not load, check your connection and try again. Check request status before sending the same request again.\n'
                    '• Confirm local eligibility, fees, required documents, and office hours with your Barangay.'),
                    style: TextStyle(fontSize: 16, height: 1.6),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
