import 'package:dio/dio.dart';

import '../models/video.dart';
import '../services/api_client.dart';

class VideoStatus {
  const VideoStatus({
    required this.videoId,
    required this.videoStatus,
    this.jobStatus,
    this.progress,
    this.r2Url,
  });

  factory VideoStatus.fromJson(Map<String, dynamic> json) {
    return VideoStatus(
      videoId: json['video_id'] as String,
      videoStatus: json['video_status'] as String,
      jobStatus: json['job_status'] as String?,
      progress: (json['progress'] as num?)?.toDouble(),
      r2Url: json['r2_url'] as String?,
    );
  }

  final String videoId;
  final String videoStatus;
  final String? jobStatus;
  final double? progress;
  final String? r2Url;
}

class VideoRepository {
  VideoRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<List<Video>> getVideosBySession(String trainingSessionId) async {
    final response = await _apiClient.dio.get<List<dynamic>>(
      '/api/v1/videos',
      queryParameters: {'training_session_id': trainingSessionId},
    );

    if (response.statusCode == 200) {
      return response.data!.map((item) => Video.fromJson(item)).toList();
    } else {
      throw Exception('Failed to fetch videos');
    }
  }

  Future<VideoStatus> getVideoStatus(String videoId) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/api/v1/videos/$videoId/status',
    );

    if (response.statusCode == 200) {
      return VideoStatus.fromJson(response.data!);
    } else {
      throw Exception('Failed to fetch video status');
    }
  }

  Future<void> uploadVideo({
    required String trainingSessionId,
    required String filename,
    required List<int> bytes,
    void Function(int sent, int total)? onSendProgress,
  }) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(bytes, filename: filename),
    });

    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/api/v1/videos/upload',
      queryParameters: {'training_session_id': trainingSessionId},
      data: formData,
      onSendProgress: onSendProgress,
    );

    if (response.statusCode != 201) {
      throw Exception('Failed to upload video');
    }
  }
}
