import 'package:flutter/material.dart';
import '../core/localization/app_language.dart';

typedef QueueTicketSubmit =
    Future<void> Function({
      required String serviceType,
      required String? notes,
    });

class RequestQueueTicketSheet extends StatefulWidget {
  final bool isSubmitting;
  final QueueTicketSubmit onSubmit;

  const RequestQueueTicketSheet({
    super.key,
    required this.isSubmitting,
    required this.onSubmit,
  });

  @override
  State<RequestQueueTicketSheet> createState() =>
      _RequestQueueTicketSheetState();
}

class _RequestQueueTicketSheetState extends State<RequestQueueTicketSheet> {
  static const _services = [
    'Document Issuance',
    'Barangay Clearance',
    'Business Permit',
    'Tax Clearance',
    'General Inquiry',
  ];

  final _notesController = TextEditingController();
  String _serviceType = 'Document Issuance';

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final notes = _notesController.text;
    Navigator.pop(context);
    await widget.onSubmit(
      serviceType: _serviceType,
      notes: notes.isNotEmpty ? notes : null,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                context.tr('Request Queue Ticket'),
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF0F172A),
                ),
              ),
              IconButton(
                tooltip: context.tr('Close'),
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            context.tr('Select Service'),
            style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            initialValue: _serviceType,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              contentPadding: EdgeInsets.symmetric(
                horizontal: 12,
                vertical: 14,
              ),
            ),
            items: _services
                .map(
                  (service) => DropdownMenuItem(
                    value: service,
                    child: Text(context.tr(service)),
                  ),
                )
                .toList(),
            onChanged: widget.isSubmitting
                ? null
                : (value) {
                    if (value != null) setState(() => _serviceType = value);
                  },
          ),
          const SizedBox(height: 16),
          Text(
            context.tr('Barangay staff verify priority lane eligibility. If you qualify, ask the service desk to review your waiting ticket.'),
            style: TextStyle(
              color: Color(0xFF475569),
              fontSize: 13,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _notesController,
            enabled: !widget.isSubmitting,
            decoration: InputDecoration(
              labelText: context.tr('Additional Notes (Optional)'),
              hintText: context.tr('e.g. Requesting 2 copies'),
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF0047BA),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onPressed: widget.isSubmitting ? null : _submit,
              child: Text(
                context.tr('Get Ticket'),
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
