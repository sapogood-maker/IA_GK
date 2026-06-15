import 'package:dio/dio.dart';

import '../models/auth_tokens.dart';
import '../models/auth_user.dart';
import '../services/api_client.dart';
import '../services/session_service.dart';

class AuthRepository {
  AuthRepository(this._apiClient, this._sessionService);

  final ApiClient _apiClient;
  final SessionService _sessionService;

  Future<AuthTokens> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _apiClient.dio.post<Map<String, dynamic>>(
        '/api/v1/auth/login',
        data: {'email': email, 'password': password},
      );
      return AuthTokens.fromJson(response.data ?? {});
    } catch (e) {
      throw Exception(friendlyError(e));
    }
  }

  Future<AuthTokens> register({
    required String name,
    required String email,
    required String password,
    String role = 'viewer',
  }) async {
    try {
      final response = await _apiClient.dio.post<Map<String, dynamic>>(
        '/api/v1/auth/register',
        data: {'name': name, 'email': email, 'password': password, 'role': role},
      );
      return AuthTokens.fromJson(response.data ?? {});
    } catch (e) {
      throw Exception(friendlyError(e));
    }
  }

  Future<AuthTokens> refresh() async {
    try {
      final response = await _apiClient.dio.post<Map<String, dynamic>>(
        '/api/v1/auth/refresh',
        data: {'refresh_token': _sessionService.refreshToken},
      );
      return AuthTokens.fromJson(response.data ?? {});
    } catch (e) {
      throw Exception(friendlyError(e));
    }
  }

  Future<AuthUser> me() async {
    try {
      final token = _sessionService.accessToken;
      final response = await _apiClient.dio.get<Map<String, dynamic>>(
        '/api/v1/auth/me',
        queryParameters: token == null
            ? null
            : {'authorization': 'Bearer $token'},
      );
      return AuthUser.fromJson(response.data ?? {});
    } catch (e) {
      throw Exception(friendlyError(e));
    }
  }

  String friendlyError(Object error) {
    if (error is DioException) {
      final statusCode = error.response?.statusCode;
      if (statusCode == 401) {
        return 'E-mail ou senha inválidos.';
      }
      if (statusCode == 400) {
        return 'Confira os dados informados e tente novamente.';
      }
      if (statusCode == null) {
        return 'Não foi possível conectar ao servidor.';
      }
    }
    return 'Não foi possível concluir a operação. Tente novamente.';
  }
}
