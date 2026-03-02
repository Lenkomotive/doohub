class Pipeline {
  final int id;
  final String pipelineKey;
  final String repo;
  final String repoPath;
  final int issueNumber;
  final String issueTitle;
  final String status;
  final int? prNumber;
  final String? branch;
  final int reviewRound;
  final String? plan;
  final String? error;
  final DateTime startedAt;
  final DateTime updatedAt;

  Pipeline({
    required this.id,
    required this.pipelineKey,
    required this.repo,
    required this.repoPath,
    required this.issueNumber,
    required this.issueTitle,
    required this.status,
    this.prNumber,
    this.branch,
    required this.reviewRound,
    this.plan,
    this.error,
    required this.startedAt,
    required this.updatedAt,
  });

  factory Pipeline.fromJson(Map<String, dynamic> json) {
    return Pipeline(
      id: json['id'],
      pipelineKey: json['pipeline_key'],
      repo: json['repo'],
      repoPath: json['repo_path'] ?? '',
      issueNumber: json['issue_number'],
      issueTitle: json['issue_title'],
      status: json['status'],
      prNumber: json['pr_number'],
      branch: json['branch'],
      reviewRound: json['review_round'] ?? 0,
      plan: json['plan'],
      error: json['error'],
      startedAt: DateTime.parse(json['started_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}
