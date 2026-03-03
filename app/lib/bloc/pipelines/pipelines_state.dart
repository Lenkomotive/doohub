import 'package:equatable/equatable.dart';
import '../../models/pipeline.dart';

enum PipelinesStatus { loading, loaded, error }

class PipelinesState extends Equatable {
  final List<Pipeline> pipelines;
  final int total;
  final PipelinesStatus status;

  const PipelinesState({
    this.pipelines = const [],
    this.total = 0,
    this.status = PipelinesStatus.loading,
  });

  Pipeline? byKey(String key) {
    for (final p in pipelines) {
      if (p.pipelineKey == key) return p;
    }
    return null;
  }

  PipelinesState copyWith({
    List<Pipeline>? pipelines,
    int? total,
    PipelinesStatus? status,
  }) {
    return PipelinesState(
      pipelines: pipelines ?? this.pipelines,
      total: total ?? this.total,
      status: status ?? this.status,
    );
  }

  @override
  List<Object?> get props => [pipelines, total, status];
}
