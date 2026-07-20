class Club {
  const Club({required this.id, required this.name, this.city});

  factory Club.fromJson(Map<String, dynamic> json) {
    return Club(
      id: json['id'] as String,
      name: json['name'] as String,
      city: json['city'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {'name': name, 'city': city};
  }

  final String id;
  final String name;
  final String? city;
}
