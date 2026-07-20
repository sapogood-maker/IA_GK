import '../models/training_session.dart';
import '../services/api_client.dart';

class TrainingSessionRepository {
  TrainingSessionRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<List<TrainingSession>> getAllSessions() async {
    final response = await _apiClient.dio.get<List<dynamic>>(
      '/api/v1/training-sessions',
    );

    if (response.statusCode == 200) {
      return response.data!
          .map((item) => TrainingSession.fromJson(item))
          .toList();
    } else {
      throw Exception('Failed to fetch training sessions');
    }
  }

  Future<List<TrainingSession>> getSessionsByGoalkeeperId(
    String goalkeeperId,
  ) async {
    final response = await _apiClient.dio.get<List<dynamic>>(
      '/api/v1/training-sessions',
      queryParameters: {'goalkeeper_id': goalkeeperId},
    );

    if (response.statusCode == 200) {
      return response.data!
          .map((item) => TrainingSession.fromJson(item))
          .toList();
    } else {
      throw Exception('Failed to fetch training sessions');
    }
  }

  Future<TrainingSession> createSession(TrainingSession session) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/api/v1/training-sessions',
      data: session.toJson(),
    );

    if (response.statusCode == 201) {
      return TrainingSession.fromJson(response.data!);
    } else {
      throw Exception('Failed to create training session');
    }
  }
}
