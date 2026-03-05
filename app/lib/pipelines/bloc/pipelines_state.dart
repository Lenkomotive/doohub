import 'package:equatable/equatable.dart';
import '../../models/pipeline.dart';

enum PipelinesStatus { loading, loaded, error }

class MergeStatus {
  final bool mergeable;
  final bool hasConflicts;
  final bool alreadyMerged;
  final bool closed;
  final String? error;

  const MergeStatus({
    required this.mergeable,
    required this.hasConflicts,
    this.alreadyMerged = false,
    this.closed = false,
    this.error,
  });

  factory MergeStatus.fromJson(Map<String, dynamic> json) {
    return MergeStatus(
      mergeable: json['mergeable'] ?? false,
      hasConflicts: json['has_conflicts'] ?? false,
      alreadyMerged: json['already_merged'] ?? false,
      closed: json['closed'] ?? false,
      error: json['error'],
    );
  }
}

class PipelinesState extends Equatable {
  final List<Pipeline> pipelines;
  final int total;
  final PipelinesStatus status;
  final Map<String, MergeStatus> mergeStatuses;
  final Set<String> mergingKeys;

  const PipelinesState({
    this.pipelines = const [],
    this.total = 0,
    this.status = PipelinesStatus.loading,
    this.mergeStatuses = const {},
    this.mergingKeys = const {},
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
    Map<String, MergeStatus>? mergeStatuses,
    Set<String>? mergingKeys,
  }) {
    return PipelinesState(
      pipelines: pipelines ?? this.pipelines,
      total: total ?? this.total,
      status: status ?? this.status,
      mergeStatuses: mergeStatuses ?? this.mergeStatuses,
      mergingKeys: mergingKeys ?? this.mergingKeys,
    );
  }

  @override
  List<Object?> get props => [pipelines, total, status, mergeStatuses, mergingKeys];
}
