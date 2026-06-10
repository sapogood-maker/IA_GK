class DashboardData {
  const DashboardData({
    required this.videos,
    required this.jobsConcluidos,
    required this.jobsEmProcessamento,
    required this.clubes,
    required this.sessoesRecentes,
    required this.analises,
  });

  final List<Map<String, dynamic>> videos;
  final List<Map<String, dynamic>> jobsConcluidos;
  final List<Map<String, dynamic>> jobsEmProcessamento;
  final List<Map<String, dynamic>> clubes;
  final List<Map<String, dynamic>> sessoesRecentes;
  final List<Map<String, dynamic>> analises;

  int get totalVideos => videos.length;
  int get totalClubes => clubes.length;
  int get totalSessoes => sessoesRecentes.length;
  int get totalAnalisesConcluidas => jobsConcluidos.length;
  int get totalEmProcessamento => jobsEmProcessamento.length;

  bool get hasAnyData =>
      videos.isNotEmpty ||
      jobsConcluidos.isNotEmpty ||
      jobsEmProcessamento.isNotEmpty ||
      clubes.isNotEmpty ||
      sessoesRecentes.isNotEmpty ||
      analises.isNotEmpty;
}
