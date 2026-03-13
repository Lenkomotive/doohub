import 'attachment.dart';
import 'message.dart';

enum ChatStatus { initial, loading, loaded, error }

class Session {
  final String sessionKey;
  final String name;
  final String status;
  final String model;
  final String projectPath;
  final String? claudeSessionId;
  final String mode;
  final List<Message> messages;
  final bool sending;
  final ChatStatus chatStatus;
  final List<Attachment> pendingAttachments;

  Session({
    required this.sessionKey,
    required this.name,
    required this.status,
    required this.model,
    required this.projectPath,
    this.claudeSessionId,
    required this.mode,
    this.messages = const [],
    this.sending = false,
    this.chatStatus = ChatStatus.initial,
    this.pendingAttachments = const [],
  });

  factory Session.fromJson(Map<String, dynamic> json) {
    return Session(
      sessionKey: json['session_key'],
      name: json['name'] ?? json['session_key'],
      status: json['status'],
      model: json['model'] ?? '',
      projectPath: json['project_path'] ?? '',
      claudeSessionId: json['claude_session_id'],
      mode: json['mode'] ?? 'general',
    );
  }

  Session copyWith({
    String? status,
    List<Message>? messages,
    bool? sending,
    ChatStatus? chatStatus,
    List<Attachment>? pendingAttachments,
  }) {
    return Session(
      sessionKey: sessionKey,
      name: name,
      status: status ?? this.status,
      model: model,
      projectPath: projectPath,
      claudeSessionId: claudeSessionId,
      mode: mode,
      messages: messages ?? this.messages,
      sending: sending ?? this.sending,
      chatStatus: chatStatus ?? this.chatStatus,
      pendingAttachments: pendingAttachments ?? this.pendingAttachments,
    );
  }
}
