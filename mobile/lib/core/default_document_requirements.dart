class DefaultDocumentOffering {
  final String documentType;
  final List<String> requirements;
  final double? publishedFee;
  final String details;

  const DefaultDocumentOffering({
    required this.documentType,
    required this.requirements,
    this.publishedFee,
    this.details = '',
  });
}

class DefaultDocumentRequirements {
  static const List<DefaultDocumentOffering> defaults = [
    DefaultDocumentOffering(
      documentType: 'Barangay Clearance',
      requirements: [
        'Government ID or proof of residency',
        'Community Tax Certificate (Cedula)',
      ],
      publishedFee: 50.0,
      details:
          'Standard clearance for employment, identification, and official transactions.',
    ),
    DefaultDocumentOffering(
      documentType: 'Certificate of Indigency',
      requirements: [
        'Government ID or proof of residency',
        'Proof of indigent status or declaration of low income',
      ],
      publishedFee: 0.0,
      details:
          'Statutory fee-exempt certificate for social welfare, medical, and legal assistance.',
    ),
    DefaultDocumentOffering(
      documentType: 'Certificate of Residency',
      requirements: [
        'Government ID',
        'Proof of address (utility bill, lease contract, or voter certification)',
      ],
      publishedFee: 50.0,
      details:
          'Official certification verifying residency address within the Barangay.',
    ),
    DefaultDocumentOffering(
      documentType: 'Barangay Business Clearance',
      requirements: [
        'Government ID of owner or representative',
        'DTI or SEC Certificate of Registration',
        'Contract of lease or proof of property ownership',
      ],
      publishedFee: 200.0,
      details:
          'Clearance required for new business registration or annual business permit renewal.',
    ),
  ];

  static String normalize(String type) =>
      type.replaceAll(RegExp(r'\s+'), ' ').trim().toLowerCase();

  static DefaultDocumentOffering? find(String? documentType) {
    if (documentType == null || documentType.trim().isEmpty) return null;
    final target = normalize(documentType);
    for (final def in defaults) {
      if (normalize(def.documentType) == target) {
        return def;
      }
    }
    if (target.contains('business') || target.contains('permit')) {
      return defaults.firstWhere(
        (d) => d.documentType == 'Barangay Business Clearance',
      );
    }
    if (target.contains('clearance')) {
      return defaults.first;
    }
    if (target.contains('indigency')) {
      return defaults[1];
    }
    if (target.contains('residency')) {
      return defaults[2];
    }
    return null;
  }

  static bool hasDefaults(String? documentType) => find(documentType) != null;

  static List<String> getRequirements(String? documentType) =>
      find(documentType)?.requirements ?? const [];

  static double? getPublishedFee(String? documentType) =>
      find(documentType)?.publishedFee;

  static String getDetails(String? documentType) =>
      find(documentType)?.details ?? '';
}

