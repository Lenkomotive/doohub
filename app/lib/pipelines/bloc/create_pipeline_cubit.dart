import 'package:flutter_bloc/flutter_bloc.dart';
import '../../services/api.dart';
import 'create_pipeline_state.dart';
import 'pipelines_cubit.dart';

class CreatePipelineCubit extends Cubit<CreatePipelineState> {
  final ApiService api;
  final PipelinesCubit pipelinesCubit;

  CreatePipelineCubit({required this.api, required this.pipelinesCubit})
      : super(const CreatePipelineState()) {
    loadRepos();
  }

  Future<void> loadRepos() async {
    try {
      final data = await api.getRepos();
      final repos = (data['repos'] as List).map((r) => r['path'] as String).toList();
      final first = repos.isNotEmpty ? repos.first : '';
      if (!isClosed) {
        emit(state.copyWith(repos: repos, selectedRepo: first, loadingRepos: false));
      }
      if (first.isNotEmpty) loadIssues(first);
    } catch (_) {
      if (!isClosed) emit(state.copyWith(loadingRepos: false));
    }
  }

  Future<void> loadIssues(String repoPath) async {
    emit(state.copyWith(loadingIssues: true, issues: [], selectedIssueNumbers: {}, issuesPage: 1, hasMoreIssues: false));
    try {
      final data = await api.getIssues(repoPath, page: 1, perPage: 30);
      final issues = (data['issues'] as List).cast<Map<String, dynamic>>();
      final hasMore = data['has_more'] as bool? ?? false;
      if (!isClosed) emit(state.copyWith(issues: issues, loadingIssues: false, issuesPage: 1, hasMoreIssues: hasMore));
    } catch (_) {
      if (!isClosed) emit(state.copyWith(loadingIssues: false));
    }
  }

  Future<void> loadMoreIssues() async {
    if (state.loadingMoreIssues || !state.hasMoreIssues) return;
    final nextPage = state.issuesPage + 1;
    emit(state.copyWith(loadingMoreIssues: true));
    try {
      final data = await api.getIssues(state.selectedRepo, page: nextPage, perPage: 20);
      final newIssues = (data['issues'] as List).cast<Map<String, dynamic>>();
      final hasMore = data['has_more'] as bool? ?? false;
      if (!isClosed) {
        emit(state.copyWith(
          issues: [...state.issues, ...newIssues],
          loadingMoreIssues: false,
          issuesPage: nextPage,
          hasMoreIssues: hasMore,
        ));
      }
    } catch (_) {
      if (!isClosed) emit(state.copyWith(loadingMoreIssues: false));
    }
  }

  void selectRepo(String repo) {
    emit(state.copyWith(selectedRepo: repo));
    if (repo.isNotEmpty) loadIssues(repo);
  }

  void selectModel(String model) {
    emit(state.copyWith(selectedModel: model));
  }

  void toggleIssue(int number) {
    final updated = Set<int>.from(state.selectedIssueNumbers);
    if (updated.contains(number)) {
      updated.remove(number);
    } else {
      updated.add(number);
    }
    emit(state.copyWith(selectedIssueNumbers: updated));
  }

  Set<int> get activeIssueNumbers => pipelinesCubit.state.pipelines
      .where((p) => p.isActive && p.repoPath == state.selectedRepo && p.issueNumber != null)
      .map((p) => p.issueNumber!)
      .toSet();

  /// Creates one pipeline per selected issue. Returns true on success.
  Future<bool> submit() async {
    if (state.selectedRepo.isEmpty || state.selectedIssueNumbers.isEmpty) return false;

    emit(state.copyWith(submitting: true));
    try {
      for (final issueNumber in state.selectedIssueNumbers) {
        await pipelinesCubit.createPipeline(
          repoPath: state.selectedRepo,
          issueNumber: issueNumber,
          model: state.selectedModel,
        );
      }
      return true;
    } catch (_) {
      if (!isClosed) emit(state.copyWith(submitting: false));
      return false;
    }
  }
}
