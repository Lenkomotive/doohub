import 'dart:async';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../models/session.dart';
import '../../models/message.dart';
import '../../services/api.dart';
import 'sessions_state.dart';

class SessionsCubit extends Cubit<SessionsState> {
  final ApiService api;
  StreamSubscription<Map<String, dynamic>>? _eventSub;

  SessionsCubit(this.api) : super(const SessionsState()) {
    fetchSessions();
    _subscribeToEvents();
  }

  // ── SSE ──

  void _subscribeToEvents() {
    _eventSub = api.sessionEvents().listen(
      (event) {
        if (isClosed) return;
        final evt = event['event'] as String?;

        if (evt == 'snapshot') {
          final raw = event['sessions'] as Map<String, dynamic>? ?? {};
          final sessions = raw.entries.map((e) {
            final info = e.value as Map<String, dynamic>;
            final existing = state.sessionByKey(e.key);
            return Session(
              sessionKey: e.key,
              name: info['name'] as String? ?? e.key,
              status: info['status'] as String? ?? 'idle',
              model: info['model'] as String? ?? '',
              projectPath: info['project_path'] as String? ?? '',
              claudeSessionId: info['claude_session_id'] as String?,
              interactive: info['interactive'] as bool? ?? false,
              messages: existing?.messages ?? const [],
              sending: existing?.sending ?? false,
              chatStatus: existing?.chatStatus ?? ChatStatus.initial,
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
              final wasSending = s.sending;
              final nowIdle = newStatus == 'idle';
              return s.copyWith(
                status: newStatus,
                sending: nowIdle && wasSending ? false : null,
              );
            }
            return s;
          }).toList();

          final filtered = state.filter == null
              ? updated
              : updated.where((s) => s.status == state.filter).toList();

          emit(state.copyWith(sessions: filtered, total: filtered.length));

          // If session just went idle while sending, refresh its history
          final session = state.sessionByKey(key);
          if (session != null && session.sending && newStatus == 'idle') {
            fetchHistory(key);
          }
        }
      },
      onError: (_) {
        fetchSessions();
        Future.delayed(const Duration(seconds: 5), _subscribeToEvents);
      },
      onDone: () {
        Future.delayed(const Duration(seconds: 3), _subscribeToEvents);
      },
    );
  }

  // ── Sessions CRUD ──

  Future<void> fetchSessions() async {
    try {
      final data = await api.getSessions(status: state.filter);
      final sessions = (data['sessions'] as List).map((e) {
        final s = Session.fromJson(e);
        final existing = state.sessionByKey(s.sessionKey);
        return Session(
          sessionKey: s.sessionKey,
          name: s.name,
          status: s.status,
          model: s.model,
          projectPath: s.projectPath,
          claudeSessionId: s.claudeSessionId,
          interactive: s.interactive,
          messages: existing?.messages ?? const [],
          sending: existing?.sending ?? false,
          chatStatus: existing?.chatStatus ?? ChatStatus.initial,
        );
      }).toList();
      if (!isClosed) {
        emit(state.copyWith(
          sessions: sessions,
          total: data['total'] ?? sessions.length,
          status: SessionsStatus.loaded,
        ));
      }
    } catch (_) {
      if (!isClosed && state.status == SessionsStatus.loading) {
        emit(state.copyWith(status: SessionsStatus.error));
      }
    }
  }

  Future<String> createSession({
    required String name,
    required String projectPath,
    String model = 'sonnet',
  }) async {
    final data = await api.createSession(
      name: name,
      projectPath: projectPath,
      model: model,
    );
    await fetchSessions();
    return data['session_key'] as String;
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

  void setFilter(String? filter) {
    emit(state.copyWith(
      filter: () => filter,
      status: SessionsStatus.loading,
    ));
    fetchSessions();
  }

  // ── Per-session messages ──

  Future<void> fetchHistory(String sessionKey) async {
    try {
      final data = await api.getHistory(sessionKey);
      final messages = (data['messages'] as List)
          .map((e) => Message.fromJson(e))
          .toList();
      if (!isClosed) {
        _updateSession(sessionKey, (s) => s.copyWith(
          messages: messages,
          chatStatus: ChatStatus.loaded,
        ));
      }
    } catch (_) {
      if (!isClosed) {
        _updateSession(sessionKey, (s) => s.copyWith(
          chatStatus: ChatStatus.error,
        ));
      }
    }
  }

  void addMessage(String sessionKey, Message message) {
    _updateSession(sessionKey, (s) => s.copyWith(
      messages: [...s.messages, message],
    ));
  }

  void setSending(String sessionKey, bool sending) {
    _updateSession(sessionKey, (s) => s.copyWith(sending: sending));
  }

  Future<void> sendMessage(String sessionKey, String content) async {
    final session = state.sessionByKey(sessionKey);
    if (content.isEmpty || (session?.sending ?? false)) return;

    final userMsg = Message(
      id: DateTime.now().millisecondsSinceEpoch,
      role: 'user',
      content: content,
      createdAt: DateTime.now(),
    );

    addMessage(sessionKey, userMsg);
    setSending(sessionKey, true);

    try {
      final data = await api.sendMessage(sessionKey, content);
      if (isClosed) return;
      final responseText = data['content'] as String? ?? '';
      final assistantMsg = Message(
        id: DateTime.now().millisecondsSinceEpoch,
        role: 'assistant',
        content: responseText,
        createdAt: DateTime.now(),
      );
      addMessage(sessionKey, assistantMsg);
      setSending(sessionKey, false);
    } catch (_) {
      if (!isClosed) setSending(sessionKey, false);
      fetchHistory(sessionKey);
    }
  }

  Future<void> cancelSession(String key) async {
    await api.cancelSession(key);
  }

  // ── Helpers ──

  void _updateSession(String key, Session Function(Session) updater) {
    final updated = state.sessions.map((s) {
      if (s.sessionKey == key) return updater(s);
      return s;
    }).toList();
    emit(state.copyWith(sessions: updated));
  }

  @override
  Future<void> close() {
    _eventSub?.cancel();
    return super.close();
  }
}
