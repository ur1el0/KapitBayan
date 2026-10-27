import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../core/network/api_client.dart';
import '../models/document_request_model.dart';
import '../models/document_offering_model.dart';
import '../models/payment_recipient_model.dart';
import 'storage_service.dart';

/// Service coordinating document request fetching, creation, and PDF downloads
class DocumentService {
  final ApiClient apiClient;
  final StorageService storageService;

  DocumentService({required this.apiClient, required this.storageService});

  /// Fetches all document requests for the authenticated user from the backend API
  Future<List<DocumentRequestModel>> fetchDocumentRequests() async {
    try {
      final response = await apiClient.get(
        '/document-requests/',
        requiresAuth: true,
      );
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      final List<DocumentRequestModel> items = [];
      var page = 1;
      dynamic current = decoded;

      while (true) {
        final rawItems = current is Map<String, dynamic>
            ? current['results']
            : current;
        if (rawItems is! List) {
          throw const FormatException('Document request list is invalid.');
        }
        items.addAll(
          rawItems.map(
            (item) => DocumentRequestModel.fromJson(
              Map<String, dynamic>.from(item as Map),
            ),
          ),
        );

        final hasNext =
            current is Map<String, dynamic> && current['next'] != null;
        if (!hasNext) break;
        page++;
        final nextResponse = await apiClient.get(
          '/document-requests/',
          queryParams: {'page': '$page'},
          requiresAuth: true,
        );
        current = jsonDecode(utf8.decode(nextResponse.bodyBytes));
      }

      return items;
    } catch (e) {
      rethrow;
    }
  }

  Future<List<DocumentOfferingModel>> fetchDocumentOfferings() async {
    final response = await apiClient.get(
      '/document-catalog/',
      requiresAuth: true,
    );
    final decoded = jsonDecode(utf8.decode(response.bodyBytes));
    final rawItems = decoded is Map<String, dynamic>
        ? decoded['results']
        : decoded;
    if (rawItems is! List) {
      throw const FormatException('Document service catalog is invalid.');
    }
    return rawItems
        .map(
          (item) => DocumentOfferingModel.fromJson(
            Map<String, dynamic>.from(item as Map),
          ),
        )
        .toList();
  }

  Future<DocumentOfferingModel> saveDocumentOffering({
    int? offeringId,
    required String documentType,
    required List<String> requirements,
    required double? publishedFeeAmount,
    required String details,
    required bool isActive,
  }) async {
    final body = <String, dynamic>{
      'document_type': documentType.trim(),
      'requirements': requirements,
      'published_fee_amount': publishedFeeAmount,
      'details': details.trim(),
      'is_active': isActive,
    };
    final response = offeringId == null
        ? await apiClient.post(
            '/document-catalog/',
            body: body,
            requiresAuth: true,
          )
        : await apiClient.patch(
            '/document-catalog/$offeringId/',
            body: body,
            requiresAuth: true,
          );
    return DocumentOfferingModel.fromJson(
      jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>,
    );
  }

  Future<void> setDocumentOfferingActive({
    required int offeringId,
    required bool isActive,
  }) async {
    await apiClient.patch(
      '/document-catalog/$offeringId/',
      body: {'is_active': isActive},
      requiresAuth: true,
    );
  }

  /// Applies the existing barangay staff review transition for one request.
  Future<DocumentRequestModel> reviewAdminDocumentRequest({
    required int requestId,
    required String status,
    required String adminNotes,
    required String orNumber,
    required String? feeAmount,
    String? feeWaiverReason,
  }) async {
    final body = <String, dynamic>{
      'status': status,
      'admin_notes': adminNotes.trim(),
      'or_number': orNumber.trim(),
    };
    if (feeAmount != null) body['fee_amount'] = feeAmount.trim();
    if (feeWaiverReason != null && feeWaiverReason.trim().isNotEmpty) {
      body['fee_waiver_reason'] = feeWaiverReason.trim();
    }

    final response = await apiClient.patch(
      '/document-requests/$requestId/validate/',
      body: body,
      requiresAuth: true,
    );
    return DocumentRequestModel.fromJson(
      jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>,
    );
  }

  /// Persists the resident's choice of cash or an active barangay e-payment recipient.
  Future<DocumentRequestModel> chooseDocumentPaymentMethod({
    required int requestId,
    required String paymentMethod,
    int? paymentRecipientId,
  }) async {
    final body = paymentMethod == 'CASH'
        ? <String, dynamic>{'payment_method': 'CASH'}
        : <String, dynamic>{'payment_recipient_id': paymentRecipientId};
    final response = await apiClient.post(
      '/document-requests/$requestId/payment-choice/',
      body: body,
      requiresAuth: true,
    );
    return DocumentRequestModel.fromJson(
      jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>,
    );
  }

