import 'package:flutter/foundation.dart';

import '../models/auth_user.dart';
import '../repositories/auth_repository.dart';
import '../services/session_service.dart';

enum AuthStatus { loading, authenticated, unauthenticated }

class AuthProvider extends ChangeNotifier {
  AuthProvider(this._authRepository, this._sessionService);

  final AuthRepository _authRepository;
  final SessionService _sessionService;

  AuthStatus _status = AuthStatus.loading;
  AuthUser? _user;
  String? _errorMessage;

  AuthStatus get status => _status;
  AuthUser? get user => _user;
  String? get errorMessage => _errorMessage;
  bool get isAuthenticated => _status == AuthStatus.authenticated;
  bool get isLoading => _status == AuthStatus.loading;

  Future<void> initialize() async {
    if (!_sessionService.hasSession) {
      _status = AuthStatus.unauthenticated;
      notifyListeners();
      return;
    }

    try {
      _user = await _authRepository.me();
      _status = AuthStatus.authenticated;
    } catch (_) {
      await _sessionService.clear();
      _status = AuthStatus.unauthenticated;
    }
    notifyListeners();
  }

  Future<bool> login({required String email, required String password}) async {
    _status = AuthStatus.loading;
    _errorMessage = null;
    notifyListeners();

    try {
      final tokens = await _authRepository.login(
        email: email,
        password: password,
      );
      await _sessionService.saveTokens(
        accessToken: tokens.accessToken,
        refreshToken: tokens.refreshToken,
      );
      _user = await _authRepository.me();
      _status = AuthStatus.authenticated;
      notifyListeners();
      return true;
    } catch (error) {
      await _sessionService.clear();
      _errorMessage = _authRepository.friendlyError(error);
      _status = AuthStatus.unauthenticated;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await _sessionService.clear();
    _user = null;
    _errorMessage = null;
    _status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}
