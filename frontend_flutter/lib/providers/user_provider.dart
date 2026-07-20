import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../models/auth_user.dart';
import '../repositories/user_repository.dart';

class UserProvider extends ChangeNotifier {
  UserProvider(this._repository);

  final UserRepository _repository;

  List<AuthUser> _users = [];
  bool _isLoading = false;
  String? _errorMessage;
  bool _isForbidden = false;

  List<AuthUser> get users => _users;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isForbidden => _isForbidden;

  Future<void> loadAll() async {
    _isLoading = true;
    _errorMessage = null;
    _isForbidden = false;
    notifyListeners();

    try {
      _users = await _repository.getAllUsers();
    } on DioException catch (e) {
      if (e.response?.statusCode == 403) {
        _isForbidden = true;
        _errorMessage = 'Acesso restrito a administradores do sistema.';
      } else {
        _errorMessage = 'Não foi possível carregar os usuários.';
      }
    } catch (_) {
      _errorMessage = 'Não foi possível carregar os usuários.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
