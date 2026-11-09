import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:mobile/core/localization/app_language.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/models/barangay_model.dart';
import 'package:mobile/models/resident_transfer_model.dart';
import 'package:mobile/models/user_model.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/storage_service.dart';
import 'package:mobile/widgets/resident_transfer_section.dart';
import 'package:shared_preferences/shared_preferences.dart';

class TransferFakeApiClient extends ApiClient {
  TransferFakeApiClient() : super(baseUrl: 'https://example.test/api/v1');

  List<Map<String, dynamic>> barangays = [
    {
      'id': 1,
      'name': 'Barangay San Antonio',
      'municipality': 'Pasig',
      'province': 'Metro Manila',
    },
    {
      'id': 2,
      'name': 'Barangay San Isidro',
      'municipality': 'Taytay',
      'province': 'Rizal',
    },
  ];

  List<Map<String, dynamic>> transfers = [];

  String? lastMultipartEndpoint;
  Map<String, String>? lastMultipartFields;
  List<http.MultipartFile>? lastMultipartFiles;

  @override
  Future<http.Response> get(
    String endpoint, {
    Map<String, String>? queryParams,
    Map<String, String>? headers,
    bool requiresAuth = true,
  }) async {
    if (endpoint == '/auth/public/barangays/') {
      return http.Response(jsonEncode(barangays), 200);
    }
    if (endpoint == '/auth/resident-transfers/') {
      return http.Response(jsonEncode(transfers), 200);
    }
    return http.Response('[]', 200);
  }

