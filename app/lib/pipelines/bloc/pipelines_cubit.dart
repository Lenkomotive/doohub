import 'dart:async';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../models/pipeline.dart';
import '../../services/api.dart';
import 'pipelines_state.dart';

class PipelinesCubit extends Cubit<PipelinesState> {
  final ApiService api;
  StreamSubscription<Map<String, dynamic>>? _eventSub;

  PipelinesCubit(this.api) : super(const PipelinesState()) {
    fetchPipelines();
    _subscribeToEvents();
  }

  // ── SSE ──

  void _subscribeToEvents() {
    _eventSub = api.pipelineEvents().listen(
      (event) {
        if (isClosed) return;
        final key = event['pipeline_key'] as String?;
        final newStatus = event['status'] as String?;
        if (key == null || newStatus == null) return;

        final existing = state.byKey(key);
        if (existing != null) {
          final updated = state.pipelines.map((p) {
            if (p.pipelineKey == key) {
              return p.copyWith(
                status: newStatus,
                prUrl: event['pr_url'] as String?,
                error: event['error'] as String?,
              );
            }
            return p;
          }).toList();
          emit(state.copyWith(pipelines: updated));
        } else {
          // New pipeline we don't know about yet — refetch
          fetchPipelines();
        }
      },
      onError: (_) {
        fetchPipelines();
        Future.delayed(const Duration(seconds: 5), _subscribeToEvents);
      },
      onDone: () {
        Future.delayed(const Duration(seconds: 3), _subscribeToEvents);
      },
    );
  }

  // ── CRUD ──

  Future<void> fetchPipelines() async {
    try {
      final data = await api.getPipelines();
      final pipelines = (data['pipelines'] as List)
          .map((e) => Pipeline.fromJson(e))
          .toList();
      if (!isClosed) {
        emit(state.copyWith(
          pipelines: pipelines,
          total: data['total'] ?? pipelines.length,
          status: PipelinesStatus.loaded,
        ));
      }
    } catch (_) {
      if (!isClosed && state.status == PipelinesStatus.loading) {
        emit(state.copyWith(status: PipelinesStatus.error));
      }
    }
  }

  Future<String> createPipeline({
    required String repoPath,
    int? issueNumber,
    String? taskDescription,
    String model = 'claude-opus-4-6',
  }) async {
    final data = await api.createPipeline(
      repoPath: repoPath,
      issueNumber: issueNumber,
      taskDescription: taskDescription,
      model: model,
    );
    await fetchPipelines();
    return data['pipeline_key'] as String;
  }

  Future<void> cancelPipeline(String key) async {
    await api.cancelPipeline(key);
    final updated = state.pipelines.map((p) {
      if (p.pipelineKey == key) return p.copyWith(status: 'cancelled');
      return p;
    }).toList();
    if (!isClosed) emit(state.copyWith(pipelines: updated));
  }

  Future<void> deletePipeline(String key) async {
    final updated = state.pipelines.where((p) => p.pipelineKey != key).toList();
    emit(state.copyWith(pipelines: updated, total: state.total - 1));
    try {
      await api.deletePipeline(key);
    } catch (_) {
      fetchPipelines();
    }
  }

  @override
  Future<void> close() {
    _eventSub?.cancel();
    return super.close();
  }
}
