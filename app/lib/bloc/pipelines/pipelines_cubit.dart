import 'dart:async';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../models/pipeline.dart';
import '../../services/api.dart';
import 'pipelines_state.dart';

class PipelinesCubit extends Cubit<PipelinesState> {
  final ApiService api;
  Timer? _timer;

  PipelinesCubit(this.api) : super(const PipelinesState()) {
    fetchPipelines();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => fetchPipelines());
  }

  Future<void> fetchPipelines() async {
    try {
      final data = await api.getPipelines(status: state.filter);
      final pipelines = (data['pipelines'] as List)
          .map((e) => Pipeline.fromJson(e))
          .toList();
      emit(state.copyWith(
        pipelines: pipelines,
        total: data['total'] ?? pipelines.length,
        status: PipelinesStatus.loaded,
      ));
    } catch (_) {
      if (state.status == PipelinesStatus.loading) {
        emit(state.copyWith(status: PipelinesStatus.error));
      }
    }
  }

  void setFilter(String? filter) {
    emit(state.copyWith(
      filter: () => filter,
      status: PipelinesStatus.loading,
    ));
    fetchPipelines();
  }

  @override
  Future<void> close() {
    _timer?.cancel();
    return super.close();
  }
}
