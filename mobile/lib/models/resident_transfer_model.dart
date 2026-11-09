class ResidentTransferModel {
  final int id;
  final int residentId;
  final String residentName;
  final String residentUsername;
  final int sourceBarangayId;
  final String sourceBarangayName;
  final int destinationBarangayId;
  final String destinationBarangayName;
  final String purok;
  final String addressDetails;
  final bool hasProofOfResidency;
  final String reason;
  final String status;
  final String reviewNote;
  final DateTime? createdAt;
  final DateTime? reviewedAt;

  const ResidentTransferModel({
    required this.id,
    required this.residentId,
    required this.residentName,
    required this.residentUsername,
    required this.sourceBarangayId,
    required this.sourceBarangayName,
    required this.destinationBarangayId,
    required this.destinationBarangayName,
    required this.purok,
    required this.addressDetails,
    required this.hasProofOfResidency,
    required this.reason,
    required this.status,
    required this.reviewNote,
    this.createdAt,
    this.reviewedAt,
  });

  bool get isPending => status == 'PENDING';
  bool get isApproved => status == 'APPROVED';
  bool get isRejected => status == 'REJECTED';

  String get newResidenceFormatted {
    final parts = [purok, addressDetails].where((p) => p.trim().isNotEmpty);
    return parts.join(', ');
  }

  factory ResidentTransferModel.fromJson(Map<String, dynamic> json) {
    return ResidentTransferModel(
      id: json['id'] is int ? json['id'] as int : int.parse(json['id'].toString()),
      residentId: json['resident_id'] is int
          ? json['resident_id'] as int
          : int.tryParse(json['resident_id']?.toString() ?? '') ?? 0,
      residentName: json['resident_name'] as String? ?? '',
      residentUsername: json['resident_username'] as String? ?? '',
      sourceBarangayId: json['source_barangay_id'] is int
          ? json['source_barangay_id'] as int
          : int.tryParse(json['source_barangay_id']?.toString() ?? '') ?? 0,
      sourceBarangayName: json['source_barangay_name'] as String? ?? '',
      destinationBarangayId: json['destination_barangay_id'] is int
          ? json['destination_barangay_id'] as int
          : int.tryParse(json['destination_barangay_id']?.toString() ?? '') ?? 0,
      destinationBarangayName: json['destination_barangay_name'] as String? ?? '',
      purok: json['purok'] as String? ?? '',
      addressDetails: json['address_details'] as String? ?? '',
      hasProofOfResidency: json['has_proof_of_residency'] as bool? ?? false,
      reason: json['reason'] as String? ?? '',
      status: json['status'] as String? ?? 'PENDING',
      reviewNote: json['review_note'] as String? ?? '',
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) : null,
      reviewedAt: json['reviewed_at'] != null ? DateTime.tryParse(json['reviewed_at'].toString()) : null,
    );
  }
}
