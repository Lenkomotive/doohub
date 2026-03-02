import 'dart:async';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../models/session.dart';
import '../../services/api.dart';
import 'chat_state.dart';

class ChatCubit extends Cubit<ChatState> {
  final ApiService api;
  final String sessionKey;
  Timer? _timer;

  ChatCubit({required this.api, required this.sessionKey})
      : super(const ChatState()) {
    fetchSession();
    fetchHistory();
    _timer = Timer.periodic(const Duration(seconds: 3), (_) => fetchSession());
  }

  Future<void> fetchSession() async {
    try {
      final data = await api.getSession(sessionKey);
      emit(state.copyWith(session: () => data));
    } catch (_) {}
  }

  Future<void> fetchHistory() async {
    try {
      final data = await api.getHistory(sessionKey);
      final messages = (data['messages'] as List)
          .map((e) => Message.fromJson(e))
          .toList();
      emit(state.copyWith(
        messages: messages,
        status: ChatStatus.loaded,
      ));
    } catch (_) {
      emit(state.copyWith(status: ChatStatus.error));
    }
  }

  Future<void> sendMessage(String content) async {
    if (content.isEmpty || state.sending) return;

    final optimistic = Message(
      id: DateTime.now().millisecondsSinceEpoch,
      role: 'user',
      content: content,
      createdAt: DateTime.now(),
    );

    emit(state.copyWith(
      messages: [...state.messages, optimistic],
      sending: true,
    ));

    try {
      final res = await api.sendMessage(sessionKey, content);
      final reply = Message(
        id: DateTime.now().millisecondsSinceEpoch + 1,
        role: 'assistant',
        content: res['content'] ?? '',
        createdAt: DateTime.now(),
      );
      emit(state.copyWith(
        messages: [...state.messages, reply],
        sending: false,
      ));
      fetchSession();
    } catch (_) {
      emit(state.copyWith(sending: false));
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
    _timer?.cancel();
    return super.close();
  }
}
