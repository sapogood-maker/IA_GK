import '../models/club.dart';
import '../services/api_client.dart';

class ClubRepository {
  ClubRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<List<Club>> getClubs() async {
    final response = await _apiClient.dio.get<List<dynamic>>(
      '/api/v1/clubs',
    );

    if (response.statusCode == 200) {
      return response.data!.map((item) => Club.fromJson(item)).toList();
    } else {
      throw Exception('Failed to fetch clubs');
    }
  }
}
