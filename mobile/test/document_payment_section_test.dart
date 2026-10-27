import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/document_request_model.dart';
import 'package:mobile/models/payment_recipient_model.dart';
import 'package:mobile/widgets/document_payment_section.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  final mockRecipients = [
    const PaymentRecipientModel(
      id: 5,
      provider: 'GCASH',
      providerLabel: 'GCash',
      displayName: 'Treasury GCash',
      recipientName: 'Barangay Treasurer',
      recipientIdentifier: '0917-111-2222',
      instructions: 'Include request ID in transfer remarks.',
    ),
  ];

  group('DocumentPaymentSection Widget Tests', () {
    testWidgets('renders processing banner when request is PROCESSING', (
      tester,
    ) async {
      final request = DocumentRequestModel(
        id: 101,
        documentType: 'Barangay Clearance',
        status: 'PROCESSING',
        feeAmount: 50.0,
        feeAssessmentStatus: 'ASSESSED',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DocumentPaymentSection(
              request: request,
              canSubmitElectronicPayment: false,
              isLoadingRecipients: false,
              recipientError: null,
              recipients: mockRecipients,
              selectedRecipientId: null,
              referenceController: TextEditingController(),
              isSubmitting: false,
              onPaymentChoiceChanged: (_) {},
              onSubmitPaymentReference: () {},
            ),
          ),
        ),
      );

      expect(
        find.text('Payment Unavailable During Processing'),
        findsOneWidget,
      );
      expect(
        find.textContaining('Payment submission unlocks once marked READY FOR PICKUP'),
        findsOneWidget,
      );
      expect(
        find.textContaining('Assessed fee: ₱50.00'),
        findsOneWidget,
      );
    });

    testWidgets('ordinary zero fee stays pending assessment during processing', (
      tester,
    ) async {
      final request = DocumentRequestModel(
        id: 110,
        documentType: 'Barangay Clearance',
        status: 'PROCESSING',
        feeAmount: 0.0,
        paymentStatus: 'NOT_REQUIRED',
        feeAssessmentStatus: 'AWAITING_ASSESSMENT',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DocumentPaymentSection(
              request: request,
              canSubmitElectronicPayment: false,
              isLoadingRecipients: false,
              recipientError: null,
              recipients: mockRecipients,
              selectedRecipientId: null,
              referenceController: TextEditingController(),
              isSubmitting: false,
              onPaymentChoiceChanged: (_) {},
              onSubmitPaymentReference: () {},
            ),
          ),
        ),
      );

      expect(find.text('Payment Unavailable During Processing'), findsOneWidget);
      expect(
        find.textContaining('Fee is awaiting staff assessment'),
        findsOneWidget,
      );
      expect(find.text('Statutory Fee Exemption (₱0.00)'), findsNothing);
      expect(request.isFeeExempt, isFalse);
    });

    testWidgets('renders staff waiver banner when fee is waived', (
      tester,
    ) async {
      final request = DocumentRequestModel(
        id: 112,
        documentType: 'Barangay Clearance',
        status: 'READY_FOR_PICKUP',
        feeAmount: 0.0,
        paymentStatus: 'NOT_REQUIRED',
        feeAssessmentStatus: 'WAIVED',
        feeWaiverReason: 'Indigent family member recommendation approved.',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DocumentPaymentSection(
              request: request,
              canSubmitElectronicPayment: false,
              isLoadingRecipients: false,
              recipientError: null,
              recipients: mockRecipients,
              selectedRecipientId: null,
              referenceController: TextEditingController(),
              isSubmitting: false,
              onPaymentChoiceChanged: (_) {},
              onSubmitPaymentReference: () {},
            ),
          ),
        ),
      );

      expect(find.text('Fee Waived (₱0.00) — Staff Approved'), findsOneWidget);
      expect(
        find.text('Reason: Indigent family member recommendation approved.'),
        findsOneWidget,
      );
      expect(find.text('Select Payment Channel'), findsNothing);
    });

    testWidgets('ordinary zero fee after assessment has no statutory claim', (
      tester,
    ) async {
      final request = DocumentRequestModel(
        id: 111,
        documentType: 'Barangay Clearance',
        status: 'READY_FOR_PICKUP',
        feeAmount: 0.0,
        paymentStatus: 'NOT_REQUIRED',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DocumentPaymentSection(
              request: request,
              canSubmitElectronicPayment: false,
              isLoadingRecipients: false,
              recipientError: null,
              recipients: mockRecipients,
              selectedRecipientId: null,
              referenceController: TextEditingController(),
              isSubmitting: false,
              onPaymentChoiceChanged: (_) {},
              onSubmitPaymentReference: () {},
            ),
          ),
        ),
      );

      expect(find.text('No payment required'), findsOneWidget);
      expect(find.text('Statutory Fee Exemption (₱0.00)'), findsNothing);
    });

    testWidgets('renders cash instructions banner when paymentMethod is CASH', (
      tester,
    ) async {
      final request = DocumentRequestModel(
        id: 102,
        documentType: 'Barangay Clearance',
        status: 'READY_FOR_PICKUP',
        feeAmount: 50.0,
        paymentMethod: 'CASH',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DocumentPaymentSection(
              request: request,
              canSubmitElectronicPayment: false,
              isLoadingRecipients: false,
              recipientError: null,
              recipients: mockRecipients,
              selectedRecipientId: null,
              referenceController: TextEditingController(),
              isSubmitting: false,
              onPaymentChoiceChanged: (_) {},
              onSubmitPaymentReference: () {},
            ),
          ),
        ),
      );

      expect(find.text('Cash Payment at Barangay Hall'), findsOneWidget);
      expect(
        find.textContaining('Please proceed to the Barangay Treasurer desk to settle your fee'),
        findsOneWidget,
      );
    });

    testWidgets('offers cash before configured barangay e-payment options', (
      tester,
    ) async {
      String? selectedChoice;
      final request = DocumentRequestModel(
        id: 120,
        documentType: 'Barangay Clearance',
        status: 'READY_FOR_PICKUP',
        feeAmount: 50.0,
        paymentStatus: 'UNPAID',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DocumentPaymentSection(
              request: request,
              canChoosePayment: true,
              selectedPaymentChoice: null,
              isSavingPaymentChoice: false,
              onPaymentChoiceChanged: (value) => selectedChoice = value,
              canSubmitElectronicPayment: false,
              isLoadingRecipients: false,
              recipientError: null,
              recipients: mockRecipients,
              selectedRecipientId: null,
              referenceController: TextEditingController(),
              isSubmitting: false,
              onSubmitPaymentReference: () {},
            ),
          ),
        ),
      );

      final dropdown = tester.widget<DropdownButton<String>>(
        find.byType(DropdownButton<String>),
      );
      expect(dropdown.items!.first.value, 'CASH');
      expect(dropdown.items!.last.value, 'RECIPIENT:5');

      await tester.tap(find.byType(DropdownButtonFormField<String>));
      await tester.pumpAndSettle();
      expect(find.text('Cash at Barangay Hall'), findsWidgets);
      expect(find.text('GCash · Treasury GCash'), findsOneWidget);
      await tester.tap(find.text('Cash at Barangay Hall').last);
      await tester.pumpAndSettle();
      expect(selectedChoice, 'CASH');
    });

    testWidgets('uses cash as the only option without configured e-payments', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DocumentPaymentSection(
              request: DocumentRequestModel(
                id: 121,
                documentType: 'Barangay Clearance',
                status: 'READY_FOR_PICKUP',
                feeAmount: 50.0,
                paymentStatus: 'UNPAID',
              ),
              canChoosePayment: true,
              selectedPaymentChoice: null,
              isSavingPaymentChoice: false,
              canSubmitElectronicPayment: false,
              isLoadingRecipients: false,
              recipientError: null,
              recipients: const [],
              selectedRecipientId: null,
              referenceController: TextEditingController(),
              isSubmitting: false,
              onSubmitPaymentReference: () {},
            ),
          ),
        ),
      );

      final dropdown = tester.widget<DropdownButton<String>>(
        find.byType(DropdownButton<String>),
      );
      expect(dropdown.items, hasLength(1));
      expect(dropdown.items!.single.value, 'CASH');
      expect(
        find.text(
          'No e-payment options are configured. Cash at the Barangay Hall is the only available method.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('renders statutory fee exemption badge when isFeeExempt', (
      tester,
    ) async {
      final request = DocumentRequestModel(
        id: 103,
        documentType: 'Certificate of Indigency',
        status: 'READY_FOR_PICKUP',
        feeAmount: 0.0,
        paymentStatus: 'NOT_REQUIRED',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DocumentPaymentSection(
              request: request,
              canSubmitElectronicPayment: false,
              isLoadingRecipients: false,
              recipientError: null,
              recipients: mockRecipients,
              selectedRecipientId: null,
              referenceController: TextEditingController(),
              isSubmitting: false,
              onPaymentChoiceChanged: (_) {},
              onSubmitPaymentReference: () {},
            ),
          ),
        ),
      );

      expect(find.text('Statutory Fee Exemption (₱0.00)'), findsOneWidget);
      expect(
        find.textContaining('RA 11261 / Indigency guidelines'),
        findsOneWidget,
      );
    });

    testWidgets(
      'renders pending verification card with reference, timestamp, and proof preview button',
      (tester) async {
        var proofViewed = false;
        final request = DocumentRequestModel(
          id: 104,
          documentType: 'Barangay Clearance',
          status: 'READY_FOR_PICKUP',
          feeAmount: 50.0,
          paymentMethod: 'GCASH',
          paymentStatus: 'PENDING_VERIFICATION',
          paymentReference: 'GCASH-TXN-12345',
          paymentTransactedAt: DateTime(2026, 10, 13, 10, 30),
          paymentRecipientName: 'Treasury GCash',
          paymentRecipientIdentifier: '0917-111-2222',
          paymentProofUrl: '/api/v1/document-requests/104/payment-proof/',
        );

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: DocumentPaymentSection(
                request: request,
                canSubmitElectronicPayment: false,
                isLoadingRecipients: false,
                recipientError: null,
                recipients: mockRecipients,
                selectedRecipientId: null,
                referenceController: TextEditingController(),
                isSubmitting: false,
                onPaymentChoiceChanged: (_) {},
                onSubmitPaymentReference: () {},
                onViewProof: () => proofViewed = true,
              ),
            ),
          ),
        );

        expect(
          find.text('Payment Submitted · Awaiting Verification'),
          findsOneWidget,
        );
        expect(find.text('Reference: GCASH-TXN-12345'), findsOneWidget);
        expect(find.textContaining('Transacted: Oct 13, 2026 10:30 AM'), findsOneWidget);
        expect(find.textContaining('Treasury GCash · 0917-111-2222'), findsOneWidget);

        final viewProofBtn = find.text('View Uploaded Receipt Proof');
        expect(viewProofBtn, findsOneWidget);

        await tester.tap(viewProofBtn);
        await tester.pumpAndSettle();
        expect(proofViewed, isTrue);
      },
    );

    testWidgets('renders rejection alert card with staff note', (
      tester,
    ) async {
      final request = DocumentRequestModel(
        id: 105,
        documentType: 'Barangay Clearance',
        status: 'READY_FOR_PICKUP',
        feeAmount: 50.0,
        paymentStatus: 'REJECTED',
        paymentReviewNote: 'Receipt amount does not match ₱50.00 fee.',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: DocumentPaymentSection(
                request: request,
                canSubmitElectronicPayment: true,
                isLoadingRecipients: false,
                recipientError: null,
                recipients: mockRecipients,
                selectedRecipientId: 5,
                referenceController: TextEditingController(text: 'OLD-REF'),
                isSubmitting: false,
                onPaymentChoiceChanged: (_) {},
                onSubmitPaymentReference: () {},
              ),
            ),
          ),
        ),
      );

      expect(find.text('Payment Reference Rejected'), findsOneWidget);
      expect(
        find.text('Staff note: Receipt amount does not match ₱50.00 fee.'),
        findsOneWidget,
      );
      expect(
        find.textContaining('Please verify your transfer details, take a clear screenshot'),
        findsOneWidget,
      );
    });

    testWidgets('requires a receipt before enabling payment submission', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: DocumentPaymentSection(
                request: DocumentRequestModel(
                  id: 107,
                  documentType: 'Barangay Clearance',
                  status: 'READY_FOR_PICKUP',
                  feeAmount: 50.0,
                  paymentStatus: 'UNPAID',
                ),
                canSubmitElectronicPayment: true,
                isLoadingRecipients: false,
                recipientError: null,
                recipients: mockRecipients,
                selectedRecipientId: 5,
                referenceController: TextEditingController(text: 'REF-107'),
                isSubmitting: false,
                onPaymentChoiceChanged: (_) {},
                onSubmitPaymentReference: () {},
              ),
            ),
          ),
        ),
      );

      final submitButton = tester.widget<ElevatedButton>(
        find.widgetWithText(ElevatedButton, 'Submit transfer reference'),
      );
      expect(submitButton.onPressed, isNull);
      expect(
        find.text('Receipt screenshot is required before you can submit.'),
        findsOneWidget,
      );
    });

    testWidgets(
      'renders date picker, screenshot preview thumbnail, and remove action in payment form',
      (tester) async {
        final mockBytes = Uint8List.fromList([
          0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
          0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
          0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00,
          0x0A, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
          0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49,
          0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
        ]);
        var removedProof = false;

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: DocumentPaymentSection(
                  request: DocumentRequestModel(
                    id: 106,
                    documentType: 'Barangay Clearance',
                    status: 'READY_FOR_PICKUP',
                    feeAmount: 50.0,
                    paymentStatus: 'UNPAID',
                  ),
                  canSubmitElectronicPayment: true,
                  isLoadingRecipients: false,
                  recipientError: null,
                  recipients: mockRecipients,
                  selectedRecipientId: 5,
                  referenceController: TextEditingController(text: 'REF-7788'),
                  selectedTransactedAt: DateTime(2026, 10, 13, 9, 0),
                  selectedProofBytes: mockBytes,
                  selectedProofFilename: 'receipt_screen.png',
                  isSubmitting: false,
                  onPaymentChoiceChanged: (_) {},
                  onProofSelected: (bytes) {
                    if (bytes == null) removedProof = true;
                  },
                  onSubmitPaymentReference: () {},
                ),
              ),
            ),
          ),
        );

        expect(find.text('Transaction Date & Time'), findsOneWidget);
        expect(find.textContaining('Oct 13, 2026 9:00 AM'), findsOneWidget);
        expect(find.text('receipt_screen.png'), findsOneWidget);

        final removeBtn = find.byIcon(Icons.close);
        expect(removeBtn, findsOneWidget);

        await tester.tap(removeBtn);
        await tester.pumpAndSettle();
        expect(removedProof, isTrue);
      },
    );
  });
}
