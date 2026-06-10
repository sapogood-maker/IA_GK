import 'package:shared_preferences/shared_preferences.dart';

class SessionService {
  SessionService(this._preferences);

  static const _accessTokenKey = 'access_token';
  static const _refreshTokenKey = 'refresh_token';

  final SharedPreferences _preferences;

  String? get accessToken => _preferences.getString(_accessTokenKey);
  String? get refreshToken => _preferences.getString(_refreshTokenKey);
  bool get hasSession => accessToken != null && refreshToken != null;

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _preferences.setString(_accessTokenKey, accessToken);
    await _preferences.setString(_refreshTokenKey, refreshToken);
  }

  Future<void> clear() async {
    await _preferences.remove(_accessTokenKey);
    await _preferences.remove(_refreshTokenKey);
  }
}
