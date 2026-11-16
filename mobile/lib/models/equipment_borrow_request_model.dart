import 'package:flutter/material.dart';

/// Immutable model representing a barangay equipment or facility borrowing request.
class EquipmentBorrowRequestModel {
  final int id;
  final int? residentId;
  final String residentName;
  final String itemType;
  final int quantity;
  final String borrowDate;
  final String returnDate;
  final String timeSlot;
  final String purpose;
  final String status;
  final String adminNotes;
  final String? reviewedByName;
  final DateTime? reviewedAt;
  final DateTime? returnedAt;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  static const List<String> defaultItemTypes = [
    'Monoblock Chairs',
    'Tent / Canopy',
    'Sound System',
    'Tables',
    'Covered Court / Multi-Purpose Hall',
    'Other',
  ];

  const EquipmentBorrowRequestModel({
    required this.id,
    this.residentId,
    this.residentName = 'Resident',
    required this.itemType,
    this.quantity = 1,
    required this.borrowDate,
    required this.returnDate,
    this.timeSlot = '',
    required this.purpose,
    this.status = 'PENDING',
    this.adminNotes = '',
    this.reviewedByName,
    this.reviewedAt,
    this.returnedAt,
    this.createdAt,
    this.updatedAt,
  });

  factory EquipmentBorrowRequestModel.fromJson(Map<String, dynamic> json) {
    final rawId = json['id'];
    final rawQuantity = json['quantity'];
    return EquipmentBorrowRequestModel(
      id: rawId is int
          ? rawId
          : int.tryParse(rawId?.toString() ?? '') ?? 0,
      residentId: (json['resident'] as num?)?.toInt(),
      residentName: json['resident_name']?.toString() ?? 'Resident',
      itemType: json['item_type']?.toString() ?? defaultItemTypes.first,
      quantity: rawQuantity is num
          ? rawQuantity.toInt()
          : int.tryParse(rawQuantity?.toString() ?? '') ?? 1,
      borrowDate: json['borrow_date']?.toString() ?? '',
      returnDate: json['return_date']?.toString() ?? '',
      timeSlot: json['time_slot']?.toString() ?? '',
      purpose: json['purpose']?.toString() ?? '',
      status: json['status']?.toString() ?? 'PENDING',
      adminNotes: json['admin_notes']?.toString() ?? '',
      reviewedByName: json['reviewed_by_name']?.toString(),
      reviewedAt: json['reviewed_at'] != null
          ? DateTime.tryParse(json['reviewed_at'].toString())
          : null,
      returnedAt: json['returned_at'] != null
          ? DateTime.tryParse(json['returned_at'].toString())
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString())
          : null,
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'].toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'resident': residentId,
      'resident_name': residentName,
      'item_type': itemType,
      'quantity': quantity,
      'borrow_date': borrowDate,
      'return_date': returnDate,
      'time_slot': timeSlot,
      'purpose': purpose,
      'status': status,
      'admin_notes': adminNotes,
      'reviewed_by_name': reviewedByName,
      'reviewed_at': reviewedAt?.toIso8601String(),
      'returned_at': returnedAt?.toIso8601String(),
      'created_at': createdAt?.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
    };
  }

  bool get isPending => status.toUpperCase() == 'PENDING';
  bool get isApproved => status.toUpperCase() == 'APPROVED';
  bool get isDeclined => status.toUpperCase() == 'DECLINED';
  bool get isReturned => status.toUpperCase() == 'RETURNED';

  String get formattedSchedule {
    final range = '$borrowDate → $returnDate';
    if (timeSlot.trim().isEmpty) return range;
    return '$range ($timeSlot)';
  }

  String get statusDisplay {
    switch (status.toUpperCase()) {
      case 'APPROVED':
        return 'Approved';
      case 'DECLINED':
        return 'Declined';
      case 'RETURNED':
        return 'Returned';
      case 'PENDING':
      default:
        return 'Pending';
    }
  }

  Color get statusBadgeBgColor {
    switch (status.toUpperCase()) {
      case 'APPROVED':
        return const Color(0xFFDCFCE7);
      case 'DECLINED':
        return const Color(0xFFFEE2E2);
      case 'RETURNED':
        return const Color(0xFFF1F5F9);
      case 'PENDING':
      default:
        return const Color(0xFFFEF3C7);
    }
  }

  Color get statusBadgeTextColor {
    switch (status.toUpperCase()) {
      case 'APPROVED':
        return const Color(0xFF15803D);
      case 'DECLINED':
        return const Color(0xFFDC2626);
      case 'RETURNED':
        return const Color(0xFF475569);
      case 'PENDING':
      default:
        return const Color(0xFFB45309);
    }
  }
}
