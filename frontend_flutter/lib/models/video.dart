class Video {
  const Video({
    required this.id,
    required this.trainingSessionId,
    required this.filename,
    this.originalFilename,
    this.mimeType,
    this.fileSizeBytes,
    this.durationSeconds,
    this.r2Url,
    required this.uploadStatus,
    this.jobStatus,
    this.jobProgress,
  });

  factory Video.fromJson(Map<String, dynamic> json) {
    return Video(
      id: json['id'] as String,
      trainingSessionId: json['training_session_id'] as String,
      filename: json['filename'] as String,
      originalFilename: json['original_filename'] as String?,
      mimeType: json['mime_type'] as String?,
      fileSizeBytes: json['file_size_bytes'] as int?,
      durationSeconds: (json['duration_seconds'] as num?)?.toDouble(),
      r2Url: json['r2_url'] as String?,
      uploadStatus: json['upload_status'] as String? ?? 'PENDING',
    );
  }

  /// Retorna uma copia com o status de processamento (obtido via
  /// GET /api/v1/videos/{id}/status) mesclado ao registro do video.
  Video withJobStatus({String? jobStatus, double? jobProgress}) {
    return Video(
      id: id,
      trainingSessionId: trainingSessionId,
      filename: filename,
      originalFilename: originalFilename,
      mimeType: mimeType,
      fileSizeBytes: fileSizeBytes,
      durationSeconds: durationSeconds,
      r2Url: r2Url,
      uploadStatus: uploadStatus,
      jobStatus: jobStatus,
      jobProgress: jobProgress,
    );
  }

  final String id;
  final String trainingSessionId;
  final String filename;
  final String? originalFilename;
  final String? mimeType;
  final int? fileSizeBytes;
  final double? durationSeconds;
  final String? r2Url;
  final String uploadStatus;
  final String? jobStatus;
  final double? jobProgress;
}
