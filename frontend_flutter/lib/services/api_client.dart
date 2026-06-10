import 'package:dio/dio.dart';

import '../core/api_config.dart';
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
        onError: (error, handler) async {
          final statusCode = error.response?.statusCode;
          final isRefreshRequest = error.requestOptions.path.contains(
            '/api/v1/auth/refresh',
          );

          if (statusCode == 401 && !isRefreshRequest) {
            final refreshed = await _refreshToken();
            if (refreshed) {
              try {
                final retry = await _dio.fetch<dynamic>(
                  error.requestOptions
                    ..headers['Authorization'] =
                        'Bearer ${_sessionService.accessToken}',
                );
                handler.resolve(retry);
                return;
              } on DioException catch (retryError) {
                handler.next(retryError);
                return;
              }
            }
          }

          handler.next(error);
        },
      ),
    );
  }

  final SessionService _sessionService;
  final Dio _dio = Dio(
    BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      connectTimeout: const Duration(seconds: 12),
      receiveTimeout: const Duration(seconds: 20),
      headers: {'Accept': 'application/json'},
    ),
  );

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
      ).post('/api/v1/auth/refresh', data: {'refresh_token': refreshToken});
      final data = response.data as Map<String, dynamic>;
      await _sessionService.saveTokens(
        accessToken: data['access_token'] as String,
        refreshToken: data['refresh_token'] as String,
      );
      return true;
    } on DioException {
      await _sessionService.clear();
      return false;
    }
  }
}
