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

  Future<List<Goalkeeper>> getGoalkeepersByClubId(String clubId) async {
    try {
      final goalkeepers = await _service.getGoalkeepersByClubId(clubId);
      // Notify listeners or update state as needed
      return goalkeepers;
    } catch (e) {
      print('Error fetching goalkeepers: $e');
      throw e;
    }
  }

  Future<Goalkeeper> getGoalkeeperById(String gkId) async {
    try {
      final goalkeeper = await _service.getGoalkeeperById(gkId);
      // Notify listeners or update state as needed
      return goalkeeper;
    } catch (e) {
      print('Error fetching goalkeeper: $e');
      throw e;
    }
  }
}
