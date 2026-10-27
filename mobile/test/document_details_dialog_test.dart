import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/models/document_request_model.dart';
import 'package:mobile/models/payment_recipient_model.dart';
import 'package:mobile/services/document_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:mobile/widgets/document_details_dialog.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _DocumentServiceWithRecipient extends DocumentService {
  _DocumentServiceWithRecipient({required super.storageService})
    : super(apiClient: ApiClient());

  @override
  Future<List<PaymentRecipientModel>> fetchPaymentRecipients() async => const [
    PaymentRecipientModel(
      id: 8,
      provider: 'GCASH',
      providerLabel: 'GCash',
      displayName: 'Barangay Treasury',
      recipientName: 'Treasurer',
      recipientIdentifier: '09XX-XXX-1234',
      instructions: 'Use your request ID as reference.',
    ),
  ];

  @override
  Future<DocumentRequestModel> chooseDocumentPaymentMethod({
    required int requestId,
    required String paymentMethod,
    int? paymentRecipientId,
  }) async => DocumentRequestModel(
    id: requestId,
    documentType: 'Barangay Clearance',
    status: 'READY_FOR_PICKUP',
    feeAmount: 50,
    paymentMethod: paymentMethod == 'CASH' ? 'CASH' : 'GCASH',
    paymentStatus: 'UNPAID',
    paymentRecipientId: paymentRecipientId,
  );
}

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('lets residents choose a configured e-payment method', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final prefs = await SharedPreferences.getInstance();
    final service = _DocumentServiceWithRecipient(
      storageService: StorageService(prefs),
    );
    const request = DocumentRequestModel(
      id: 17,
      documentType: 'Barangay Clearance',
      status: 'READY_FOR_PICKUP',
      feeAmount: 50,
      paymentMethod: '',
      paymentStatus: 'UNPAID',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: TextButton(
              onPressed: () => showModalBottomSheet<void>(
                context: context,
                isScrollControlled: true,
                builder: (_) => DocumentDetailsDialog(
                  request: request,
                  documentService: service,
                ),
              ),
              child: const Text('Open details'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Open details'));
    await tester.pumpAndSettle();

    expect(find.text('Current Status'), findsOneWidget);
    expect(find.text('Requirements'), findsOneWidget);
    expect(find.text('• Government ID or proof of residency'), findsOneWidget);
    expect(find.text('• Community Tax Certificate (Cedula)'), findsOneWidget);
    expect(find.text('Choose payment method'), findsOneWidget);
    expect(
      find.text('Cash is always available. E-payment options are set by your Barangay.'),
      findsOneWidget,
    );
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    expect(find.text('Cash at Barangay Hall'), findsOneWidget);
    expect(find.text('GCash · Barangay Treasury'), findsOneWidget);
    await tester.tap(find.text('GCash · Barangay Treasury'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Treasurer · 09XX-XXX-1234'), findsOneWidget);
    expect(find.textContaining('Use your request ID as reference.'), findsOneWidget);
    expect(find.text('Transfer reference'), findsOneWidget);
    expect(find.text('Submit transfer reference'), findsOneWidget);
  });
}
