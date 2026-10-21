import 'package:flutter/foundation.dart';

@immutable
class DocumentOfferingModel {
  final int id;
  final String documentType;
  final List<String> requirements;
  final double? publishedFeeAmount;
  final String details;
  final bool isActive;

  const DocumentOfferingModel({
    required this.id,
    required this.documentType,
    this.requirements = const [],
    this.publishedFeeAmount,
    this.details = '',
    this.isActive = true,
  });

  factory DocumentOfferingModel.fromJson(Map<String, dynamic> json) {
    final rawRequirements = json['requirements'];
    final requirements = rawRequirements is List
        ? rawRequirements.map((item) => item.toString()).toList(growable: false)
        : const <String>[];
    final rawFee = json['published_fee_amount'];
    return DocumentOfferingModel(
      id: (json['id'] as num?)?.toInt() ?? 0,
      documentType: json['document_type'] as String? ?? '',
      requirements: requirements,
      publishedFeeAmount: rawFee is num
          ? rawFee.toDouble()
          : double.tryParse(rawFee?.toString() ?? ''),
      details: json['details'] as String? ?? '',
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}
