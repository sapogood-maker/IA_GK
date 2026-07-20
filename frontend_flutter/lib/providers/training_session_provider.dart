import 'package:flutter/foundation.dart';

import '../models/training_session.dart';
import '../repositories/training_session_repository.dart';

class TrainingSessionProvider extends ChangeNotifier {
  TrainingSessionProvider(this._repository);

  final TrainingSessionRepository _repository;

  List<TrainingSession> _sessions = [];
  bool _isLoading = false;
  String? _errorMessage;

  List<TrainingSession> get sessions => _sessions;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> loadAll() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _sessions = await _repository.getAllSessions();
    } catch (_) {
      _errorMessage = 'Não foi possível carregar as sessões de treino.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<List<TrainingSession>> getSessionsByGoalkeeperId(
    String goalkeeperId,
  ) async {
    return _repository.getSessionsByGoalkeeperId(goalkeeperId);
  }

  Future<bool> createSession(TrainingSession session) async {
    try {
      await _repository.createSession(session);
      await loadAll();
      return true;
    } catch (_) {
      _errorMessage = 'Não foi possível cadastrar a sessão de treino.';
      notifyListeners();
      return false;
    }
  }
}
