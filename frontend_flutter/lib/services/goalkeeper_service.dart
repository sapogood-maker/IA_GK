import '../repositories/goalkeeper_repository.dart';
import '../models/goalkeeper.dart';

class GoalkeeperService {
  final GoalkeeperRepository _repository;

  GoalkeeperService(this._repository);

  Future<Goalkeeper> createGoalkeeper(Goalkeeper goalkeeper) async {
    return await _repository.createGoalkeeper(goalkeeper);
  }

  Future<List<Goalkeeper>> getGoalkeepersByClubId(String clubId) async {
    return await _repository.getGoalkeepersByClubId(clubId);
  }

  Future<List<Goalkeeper>> getAllGoalkeepers() async {
    return await _repository.getAllGoalkeepers();
  }

  Future<Goalkeeper> getGoalkeeperById(String gkId) async {
    return await _repository.getGoalkeeperById(gkId);
  }
}
