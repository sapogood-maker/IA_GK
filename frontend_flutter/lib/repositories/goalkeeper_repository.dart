import '../models/goalkeeper.dart';
import '../services/api_client.dart';

class GoalkeeperRepository {
  final ApiClient _apiClient;

  GoalkeeperRepository(this._apiClient);

  Future<Goalkeeper> createGoalkeeper(Goalkeeper goalkeeper) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/api/v1/goalkeepers',
      data: goalkeeper.toJson(),
    );

    if (response.statusCode == 201) {
      return Goalkeeper.fromJson(response.data);
    } else {
      throw Exception('Failed to create goalkeeper');
    }
  }

  Future<List<Goalkeeper>> getGoalkeepersByClubId(String clubId) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/api/v1/goalkeepers',
      queryParameters: {'club_id': clubId},
    );

    if (response.statusCode == 200) {
      return (response.data as List).map((item) => Goalkeeper.fromJson(item)).toList();
    } else {
      throw Exception('Failed to fetch goalkeepers');
    }
  }

  Future<Goalkeeper> getGoalkeeperById(String gkId) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/api/v1/goalkeepers/$gkId',
    );

    if (response.statusCode == 200) {
      return Goalkeeper.fromJson(response.data);
    } else {
      throw Exception('Failed to fetch goalkeeper');
    }
  }
}
