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
      philsysIdNumber: json['philsys_id_number']?.toString(),
      philsysIdPhoto: json['philsys_id_photo']?.toString(),
      secondaryIdType: json['secondary_id_type']?.toString(),
      secondaryIdPhoto: json['secondary_id_photo']?.toString(),
      utilityBillingType: json['utility_billing_type']?.toString(),
      utilityBillingPhoto: json['utility_billing_photo']?.toString(),
    );
  }

  static int _toInt(Object? value) {
    if (value is int) return value;
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}
