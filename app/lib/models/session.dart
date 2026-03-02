class Session {
  final String sessionKey;
  final String status;
  final String model;
  final String projectPath;
  final String? claudeSessionId;
  final bool interactive;

  Session({
    required this.sessionKey,
    required this.status,
    required this.model,
    required this.projectPath,
    this.claudeSessionId,
    required this.interactive,
  });

  factory Session.fromJson(Map<String, dynamic> json) {
    return Session(
      sessionKey: json['session_key'],
      status: json['status'],
      model: json['model'] ?? '',
      projectPath: json['project_path'] ?? '',
      claudeSessionId: json['claude_session_id'],
      interactive: json['interactive'] ?? false,
    );
  }
}

class Message {
  final int id;
  final String role;
  final String content;
  final DateTime createdAt;

  Message({
    required this.id,
    required this.role,
    required this.content,
    required this.createdAt,
  });

  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      id: json['id'],
      role: json['role'],
      content: json['content'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
