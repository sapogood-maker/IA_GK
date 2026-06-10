import '../models/dashboard_data.dart';
import '../services/api_client.dart';

class DashboardRepository {
  DashboardRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<DashboardData> fetchDashboardData() async {
    final results = await Future.wait<List<Map<String, dynamic>>>([
      _getList('/api/v1/videos'),
      _getList('/api/v1/processing-jobs', queryParameters: {'status': 'DONE'}),
      _getList(
        '/api/v1/processing-jobs',
        queryParameters: {'status': 'PROCESSING'},
      ),
      _getList('/api/v1/clubs'),
      _getList('/api/v1/training-sessions'),
      _getList('/api/v1/processing-jobs'),
    ]);

    return DashboardData(
      videos: results[0],
      jobsConcluidos: results[1],
      jobsEmProcessamento: results[2],
      clubes: results[3],
      sessoesRecentes: results[4],
      analises: results[5],
    );
  }

  Future<List<Map<String, dynamic>>> _getList(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      final response = await _apiClient.dio.get<List<dynamic>>(
        path,
        queryParameters: queryParameters,
      );
      return (response.data ?? [])
          .whereType<Map>()
          .map((item) => item.cast<String, dynamic>())
          .toList();
    } catch (_) {
      return const [];
    }
  }
}
