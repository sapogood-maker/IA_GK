import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../repositories/system_repository.dart';

class SystemProvider extends ChangeNotifier {
  SystemProvider(this._repository);

  final SystemRepository _repository;

  R2Health? _r2Health;
  bool _isLoading = false;
  bool _isForbidden = false;
  String? _errorMessage;

  R2Health? get r2Health => _r2Health;
  bool get isLoading => _isLoading;
  bool get isForbidden => _isForbidden;
  String? get errorMessage => _errorMessage;

  Future<void> loadR2Health() async {
    _isLoading = true;
    _errorMessage = null;
    _isForbidden = false;
    notifyListeners();

    try {
      _r2Health = await _repository.checkR2Health();
    } on DioException catch (e) {
      if (e.response?.statusCode == 403) {
        _isForbidden = true;
      } else {
        _errorMessage =
            e.response?.data is Map
                ? (e.response?.data['detail']?.toString() ??
                      'R2 indisponível.')
                : 'R2 indisponível.';
      }
    } catch (_) {
      _errorMessage = 'R2 indisponível.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
