import 'package:flutter/foundation.dart';

import '../models/club.dart';
import '../repositories/club_repository.dart';

class ClubProvider extends ChangeNotifier {
  ClubProvider(this._repository);

  final ClubRepository _repository;

  List<Club> _clubs = [];
  bool _isLoading = false;
  String? _errorMessage;

  List<Club> get clubs => _clubs;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> load() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _clubs = await _repository.getClubs();
    } catch (_) {
      _errorMessage = 'Não foi possível carregar os clubes.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
