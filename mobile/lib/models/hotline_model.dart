class HotlineModel {
  final int id;
  final String name;
  final String number;
  final String category;
  final String categoryDisplay;
  final bool isActive;

  const HotlineModel({
    required this.id,
    required this.name,
    required this.number,
    required this.category,
    required this.categoryDisplay,
    this.isActive = true,
  });

  factory HotlineModel.fromJson(Map<String, dynamic> json) {
    final cat = json['category'] as String? ?? 'OTHER';
    return HotlineModel(
      id: json['id'] as int? ?? 0,
      name: json['name'] as String? ?? '',
      number: json['number'] as String? ?? '',
      category: cat,
      categoryDisplay:
          json['category_display'] as String? ?? _getCategoryDisplay(cat),
      isActive: json['is_active'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'number': number,
    'category': category,
    'category_display': categoryDisplay,
    'is_active': isActive,
  };

  static String _getCategoryDisplay(String cat) {
    switch (cat.toUpperCase()) {
      case 'POLICE':
        return 'Police';
      case 'FIRE':
        return 'Fire Department';
      case 'MEDICAL':
        return 'Medical / Hospital';
      case 'BARANGAY':
        return 'Barangay Desk';
      default:
        return 'Other Emergency';
    }
  }
}
