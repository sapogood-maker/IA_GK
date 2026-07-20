import 'package:flutter/foundation.dart';

import '../models/video.dart';
import '../repositories/video_repository.dart';

class VideoProvider extends ChangeNotifier {
  VideoProvider(this._repository);

  final VideoRepository _repository;

  List<Video> _videos = [];
  bool _isLoading = false;
  String? _errorMessage;

  bool _isUploading = false;
  double _uploadProgress = 0;
  String? _uploadError;

  List<Video> get videos => _videos;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  bool get isUploading => _isUploading;
  double get uploadProgress => _uploadProgress;
  String? get uploadError => _uploadError;

  Future<void> loadBySession(String trainingSessionId) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final videos = await _repository.getVideosBySession(trainingSessionId);
      final comStatus = await Future.wait(
        videos.map((video) async {
          try {
            final status = await _repository.getVideoStatus(video.id);
            return video.withJobStatus(
              jobStatus: status.jobStatus,
              jobProgress: status.progress,
            );
          } catch (_) {
            return video;
          }
        }),
      );
      _videos = comStatus;
    } catch (_) {
      _errorMessage = 'Não foi possível carregar os vídeos desta sessão.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> uploadVideo({
    required String trainingSessionId,
    required String filename,
    required List<int> bytes,
  }) async {
    _isUploading = true;
    _uploadProgress = 0;
    _uploadError = null;
    notifyListeners();

    try {
      await _repository.uploadVideo(
        trainingSessionId: trainingSessionId,
        filename: filename,
        bytes: bytes,
        onSendProgress: (sent, total) {
          if (total > 0) {
            _uploadProgress = sent / total;
            notifyListeners();
          }
        },
      );
      await loadBySession(trainingSessionId);
      return true;
    } catch (_) {
      _uploadError = 'Não foi possível enviar o vídeo. Tente novamente.';
      notifyListeners();
      return false;
    } finally {
      _isUploading = false;
      _uploadProgress = 0;
      notifyListeners();
    }
  }
}
