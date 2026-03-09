class Pipeline {
  final String pipelineKey;
  final String repoPath;
  final int? issueNumber;
  final String? issueTitle;
  final String? taskDescription;
  final String status;
  final String? plan;
  final String? branch;
  final int? prNumber;
  final String? prUrl;
  final String? error;
  final int reviewRound;
  final String model;
  final int? templateId;
  final String? templateName;
  final double totalCostUsd;
  final DateTime createdAt;
  final DateTime updatedAt;

  Pipeline({
    required this.pipelineKey,
    required this.repoPath,
    this.issueNumber,
    this.issueTitle,
    this.taskDescription,
    required this.status,
    this.plan,
    this.branch,
    this.prNumber,
    this.prUrl,
    this.error,
    this.reviewRound = 0,
    required this.model,
    this.templateId,
    this.templateName,
    this.totalCostUsd = 0,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Pipeline.fromJson(Map<String, dynamic> json) {
    return Pipeline(
      pipelineKey: json['pipeline_key'],
      repoPath: json['repo_path'] ?? '',
      issueNumber: json['issue_number'],
      issueTitle: json['issue_title'],
      taskDescription: json['task_description'],
      status: json['status'] ?? 'planning',
      plan: json['plan'],
      branch: json['branch'],
      prNumber: json['pr_number'],
      prUrl: json['pr_url'],
      error: json['error'],
      reviewRound: json['review_round'] ?? 0,
      model: json['model'] ?? 'sonnet',
      templateId: json['template_id'],
      templateName: json['template_name'],
      totalCostUsd: (json['total_cost_usd'] ?? 0).toDouble(),
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Pipeline copyWith({
    String? status,
    String? plan,
    String? branch,
    int? prNumber,
    String? prUrl,
    String? error,
    int? reviewRound,
    double? totalCostUsd,
  }) {
    return Pipeline(
      pipelineKey: pipelineKey,
      repoPath: repoPath,
      issueNumber: issueNumber,
      issueTitle: issueTitle,
      taskDescription: taskDescription,
      status: status ?? this.status,
      plan: plan ?? this.plan,
      branch: branch ?? this.branch,
      prNumber: prNumber ?? this.prNumber,
      prUrl: prUrl ?? this.prUrl,
      error: error ?? this.error,
      reviewRound: reviewRound ?? this.reviewRound,
      model: model,
      templateId: templateId,
      templateName: templateName,
      totalCostUsd: totalCostUsd ?? this.totalCostUsd,
      createdAt: createdAt,
      updatedAt: DateTime.now(),
    );
  }

  String get displayTitle =>
      issueTitle ?? taskDescription ?? 'Pipeline $pipelineKey';

  bool get isActive => const {
        'planning', 'planned', 'developing', 'developed', 'reviewing',
      }.contains(status);
}
