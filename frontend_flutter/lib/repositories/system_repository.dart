import '../services/api_client.dart';

class R2Health {
  const R2Health({
    required this.status,
    required this.bucket,
    required this.readAccess,
    required this.writeAccess,
  });

  factory R2Health.fromJson(Map<String, dynamic> json) {
    return R2Health(
      status: json['status'] as String? ?? '',
      bucket: json['bucket'] as String? ?? '',
      readAccess: json['read_access'] as bool? ?? false,
      writeAccess: json['write_access'] as bool? ?? false,
    );
  }

  final String status;
  final String bucket;
  final bool readAccess;
  final bool writeAccess;
}

class SystemRepository {
  SystemRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<R2Health> checkR2Health() async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/api/v1/r2/health',
    );
    return R2Health.fromJson(response.data!);
  }
}
