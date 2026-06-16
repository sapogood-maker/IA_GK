class Goalkeeper {
  final String id;
  final String name;
  final DateTime? birthDate;
  final String? dominantHand;
  final int? heightCm;
  final double? weightKg;

  Goalkeeper({
    required this.id,
    required this.name,
    this.birthDate,
    this.dominantHand,
    this.heightCm,
    this.weightKg,
  });

  factory Goalkeeper.fromJson(Map<String, dynamic> json) {
    return Goalkeeper(
      id: json['id'] as String,
      name: json['name'] as String,
      birthDate: json['birth_date'] != null ? DateTime.parse(json['birth_date']) : null,
      dominantHand: json['dominant_hand'] as String?,
      heightCm: json['height_cm'] as int?,
      weightKg: json['weight_kg'] as double?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'birth_date': birthDate?.toIso8601String(),
      'dominant_hand': dominantHand,
      'height_cm': heightCm,
      'weight_kg': weightKg,
    };
  }
}
