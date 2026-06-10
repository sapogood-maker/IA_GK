import 'package:flutter/foundation.dart';

import '../models/dashboard_data.dart';
import '../repositories/dashboard_repository.dart';

class DashboardProvider extends ChangeNotifier {
  DashboardProvider(this._repository);

  final DashboardRepository _repository;

  DashboardData? _data;
  bool _isLoading = false;
  String? _errorMessage;

  DashboardData? get data => _data;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> load() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _data = await _repository.fetchDashboardData();
    } catch (_) {
      _errorMessage = 'Não foi possível carregar os dados do painel.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
