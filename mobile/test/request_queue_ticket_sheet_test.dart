import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/widgets/request_queue_ticket_sheet.dart';

void main() {
  testWidgets('submits the selected service and optional notes', (
    tester,
  ) async {
    String? submittedService;
    String? submittedNotes;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () => showModalBottomSheet<void>(
                context: context,
                isScrollControlled: true,
                builder: (_) => RequestQueueTicketSheet(
                  isSubmitting: false,
                  onSubmit: ({required serviceType, required notes}) async {
                    submittedService = serviceType;
                    submittedNotes = notes;
                  },
                ),
              ),
              child: const Text('Open'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Other in-person service').last);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Two copies');
    await tester.tap(find.text('Get Ticket'));
    await tester.pumpAndSettle();

    expect(submittedService, 'Other in-person service');
    expect(submittedNotes, 'Two copies');
  });
}
