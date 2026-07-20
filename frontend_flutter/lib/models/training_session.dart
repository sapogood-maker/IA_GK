class TrainingSession {
  const TrainingSession({
    required this.id,
    required this.goalkeeperId,
    this.coachId,
    required this.title,
    required this.sessionType,
    required this.sessionDate,
    this.notes,
  });

  factory TrainingSession.fromJson(Map<String, dynamic> json) {
    return TrainingSession(
      id: json['id'] as String,
      goalkeeperId: json['goalkeeper_id'] as String,
      coachId: json['coach_id'] as String?,
      title: json['title'] as String,
      sessionType: json['session_type'] as String,
      sessionDate: DateTime.parse(json['session_date'] as String),
      notes: json['notes'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'goalkeeper_id': goalkeeperId,
      'coach_id': coachId,
      'title': title,
      'session_type': sessionType,
      'session_date': sessionDate.toIso8601String(),
      'notes': notes,
    };
  }

  final String id;
  final String goalkeeperId;
  final String? coachId;
  final String title;
  final String sessionType;
  final DateTime sessionDate;
  final String? notes;
}
