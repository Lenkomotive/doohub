import 'package:equatable/equatable.dart';
import '../../models/pipeline.dart';

enum PipelinesStatus { loading, loaded, error }

class PipelinesState extends Equatable {
  final List<Pipeline> pipelines;
  final int total;
  final String? filter;
  final PipelinesStatus status;

  const PipelinesState({
    this.pipelines = const [],
    this.total = 0,
    this.filter,
    this.status = PipelinesStatus.loading,
  });

  PipelinesState copyWith({
    List<Pipeline>? pipelines,
    int? total,
    String? Function()? filter,
    PipelinesStatus? status,
  }) {
    return PipelinesState(
      pipelines: pipelines ?? this.pipelines,
      total: total ?? this.total,
      filter: filter != null ? filter() : this.filter,
      status: status ?? this.status,
    );
  }

  @override
  List<Object?> get props => [pipelines, total, filter, status];
}