  /// Saves only an official receipt number without changing request status or fee data.
  Future<DocumentRequestModel> saveOfficialReceiptNumber({
    required int requestId,
    required String orNumber,
  }) async {
    final response = await apiClient.patch(
      '/document-requests/$requestId/or-number/',
      body: {'or_number': orNumber.trim()},
      requiresAuth: true,
    );
    return DocumentRequestModel.fromJson(
      jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>,
    );
  }

  /// Verifies or rejects a pending manual electronic transfer reference.
  Future<DocumentRequestModel> reviewAdminPayment({
    required int requestId,
    required String status,
    required String note,
    String? orNumber,
  }) async {
    final response = await apiClient.patch(
      '/document-requests/$requestId/payment-review/',
      body: {
        'status': status,
        'note': note.trim(),
        if (orNumber != null && orNumber.trim().isNotEmpty)
          'or_number': orNumber.trim(),
      },
      requiresAuth: true,
    );
    return DocumentRequestModel.fromJson(
      jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>,
    );
  }

  /// Creates a new document request for the authenticated resident
  Future<DocumentRequestModel> createDocumentRequest({
    required String documentType,
    String urgencyTag = 'REGULAR',
    String? purpose,
  }) async {
    return _createDocumentRequest(
      documentType: documentType,
      urgencyTag: urgencyTag,
      purpose: purpose,
    );
  }

  Future<DocumentRequestModel> createDocumentRequestFromOffering({
    required int offeringId,
    required String documentType,
    String urgencyTag = 'REGULAR',
    String? purpose,
  }) async {
    return _createDocumentRequest(
      documentType: documentType,
      offeringId: offeringId,
      urgencyTag: urgencyTag,
      purpose: purpose,
    );
  }

  Future<DocumentRequestModel> _createDocumentRequest({
    required String documentType,
    int? offeringId,
    required String urgencyTag,
    String? purpose,
  }) async {
    try {
      final response = await apiClient.post(
        '/document-requests/',
        body: {
          'document_type': documentType,
          'offering_id': ?offeringId,
          'urgency_tag': urgencyTag.toUpperCase(),
          'purpose': ?purpose,
        },
        requiresAuth: true,
      );

      final Map<String, dynamic> data = jsonDecode(
        utf8.decode(response.bodyBytes),
      );
      return DocumentRequestModel.fromJson(data);
    } catch (e) {
      rethrow;
    }
  }

  /// Lists active electronic payment recipients for the resident's barangay.
  Future<List<PaymentRecipientModel>> fetchPaymentRecipients() async {
    final response = await apiClient.get(
      '/payment-recipients/',
      requiresAuth: true,
    );
    final decoded = jsonDecode(utf8.decode(response.bodyBytes));
    final List<dynamic> results = decoded is Map<String, dynamic>
        ? (decoded['results'] as List<dynamic>? ?? <dynamic>[])
        : decoded as List<dynamic>;
    return results
        .map(
          (item) =>
              PaymentRecipientModel.fromJson(item as Map<String, dynamic>),
        )
        .toList();
  }

  /// Sends a resident-selected transfer reference, timestamp, and required receipt screenshot
  /// for manual barangay verification using multipart/form-data.
  Future<DocumentRequestModel> submitPaymentReference({
    required int requestId,
    required int paymentRecipientId,
    required String paymentReference,
    required DateTime transactedAt,
    required List<int> proofImageBytes,
    required String proofImageFilename,
  }) async {
    if (proofImageBytes.isEmpty) {
      throw ArgumentError.value(
        proofImageBytes,
        'proofImageBytes',
        'A receipt image is required.',
      );
    }
    if (proofImageFilename.trim().isEmpty) {
      throw ArgumentError.value(
        proofImageFilename,
        'proofImageFilename',
        'A receipt filename is required.',
      );
    }

    final fields = <String, String>{
      'payment_recipient_id': paymentRecipientId.toString(),
      'payment_reference': paymentReference.trim(),
    };
    fields['payment_transacted_at'] = transactedAt.toIso8601String();

    final files = <http.MultipartFile>[
      http.MultipartFile.fromBytes(
        'payment_proof_image',
        proofImageBytes,
        filename: proofImageFilename,
      ),
    ];

    final response = await apiClient.postMultipart(
      '/document-requests/$requestId/payment-reference/',
      fields: fields,
      files: files,
      requiresAuth: true,
    );
    final data =
        jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    return DocumentRequestModel.fromJson(data);
  }

  /// Fetches private authenticated payment proof image bytes for staff or owner inspection
  Future<Uint8List> fetchPaymentProof(int requestId) async {
    final response = await apiClient.get(
      '/document-requests/$requestId/payment-proof/',
      headers: const {'Accept': '*/*'},
      requiresAuth: true,
    );
    return response.bodyBytes;
  }

  /// Downloads the issued certificate PDF for approved / ready-for-pickup documents
  Future<Uint8List> downloadDocumentPdf(int requestId) async {
    try {
      final response = await apiClient.get(
        '/document-requests/$requestId/generate-pdf/',
        requiresAuth: true,
      );
      return response.bodyBytes;
    } catch (e) {
      rethrow;
    }
  }
}
