/// Represents an authenticated user in the KapitBayan platform.
class UserModel {
  final int id;
  final String username;
  final String email;
  final String role;
  final String fullName;
  final bool isSuperuser;
  final bool isVerified;
  final String? contactNumber;
  final String? purok;
  final String? birthDate;
  final bool? voterStatus;

  final int? residentId;
  final String? philsysIdNumber;
  final String? philsysIdPhoto;
  final String? secondaryIdType;
  final String? secondaryIdPhoto;
  final String? utilityBillingType;
  final String? utilityBillingPhoto;

  const UserModel({
    required this.id,
    required this.username,
    required this.email,
    required this.role,
    required this.fullName,
    this.isSuperuser = false,
    this.isVerified = true,
    this.contactNumber,
    this.purok,
    this.birthDate,
    this.voterStatus,
    this.residentId,
    this.philsysIdNumber,
    this.philsysIdPhoto,
    this.secondaryIdType,
    this.secondaryIdPhoto,
    this.utilityBillingType,
    this.utilityBillingPhoto,
  });

  /// Factory constructor to parse both login payload and /auth/me/ profile responses
  factory UserModel.fromJson(Map<String, dynamic> json) {
    final profile = json['profile'] as Map<String, dynamic>?;

    final String resolvedFullName = json['full_name'] as String? ??
        profile?['full_name'] as String? ??
        json['username'] as String? ??
        '';

    final bool resolvedVerification = profile != null
        ? (profile['is_verified'] as bool? ?? false)
        : (json['is_verified'] as bool? ?? true);

    return UserModel(
      id: json['id'] as int? ?? 0,
      username: json['username'] as String? ?? '',
      email: json['email'] as String? ?? '',
      role: json['role'] as String? ?? 'RESIDENT',
      fullName: resolvedFullName,
      isSuperuser: json['is_superuser'] as bool? ?? false,
      isVerified: resolvedVerification,
      contactNumber: profile?['contact_number'] as String? ?? json['contact_number'] as String?,
      purok: profile?['purok']?.toString() ?? json['purok']?.toString(),
      birthDate: profile?['birth_date'] as String? ?? json['birth_date'] as String?,
      voterStatus: profile?['voter_status'] as bool? ?? json['voter_status'] as bool?,
      residentId: profile?['id'] as int? ?? json['resident_id'] as int?,
      philsysIdNumber: profile?['philsys_id_number'] as String? ?? json['philsys_id_number'] as String?,
      philsysIdPhoto: profile?['philsys_id_photo'] as String? ?? json['philsys_id_photo'] as String?,
      secondaryIdType: profile?['secondary_id_type'] as String? ?? json['secondary_id_type'] as String?,
      secondaryIdPhoto: profile?['secondary_id_photo'] as String? ?? json['secondary_id_photo'] as String?,
      utilityBillingType: profile?['utility_billing_type'] as String? ?? json['utility_billing_type'] as String?,
      utilityBillingPhoto: profile?['utility_billing_photo'] as String? ?? json['utility_billing_photo'] as String?,
    );
  }

  /// Converts the user model to a JSON map for caching
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'email': email,
      'role': role,
      'full_name': fullName,
      'is_superuser': isSuperuser,
      'is_verified': isVerified,
      'contact_number': contactNumber,
      'purok': purok,
      'birth_date': birthDate,
      'voter_status': voterStatus,
      'resident_id': residentId,
      'philsys_id_number': philsysIdNumber,
      'philsys_id_photo': philsysIdPhoto,
      'secondary_id_type': secondaryIdType,
      'secondary_id_photo': secondaryIdPhoto,
      'utility_billing_type': utilityBillingType,
      'utility_billing_photo': utilityBillingPhoto,
    };
  }

  UserModel copyWith({
    int? id,
    String? username,
    String? email,
    String? role,
    String? fullName,
    bool? isSuperuser,
    bool? isVerified,
    String? contactNumber,
    String? purok,
    String? birthDate,
    bool? voterStatus,
    int? residentId,
    String? philsysIdNumber,
    String? philsysIdPhoto,
    String? secondaryIdType,
    String? secondaryIdPhoto,
    String? utilityBillingType,
    String? utilityBillingPhoto,
  }) {
    return UserModel(
      id: id ?? this.id,
      username: username ?? this.username,
      email: email ?? this.email,
      role: role ?? this.role,
      fullName: fullName ?? this.fullName,
      isSuperuser: isSuperuser ?? this.isSuperuser,
      isVerified: isVerified ?? this.isVerified,
      contactNumber: contactNumber ?? this.contactNumber,
      purok: purok ?? this.purok,
      birthDate: birthDate ?? this.birthDate,
      voterStatus: voterStatus ?? this.voterStatus,
      residentId: residentId ?? this.residentId,
      philsysIdNumber: philsysIdNumber ?? this.philsysIdNumber,
      philsysIdPhoto: philsysIdPhoto ?? this.philsysIdPhoto,
      secondaryIdType: secondaryIdType ?? this.secondaryIdType,
      secondaryIdPhoto: secondaryIdPhoto ?? this.secondaryIdPhoto,
      utilityBillingType: utilityBillingType ?? this.utilityBillingType,
      utilityBillingPhoto: utilityBillingPhoto ?? this.utilityBillingPhoto,
    );
  }

  bool get hasPhilsysPhoto => philsysIdPhoto != null && philsysIdPhoto!.isNotEmpty;
  bool get hasSecondaryIdPhoto => secondaryIdPhoto != null && secondaryIdPhoto!.isNotEmpty;
  bool get hasUtilityBillingPhoto => utilityBillingPhoto != null && utilityBillingPhoto!.isNotEmpty;

  int get proofDocumentsCount {
    int count = 0;
    if (hasPhilsysPhoto) count++;
    if (hasSecondaryIdPhoto) count++;
    if (hasUtilityBillingPhoto) count++;
    return count;
  }
  
  /// Convenience getter to check if the user is a resident
  bool get isResident => role.toUpperCase() == 'RESIDENT';

  /// Convenience getter to check if the user is an official or admin
  bool get isOfficial =>
      role.toUpperCase() == 'BARANGAY_OFFICIAL' ||
      role.toUpperCase() == 'ADMIN' ||
      role.toUpperCase() == 'FIELD_OFFICIAL';

  /// Whether this client understands and can safely route the account role.
  bool get isSupportedRole => !isSuperuser && const {
        'RESIDENT',
        'ADMIN',
        'FIELD_OFFICIAL',
      }.contains(role.toUpperCase());

  /// Convenience getter to check specifically if user has field duties
  bool get isFieldOfficial =>
      role.toUpperCase() == 'FIELD_OFFICIAL' ||
      role.toUpperCase() == 'ADMIN';

  /// Formatted role string for badges and official profile headers
  String get roleDisplay {
    switch (role.toUpperCase()) {
      case 'ADMIN':
        return 'Barangay Executive';
      case 'FIELD_OFFICIAL':
        return 'Field Official / Tanod';
      default:
        return 'Resident';
    }
  }
  @override
  String toString() => 'UserModel(id: $id, username: $username, fullName: $fullName, role: $role)';
}
