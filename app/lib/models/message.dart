import 'attachment.dart';

class Message {
  final int id;
  final String role;
  final String content;
  final DateTime createdAt;
  final List<Attachment> attachments;

  Message({
    required this.id,
    required this.role,
    required this.content,
    required this.createdAt,
    this.attachments = const [],
  });

  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      id: json['id'],
      role: json['role'],
      content: json['content'],
      createdAt: DateTime.parse(json['created_at']),
      attachments: (json['attachments'] as List?)
              ?.map((e) => Attachment.fromJson(e))
              .toList() ??
          const [],
    );
  }
}
