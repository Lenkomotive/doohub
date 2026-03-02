import 'dart:async';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../models/session.dart';
import '../../services/api.dart';
import 'chat_state.dart';

class ChatCubit extends Cubit<ChatState> {
  final ApiService api;
  final String sessionKey;
  StreamSubscription<Map<String, dynamic>>? _streamSub;

  ChatCubit({required this.api, required this.sessionKey})
      : super(const ChatState()) {
    fetchSession();
    fetchHistory();
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
      streamingContent: '',
    ));

    // Add a placeholder assistant bubble that will fill with tokens
    final streamingMsg = Message(
      id: DateTime.now().millisecondsSinceEpoch + 1,
      role: 'assistant',
      content: '',
      createdAt: DateTime.now(),
    );
    emit(state.copyWith(
      messages: [...state.messages, streamingMsg],
    ));

    _streamSub?.cancel();
    _streamSub = api.streamMessage(sessionKey, content).listen(
      (event) {
        final evt = event['event'] as String?;
        if (evt == 'token') {
          final token = event['token'] as String? ?? '';
          final current = state.streamingContent + token;
          final msgs = List<Message>.from(state.messages);
          msgs[msgs.length - 1] = Message(
            id: streamingMsg.id,
            role: 'assistant',
            content: current,
            createdAt: streamingMsg.createdAt,
          );
          emit(state.copyWith(messages: msgs, streamingContent: current));
        } else if (evt == 'done') {
          final result = event['result'] as String? ?? state.streamingContent;
          final msgs = List<Message>.from(state.messages);
          msgs[msgs.length - 1] = Message(
            id: streamingMsg.id,
            role: 'assistant',
            content: result,
            createdAt: streamingMsg.createdAt,
          );
          emit(state.copyWith(
            messages: msgs,
            sending: false,
            streamingContent: '',
          ));
          fetchSession();
        } else if (evt == 'error') {
          emit(state.copyWith(sending: false, streamingContent: ''));
          fetchHistory();
        }
      },
      onError: (_) {
        emit(state.copyWith(sending: false, streamingContent: ''));
        fetchHistory();
      },
    );
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
    _streamSub?.cancel();
    return super.close();
  }
}
