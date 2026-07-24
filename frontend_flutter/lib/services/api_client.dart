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
        // Dio so chama onResponse para respostas 2xx (validateStatus
        // padrao) - um 401 vira DioException e passa por onError, nunca
        // por onResponse. Sem isso aqui, o token expirado (padrao 30min,
        // JWT_EXPIRATION_MINUTES) nunca era renovado e toda chamada
        // seguinte falhava com 401 ate o usuario deslogar/logar de novo.
        onError: (error, handler) async {
          final isUnauthorized = error.response?.statusCode == 401;
          final alreadyRetried =
              error.requestOptions.extra['retried_after_refresh'] == true;

          if (!isUnauthorized || alreadyRetried) {
            handler.next(error);
            return;
          }

          final refreshed = await _refreshToken();
          if (!refreshed) {
            handler.next(error);
            return;
          }

          try {
            final retryOptions = error.requestOptions;
            retryOptions.extra['retried_after_refresh'] = true;
            retryOptions.headers['Authorization'] =
                'Bearer ${_sessionService.accessToken}';
            final response = await _dio.fetch(retryOptions);
            handler.resolve(response);
          } catch (_) {
            handler.next(error);
          }
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
