import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/models/equipment_borrow_request_model.dart';
import 'package:mobile/screens/equipment_borrowing_screen.dart';
import 'package:mobile/services/equipment_borrow_service.dart';

class _FakeEquipmentBorrowService extends EquipmentBorrowService {
  _FakeEquipmentBorrowService() : super(apiClient: ApiClient());

  final List<EquipmentBorrowRequestModel> requests = [
    const EquipmentBorrowRequestModel(
      id: 1,
      residentName: 'Juan Dela Cruz',
      itemType: 'Monoblock Chairs',
      quantity: 20,
      borrowDate: '2026-11-20',
      returnDate: '2026-11-21',
      timeSlot: '08:00 AM - 05:00 PM',
      purpose: 'Neighborhood birthday gathering.',
      status: 'PENDING',
    ),
  ];

  String? submittedPurpose;
  String? lastReviewedStatus;

  @override
  Future<List<EquipmentBorrowRequestModel>> fetchRequests() async =>
      List<EquipmentBorrowRequestModel>.from(requests);

  @override
  Future<EquipmentBorrowRequestModel> createRequest({
    required String itemType,
    required int quantity,
    required String borrowDate,
    required String returnDate,
    String timeSlot = '',
    required String purpose,
  }) async {
    submittedPurpose = purpose;
    final created = EquipmentBorrowRequestModel(
      id: requests.length + 1,
      itemType: itemType,
      quantity: quantity,
      borrowDate: borrowDate,
      returnDate: returnDate,
      timeSlot: timeSlot,
      purpose: purpose,
      status: 'PENDING',
    );
    requests.insert(0, created);
    return created;
  }

  @override
  Future<EquipmentBorrowRequestModel> reviewRequest({
    required int requestId,
    required String status,
    String adminNotes = '',
  }) async {
    lastReviewedStatus = status;
    final index = requests.indexWhere((r) => r.id == requestId);
    final updated = EquipmentBorrowRequestModel(
      id: requests[index].id,
      residentName: requests[index].residentName,
      itemType: requests[index].itemType,
      quantity: requests[index].quantity,
      borrowDate: requests[index].borrowDate,
      returnDate: requests[index].returnDate,
      timeSlot: requests[index].timeSlot,
      purpose: requests[index].purpose,
      status: status,
      adminNotes: adminNotes,
    );
    requests[index] = updated;
    return updated;
  }
}

void main() {
  test('EquipmentBorrowRequestModel parses JSON and computes status labels', () {
    final model = EquipmentBorrowRequestModel.fromJson({
      'id': '42',
      'resident_name': 'Maria Santos',
      'item_type': 'Tent / Canopy',
      'quantity': 2,
      'borrow_date': '2026-11-22',
      'return_date': '2026-11-23',
      'time_slot': '08:00 AM - 05:00 PM',
      'purpose': 'Community clean-up tent.',
      'status': 'APPROVED',
      'admin_notes': 'Approved by Captain.',
    });

    expect(model.id, 42);
    expect(model.isApproved, isTrue);
    expect(model.statusDisplay, 'Approved');
    expect(model.formattedSchedule, '2026-11-22 → 2026-11-23 (08:00 AM - 05:00 PM)');
  });

  testWidgets('resident can submit an equipment borrowing request', (
    tester,
  ) async {
    final service = _FakeEquipmentBorrowService();
    await tester.pumpWidget(
      MaterialApp(
        home: EquipmentBorrowingScreen(equipmentBorrowService: service),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Equipment & Facility Borrowing'), findsOneWidget);
    expect(find.text('Neighborhood birthday gathering.'), findsOneWidget);

    await tester.enterText(
      find.widgetWithText(TextField, 'Purpose'),
      '  Barangay youth sports fest.  ',
    );
    await tester.ensureVisible(find.text('Submit Borrowing Request'));
    await tester.tap(find.text('Submit Borrowing Request'));
    await tester.pumpAndSettle();

    expect(service.submittedPurpose, 'Barangay youth sports fest.');
    expect(find.text('Barangay youth sports fest.'), findsOneWidget);
    expect(
      find.text('Equipment borrowing request submitted for review.'),
      findsOneWidget,
    );
  });

  testWidgets('admin can approve and mark borrowing request returned', (
    tester,
  ) async {
    final service = _FakeEquipmentBorrowService();
    await tester.pumpWidget(
      MaterialApp(
        home: EquipmentBorrowingScreen(
          equipmentBorrowService: service,
          isAdmin: true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Approve'));
    await tester.pumpAndSettle();
    expect(service.lastReviewedStatus, 'APPROVED');
    expect(find.text('Approved'), findsOneWidget);

    await tester.tap(find.text('Mark Returned'));
    await tester.pumpAndSettle();
    expect(service.lastReviewedStatus, 'RETURNED');
    expect(find.text('Returned'), findsOneWidget);
  });
}
