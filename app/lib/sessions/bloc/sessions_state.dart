import 'package:equatable/equatable.dart';
import '../../models/session.dart';

enum SessionsStatus { loading, loaded, error }

class SessionsState extends Equatable {
  final List<Session> sessions;
  final int total;
  final String? filter;
  final SessionsStatus status;

  const SessionsState({
    this.sessions = const [],
    this.total = 0,
    this.filter,
    this.status = SessionsStatus.loading,
  });

  Session? sessionByKey(String key) {
    for (final s in sessions) {
      if (s.sessionKey == key) return s;
    }
    return null;
  }

  SessionsState copyWith({
    List<Session>? sessions,
    int? total,
    String? Function()? filter,
    SessionsStatus? status,
  }) {
    return SessionsState(
      sessions: sessions ?? this.sessions,
      total: total ?? this.total,
      filter: filter != null ? filter() : this.filter,
      status: status ?? this.status,
    );
  }

  @override
  List<Object?> get props => [sessions, total, filter, status];
}
