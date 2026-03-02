import 'dart:async';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../models/session.dart';
import '../../services/api.dart';
import 'chat_state.dart';

class ChatCubit extends Cubit<ChatState> {
  final ApiService api;
  final String sessionKey;
  StreamSubscription<Map<String, dynamic>>? _eventSub;

  ChatCubit({required this.api, required this.sessionKey})
      : super(const ChatState()) {
    fetchSession();
    fetchHistory();
    _subscribeToEvents();
  }

  void _subscribeToEvents() {
    _eventSub = api.sessionEvents().listen(
      (event) {
        final evt = event['event'] as String?;
        String? liveStatus;

        if (evt == 'snapshot') {
          final sessions = event['sessions'] as Map<String, dynamic>? ?? {};
          final info = sessions[sessionKey] as Map<String, dynamic>?;
          liveStatus = info?['status'] as String?;
        } else if (evt == 'status' && event['session_key'] == sessionKey) {
          liveStatus = event['status'] as String?;
        }

        if (liveStatus == null || isClosed) return;

        // Merge live status into session map
        final updated = {...?state.session, 'status': liveStatus};
        final wasSending = state.sending;
        final nowIdle = liveStatus == 'idle';

        emit(state.copyWith(
          session: () => updated,
          sending: nowIdle && wasSending ? false : null,
        ));

        // If Claude just went idle while we thought it was sending, refresh history
        if (nowIdle && wasSending) fetchHistory();
      },
      onDone: () => Future.delayed(const Duration(seconds: 3), _subscribeToEvents),
      onError: (_) => Future.delayed(const Duration(seconds: 5), _subscribeToEvents),
    );
  }

  Future<void> fetchSession() async {
    try {
      final data = await api.getSession(sessionKey);
      if (!isClosed) emit(state.copyWith(session: () => data));
    } catch (_) {}
  }

  Future<void> fetchHistory() async {
    try {
      final data = await api.getHistory(sessionKey);
      final messages = (data['messages'] as List)
          .map((e) => Message.fromJson(e))
          .toList();
      if (!isClosed) emit(state.copyWith(messages: messages, status: ChatStatus.loaded));
    } catch (_) {
      if (!isClosed) emit(state.copyWith(status: ChatStatus.error));
    }
  }

  Future<void> sendMessage(String content) async {
    if (content.isEmpty || state.sending) return;

    final userMsg = Message(
      id: DateTime.now().millisecondsSinceEpoch,
      role: 'user',
      content: content,
      createdAt: DateTime.now(),
    );

    emit(state.copyWith(
      messages: [...state.messages, userMsg],
      sending: true,
    ));

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
      emit(state.copyWith(
        messages: [...state.messages, assistantMsg],
        sending: false,
      ));
      fetchSession();
    } catch (_) {
      if (!isClosed) emit(state.copyWith(sending: false));
      fetchHistory();
    }
  }

  Future<void> cancelSession() async {
    await api.cancelSession(sessionKey);
    fetchSession();
  }

  Future<void> deleteSession() async {
    await api.deleteSession(sessionKey);
  }

  @override
  Future<void> close() {
    _eventSub?.cancel();
    return super.close();
  }
}
