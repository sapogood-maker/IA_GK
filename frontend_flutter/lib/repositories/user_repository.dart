import '../models/auth_user.dart';
import '../services/api_client.dart';

class UserRepository {
  UserRepository(this._apiClient);

  final ApiClient _apiClient;

  /// Lista todos os usuarios do sistema. Restrito a SYSTEM_ADMIN no
  /// backend - lanca DioException com status 403 para os demais papeis.
  Future<List<AuthUser>> getAllUsers() async {
    final response = await _apiClient.dio.get<List<dynamic>>('/api/v1/users');

    if (response.statusCode == 200) {
      return response.data!.map((item) => AuthUser.fromJson(item)).toList();
    } else {
      throw Exception('Failed to fetch users');
    }
  }
}
