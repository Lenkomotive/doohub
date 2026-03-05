import 'package:equatable/equatable.dart';

enum NotificationSettingsStatus { loading, loaded, error }

class NotificationSettingsState extends Equatable {
  final bool sessions;
  final bool pipelines;
  final NotificationSettingsStatus status;

  const NotificationSettingsState({
    this.sessions = true,
    this.pipelines = true,
    this.status = NotificationSettingsStatus.loading,
  });

  NotificationSettingsState copyWith({
    bool? sessions,
    bool? pipelines,
    NotificationSettingsStatus? status,
  }) {
    return NotificationSettingsState(
      sessions: sessions ?? this.sessions,
      pipelines: pipelines ?? this.pipelines,
      status: status ?? this.status,
    );
  }

  @override
  List<Object?> get props => [sessions, pipelines, status];
}
