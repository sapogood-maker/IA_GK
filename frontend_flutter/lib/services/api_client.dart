import 'package:dio/dio.dart';

import '../core/api_config.dart';
import '../models/auth_tokens.dart';
import 'session_service.dart';

class ApiClient {
  ApiClient(this._sessionService) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final token = _sessionService.accessToken;
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onResponse: (response, handler) {
          if (response.statusCode == 401) {
            _refreshToken();
          }
          handler.next(response);
        },
      ),
    );
  }

  final SessionService _sessionService;
  final Dio _dio = Dio(BaseOptions(baseUrl: ApiConfig.baseUrl));

  Dio get dio => _dio;

  Future<bool> _refreshToken() async {
    final refreshToken = _sessionService.refreshToken;
    if (refreshToken == null || refreshToken.isEmpty) {
      await _sessionService.clear();
      return false;
    }

    try {
      final response = await Dio(
        BaseOptions(baseUrl: ApiConfig.baseUrl),
      ).post<Map<String, dynamic>>(
        '/api/v1/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      final tokens = AuthTokens.fromJson(response.data ?? {});
      await _sessionService.saveTokens(
        accessToken: tokens.accessToken,
        refreshToken: tokens.refreshToken,
      );
      return true;
    } catch (e) {
      await _sessionService.clear();
      return false;
    }
  }
}
