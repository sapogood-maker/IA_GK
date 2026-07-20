import 'package:flutter/foundation.dart';
import '../services/goalkeeper_service.dart';
import '../models/goalkeeper.dart';

class GoalkeeperProvider with ChangeNotifier {
  final GoalkeeperService _service;

  GoalkeeperProvider(this._service);

  List<Goalkeeper> _goalkeepers = [];
  bool _isLoading = false;
  String? _errorMessage;

  List<Goalkeeper> get goalkeepers => _goalkeepers;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> loadAll() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _goalkeepers = await _service.getAllGoalkeepers();
    } catch (_) {
      _errorMessage = 'Não foi possível carregar os goleiros.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> createGoalkeeper(Goalkeeper goalkeeper) async {
    try {
      await _service.createGoalkeeper(goalkeeper);
      await loadAll();
      return true;
    } catch (_) {
      _errorMessage = 'Não foi possível cadastrar o goleiro.';
      notifyListeners();
      return false;
    }
  }

  Future<List<Goalkeeper>> getGoalkeepersByClubId(String clubId) async {
    return await _service.getGoalkeepersByClubId(clubId);
  }

  Future<Goalkeeper> getGoalkeeperById(String gkId) async {
    return await _service.getGoalkeeperById(gkId);
  }
}