  @override
  Future<http.Response> postMultipart(
    String endpoint, {
    Map<String, String>? fields,
    List<http.MultipartFile>? files,
    bool requiresAuth = true,
  }) async {
    lastMultipartEndpoint = endpoint;
    lastMultipartFields = fields;
    lastMultipartFiles = files;

    final newTransfer = {
      'id': 99,
      'resident_id': 10,
      'resident_name': 'Juan Dela Cruz',
      'resident_username': 'juandc',
      'source_barangay_id': 1,
      'source_barangay_name': 'Barangay San Antonio',
      'destination_barangay_id': int.parse(fields?['destination_barangay_id'] ?? '2'),
      'destination_barangay_name': 'Barangay San Isidro',
      'purok': fields?['purok'] ?? '',
      'address_details': fields?['address_details'] ?? '',
      'has_proof_of_residency': true,
      'reason': fields?['reason'] ?? '',
      'status': 'PENDING',
      'review_note': '',
      'created_at': DateTime.now().toIso8601String(),
      'reviewed_at': null,
    };
    transfers.add(newTransfer);

    return http.Response(jsonEncode(newTransfer), 201);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late StorageService storageService;
  late TransferFakeApiClient apiClient;
  late AuthService authService;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    storageService = StorageService(preferences);
    apiClient = TransferFakeApiClient();
    authService = AuthService(
      apiClient: apiClient,
      storageService: storageService,
    );
  });

  group('AuthService Transfer Methods', () {
    test('fetchTransferRequests parses transfer request items', () async {
      apiClient.transfers = [
        {
          'id': 12,
          'resident_id': 10,
          'resident_name': 'Juan Dela Cruz',
          'resident_username': 'juandc',
          'source_barangay_id': 1,
          'source_barangay_name': 'Barangay San Antonio',
          'destination_barangay_id': 2,
          'destination_barangay_name': 'Barangay San Isidro',
          'purok': 'Purok 4',
          'address_details': 'Block 5 Lot 2',
          'has_proof_of_residency': true,
          'reason': 'Work relocation.',
          'status': 'PENDING',
          'review_note': '',
          'created_at': '2026-11-09T08:00:00Z',
          'reviewed_at': null,
        },
      ];

      final requests = await authService.fetchTransferRequests();

      expect(requests, hasLength(1));
      expect(requests.first.id, 12);
      expect(requests.first.sourceBarangayName, 'Barangay San Antonio');
      expect(requests.first.destinationBarangayName, 'Barangay San Isidro');
      expect(requests.first.purok, 'Purok 4');
      expect(requests.first.isPending, isTrue);
    });

    test('submitTransferRequest sends multipart fields and file', () async {
      final dummyFile = XFile.fromData(
        Uint8List.fromList([1, 2, 3, 4]),
        name: 'proof.png',
      );

      final result = await authService.submitTransferRequest(
        destinationBarangayId: 2,
        reason: 'Moving closer to family.',
        purok: 'Purok 2',
        addressDetails: '789 Kalayaan Ave',
        proofFile: dummyFile,
      );

      expect(apiClient.lastMultipartEndpoint, '/auth/resident-transfers/');
      expect(apiClient.lastMultipartFields?['destination_barangay_id'], '2');
      expect(apiClient.lastMultipartFields?['reason'], 'Moving closer to family.');
      expect(apiClient.lastMultipartFields?['purok'], 'Purok 2');
      expect(apiClient.lastMultipartFields?['address_details'], '789 Kalayaan Ave');
      expect(apiClient.lastMultipartFiles, hasLength(1));
      expect(apiClient.lastMultipartFiles!.first.field, 'proof_of_residency');
      expect(result.status, 'PENDING');
    });
  });

  group('ResidentTransferSection Widget', () {
    Widget buildTestWidget({required UserModel user}) {
      return MaterialApp(
        theme: AppTheme.lightTheme,
        home: Scaffold(
          body: SingleChildScrollView(
            child: ResidentTransferSection(
              user: user,
              authService: authService,
            ),
          ),
        ),
      );
    }

    testWidgets('shows verification requirement when resident is unverified', (tester) async {
      final unverifiedUser = UserModel(
        id: 1,
        username: 'unverified_resident',
        email: 'unverified@example.com',
        fullName: 'New Resident',
        role: 'RESIDENT',
        isVerified: false,
        barangayId: 1,
      );

      await tester.pumpWidget(buildTestWidget(user: unverifiedUser));
      await tester.pumpAndSettle();

      expect(find.text('Barangay Transfer'), findsOneWidget);
      expect(
        find.text('Barangay transfer requests are available after your resident account is verified.'),
        findsOneWidget,
      );
      expect(find.text('RECEIVING BARANGAY'), findsNothing);
    });

    testWidgets('shows transfer form for verified resident with no pending transfer', (tester) async {
      final verifiedUser = UserModel(
        id: 1,
        username: 'verified_resident',
        email: 'verified@example.com',
        fullName: 'Juan Dela Cruz',
        role: 'RESIDENT',
        isVerified: true,
        barangayId: 1,
      );

      await tester.pumpWidget(buildTestWidget(user: verifiedUser));
      await tester.pumpAndSettle();

      expect(find.text('Barangay Transfer'), findsOneWidget);
      expect(find.text('RECEIVING BARANGAY'), findsOneWidget);
      expect(find.text('Choose receiving Barangay'), findsOneWidget);
      expect(find.text('PUROK / ZONE (IF APPLICABLE)'), findsOneWidget);
      expect(find.text('NEW STREET ADDRESS / DETAILS'), findsOneWidget);
      expect(find.text('PROOF OF RESIDENCY'), findsOneWidget);
      expect(find.text('REASON FOR MOVING'), findsOneWidget);
      expect(find.text('Submit Transfer Request'), findsOneWidget);
    });

    testWidgets('shows pending card and blocks new form when request is pending', (tester) async {
      apiClient.transfers = [
        {
          'id': 50,
          'resident_id': 1,
          'resident_name': 'Juan Dela Cruz',
          'resident_username': 'juandc',
          'source_barangay_id': 1,
          'source_barangay_name': 'Barangay San Antonio',
          'destination_barangay_id': 2,
          'destination_barangay_name': 'Barangay San Isidro',
          'purok': 'Purok 7',
          'address_details': '101 Highway',
          'has_proof_of_residency': true,
          'reason': 'Transferred assignment.',
          'status': 'PENDING',
          'review_note': '',
          'created_at': '2026-11-09T09:00:00Z',
          'reviewed_at': null,
        },
      ];

      final verifiedUser = UserModel(
        id: 1,
        username: 'verified_resident',
        email: 'verified@example.com',
        fullName: 'Juan Dela Cruz',
        role: 'RESIDENT',
        isVerified: true,
        barangayId: 1,
      );

      await tester.pumpWidget(buildTestWidget(user: verifiedUser));
      await tester.pumpAndSettle();

      expect(find.text('Barangay San Antonio → Barangay San Isidro'), findsAtLeastNWidgets(1));
      expect(find.text('PENDING'), findsAtLeastNWidgets(1));
      expect(
        find.text('You already have a transfer request waiting for review. You can submit another after it is approved or rejected.'),
        findsOneWidget,
      );
      // New form fields should NOT be rendered
      expect(find.text('RECEIVING BARANGAY'), findsNothing);
      expect(find.text('Submit Transfer Request'), findsNothing);
    });

    testWidgets('shows rejection note in history when past transfer was rejected', (tester) async {
      apiClient.transfers = [
        {
          'id': 51,
          'resident_id': 1,
          'resident_name': 'Juan Dela Cruz',
          'resident_username': 'juandc',
          'source_barangay_id': 1,
          'source_barangay_name': 'Barangay San Antonio',
          'destination_barangay_id': 2,
          'destination_barangay_name': 'Barangay San Isidro',
          'purok': '',
          'address_details': '',
          'has_proof_of_residency': true,
          'reason': 'Moved to new apartment.',
          'status': 'REJECTED',
          'review_note': 'Document is blurry and unreadable.',
          'created_at': '2026-11-08T09:00:00Z',
          'reviewed_at': '2026-11-08T10:00:00Z',
        },
      ];

      final verifiedUser = UserModel(
        id: 1,
        username: 'verified_resident',
        email: 'verified@example.com',
        fullName: 'Juan Dela Cruz',
        role: 'RESIDENT',
        isVerified: true,
        barangayId: 1,
      );

      await tester.pumpWidget(buildTestWidget(user: verifiedUser));
      await tester.pumpAndSettle();

      expect(find.text('REJECTED'), findsOneWidget);
      expect(
        find.text('Rejection reason: Document is blurry and unreadable.'),
        findsOneWidget,
      );
    });
  });
}
