class Message {
  final int id;
  final String role;
  final String content;
  final List<String>? imageUrls;
  final DateTime createdAt;

  Message({
    required this.id,
    required this.role,
    required this.content,
    this.imageUrls,
    required this.createdAt,
  });

  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      id: json['id'],
      role: json['role'],
      content: json['content'],
      imageUrls: (json['image_urls'] as List?)?.cast<String>(),
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
