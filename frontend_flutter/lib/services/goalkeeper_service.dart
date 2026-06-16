import '../repositories/goalkeeper_repository.dart';
import '../models/goalkeeper.dart';

class GoalkeeperService {
  final GoalkeeperRepository _repository;

  GoalkeeperService(this._repository);

  Future<Goalkeeper> createGoalkeeper(Goalkeeper goalkeeper) async {
    return await _repository.createGoalkeeper(goalkeeper);
  }
}
