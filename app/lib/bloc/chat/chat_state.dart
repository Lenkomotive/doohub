import 'package:equatable/equatable.dart';
import '../../models/session.dart';

enum ChatStatus { loading, loaded, error }

class ChatState extends Equatable {
  final List<Message> messages;
  final Map<String, dynamic>? session;
  final bool sending;
  final ChatStatus status;
  final String streamingContent;

  const ChatState({
    this.messages = const [],
    this.session,
    this.sending = false,
    this.status = ChatStatus.loading,
    this.streamingContent = '',
  });

  ChatState copyWith({
    List<Message>? messages,
    Map<String, dynamic>? Function()? session,
    bool? sending,
    ChatStatus? status,
    String? streamingContent,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      session: session != null ? session() : this.session,
      sending: sending ?? this.sending,
      status: status ?? this.status,
      streamingContent: streamingContent ?? this.streamingContent,
    );
  }

  @override
  List<Object?> get props => [messages, session, sending, status, streamingContent];
}
