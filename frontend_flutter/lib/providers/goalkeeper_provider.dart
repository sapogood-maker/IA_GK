import 'package:flutter/material.dart';
import '../services/goalkeeper_service.dart';
import '../models/goalkeeper.dart';

class GoalkeeperProvider with ChangeNotifier {
  final GoalkeeperService _service;

  GoalkeeperProvider(this._service);

  Future<void> createGoalkeeper(Goalkeeper goalkeeper) async {
    try {
      await _service.createGoalkeeper(goalkeeper);
      // Notify listeners or update state as needed
    } catch (e) {
      print('Error creating goalkeeper: $e');
    }
  }
}
