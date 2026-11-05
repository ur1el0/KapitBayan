class AdminResidentModel {
  final int id;
  final String fullName;
  final String username;
  final String email;
  final String? birthDate;
  final String? contactNumber;
  final String? purok;
  final String? addressDetails;
  final bool voterStatus;
  final bool isVerified;
  final int? guardianId;
  final String? guardianName;
  final String? guardianUsername;
  final bool? guardianAccountEligible;
  final String? guardianRelationship;
  final String? guardianshipEvidence;
  final String? philsysIdNumber;
  final String? philsysIdPhoto;
  final String? secondaryIdType;
  final String? secondaryIdPhoto;
  final String? utilityBillingType;
  final String? utilityBillingPhoto;

  const AdminResidentModel({
    required this.id,
    required this.fullName,
    required this.username,
    required this.email,
    this.birthDate,
    this.contactNumber,
    this.purok,
    this.addressDetails,
    this.voterStatus = false,
    this.isVerified = false,
    this.guardianId,
    this.guardianName,
    this.guardianUsername,
    this.guardianAccountEligible,
    this.guardianRelationship,
    this.guardianshipEvidence,
    this.philsysIdNumber,
    this.philsysIdPhoto,
    this.secondaryIdType,
    this.secondaryIdPhoto,
    this.utilityBillingType,
    this.utilityBillingPhoto,
  });

  factory AdminResidentModel.fromJson(Map<String, dynamic> json) {
    return AdminResidentModel(
      id: _toInt(json['id']),
      fullName: json['full_name']?.toString() ?? 'Resident',
      username: json['username']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      birthDate: json['birth_date']?.toString(),
      contactNumber: json['contact_number']?.toString(),
      purok: json['purok']?.toString(),
      addressDetails: json['address_details']?.toString(),
      voterStatus: json['voter_status'] as bool? ?? false,
      isVerified: json['is_verified'] as bool? ?? false,
      guardianId: json['guardian'] == null ? null : _toInt(json['guardian']),
      guardianName: json['guardian_name']?.toString(),
      guardianUsername: json['guardian_username']?.toString(),
      guardianAccountEligible: json['guardian_account_eligible'] as bool?,
      guardianRelationship: json['guardian_relationship']?.toString(),
      guardianshipEvidence: json['guardianship_evidence']?.toString(),
      philsysIdNumber: json['philsys_id_number']?.toString(),
      philsysIdPhoto: json['philsys_id_photo']?.toString(),
      secondaryIdType: json['secondary_id_type']?.toString(),
      secondaryIdPhoto: json['secondary_id_photo']?.toString(),
      utilityBillingType: json['utility_billing_type']?.toString(),
      utilityBillingPhoto: json['utility_billing_photo']?.toString(),
    );
  }

  bool get isMinor {
    final parsed = DateTime.tryParse(birthDate ?? '');
    if (parsed == null) return false;
    final today = DateTime.now();
    var age = today.year - parsed.year;
    if (today.month < parsed.month ||
        (today.month == parsed.month && today.day < parsed.day)) {
      age--;
    }
    return age < 18;
  }

  String get guardianRelationshipLabel {
    switch (guardianRelationship) {
      case 'PARENT':
        return 'Parent';
      case 'COURT_APPOINTED':
        return 'Court-appointed guardian';
      case 'OTHER_AUTHORIZED':
        return 'Other authorized guardian';
      default:
        return 'Not provided';
    }
  }

  static int _toInt(Object? value) {
    if (value is int) return value;
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}
