import 'package:equatable/equatable.dart';

class CreatePipelineState extends Equatable {
  final List<String> repos;
  final String selectedRepo;
  final String selectedModel;
  final List<Map<String, dynamic>> issues;
  final Set<int> selectedIssueNumbers;
  final bool loadingRepos;
  final bool loadingIssues;
  final bool loadingMoreIssues;
  final bool submitting;
  final String? issuesCursor;
  final bool hasMoreIssues;

  const CreatePipelineState({
    this.repos = const [],
    this.selectedRepo = '',
    this.selectedModel = 'claude-opus-4-6',
    this.issues = const [],
    this.selectedIssueNumbers = const {},
    this.loadingRepos = true,
    this.loadingIssues = false,
    this.loadingMoreIssues = false,
    this.submitting = false,
    this.issuesCursor,
    this.hasMoreIssues = false,
  });

  CreatePipelineState copyWith({
    List<String>? repos,
    String? selectedRepo,
    String? selectedModel,
    List<Map<String, dynamic>>? issues,
    Set<int>? selectedIssueNumbers,
    bool? loadingRepos,
    bool? loadingIssues,
    bool? loadingMoreIssues,
    bool? submitting,
    String? issuesCursor,
    bool clearCursor = false,
    bool? hasMoreIssues,
  }) {
    return CreatePipelineState(
      repos: repos ?? this.repos,
      selectedRepo: selectedRepo ?? this.selectedRepo,
      selectedModel: selectedModel ?? this.selectedModel,
      issues: issues ?? this.issues,
      selectedIssueNumbers: selectedIssueNumbers ?? this.selectedIssueNumbers,
      loadingRepos: loadingRepos ?? this.loadingRepos,
      loadingIssues: loadingIssues ?? this.loadingIssues,
      loadingMoreIssues: loadingMoreIssues ?? this.loadingMoreIssues,
      submitting: submitting ?? this.submitting,
      issuesCursor: clearCursor ? null : (issuesCursor ?? this.issuesCursor),
      hasMoreIssues: hasMoreIssues ?? this.hasMoreIssues,
    );
  }

  @override
  List<Object?> get props => [
        repos,
        selectedRepo,
        selectedModel,
        issues,
        selectedIssueNumbers,
        loadingRepos,
        loadingIssues,
        loadingMoreIssues,
        submitting,
        issuesCursor,
        hasMoreIssues,
      ];
}
