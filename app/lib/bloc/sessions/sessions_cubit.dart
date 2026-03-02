import 'dart:async';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../models/session.dart';
import '../../services/api.dart';
import 'sessions_state.dart';

class SessionsCubit extends Cubit<SessionsState> {
  final ApiService api;
  StreamSubscription<Map<String, dynamic>>? _eventSub;

  SessionsCubit(this.api) : super(const SessionsState()) {
    fetchSessions(); // immediate REST load so list shows fast
    _subscribeToEvents(); // SSE for real-time updates on top
  }

  void _subscribeToEvents() {
    _eventSub = api.sessionEvents().listen(
      (event) {
        final evt = event['event'] as String?;

        if (evt == 'snapshot') {
          final raw = event['sessions'] as Map<String, dynamic>? ?? {};
          final sessions = raw.entries.map((e) {
            final info = e.value as Map<String, dynamic>;
            return Session(
              sessionKey: e.key,
              name: info['name'] as String? ?? e.key,
              status: info['status'] as String? ?? 'idle',
              model: info['model'] as String? ?? '',
              projectPath: info['project_path'] as String? ?? '',
              claudeSessionId: info['claude_session_id'] as String?,
              interactive: info['interactive'] as bool? ?? false,
            );
          }).toList();

          final filtered = state.filter == null
              ? sessions
              : sessions.where((s) => s.status == state.filter).toList();

          emit(state.copyWith(
            sessions: filtered,
            total: filtered.length,
            status: SessionsStatus.loaded,
          ));
        } else if (evt == 'status') {
          final key = event['session_key'] as String?;
          final newStatus = event['status'] as String?;
          if (key == null || newStatus == null) return;

          final updated = state.sessions.map((s) {
            if (s.sessionKey == key) {
              return Session(
                sessionKey: s.sessionKey,
                name: s.name,
                status: newStatus,
                model: s.model,
                projectPath: s.projectPath,
                claudeSessionId: s.claudeSessionId,
                interactive: s.interactive,
              );
            }
            return s;
          }).toList();

          final filtered = state.filter == null
              ? updated
              : updated.where((s) => s.status == state.filter).toList();

          emit(state.copyWith(sessions: filtered, total: filtered.length));
        }
      },
      onError: (_) {
        fetchSessions();
        Future.delayed(const Duration(seconds: 5), _subscribeToEvents);
      },
      onDone: () {
        // Reconnect when stream ends
        Future.delayed(const Duration(seconds: 3), _subscribeToEvents);
      },
    );
  }

  Future<void> fetchSessions() async {
    try {
      final data = await api.getSessions(status: state.filter);
      final sessions = (data['sessions'] as List)
          .map((e) => Session.fromJson(e))
          .toList();
      emit(state.copyWith(
        sessions: sessions,
        total: data['total'] ?? sessions.length,
        status: SessionsStatus.loaded,
      ));
    } catch (_) {
      if (state.status == SessionsStatus.loading) {
        emit(state.copyWith(status: SessionsStatus.error));
      }
    }
  }

  void setFilter(String? filter) {
    emit(state.copyWith(
      filter: () => filter,
      status: SessionsStatus.loading,
    ));
    fetchSessions();
  }

  Future<void> createSession({
    required String name,
    required String projectPath,
    String model = 'sonnet',
  }) async {
    await api.createSession(
      name: name,
      projectPath: projectPath,
      model: model,
    );
    await fetchSessions();
  }

  Future<void> deleteSession(String key) async {
    final updated = state.sessions.where((s) => s.sessionKey != key).toList();
    emit(state.copyWith(sessions: updated, total: state.total - 1));
    try {
      await api.deleteSession(key);
    } catch (_) {
      fetchSessions();
    }
  }

  @override
  Future<void> close() {
    _eventSub?.cancel();
    return super.close();
  }
}
