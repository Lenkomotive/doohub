class Attachment {
  final int? id;
  final String filename;
  final String mimeType;
  final int fileSize;
  final String? url;
  final String? localPath;

  Attachment({
    this.id,
    required this.filename,
    required this.mimeType,
    required this.fileSize,
    this.url,
    this.localPath,
  });

  factory Attachment.fromJson(Map<String, dynamic> json) {
    return Attachment(
      id: json['id'],
      filename: json['filename'] ?? '',
      mimeType: json['mime_type'] ?? '',
      fileSize: json['file_size'] ?? 0,
      url: json['url'],
    );
  }

  bool get isDocument {
    return mimeType.contains('pdf') ||
        mimeType.contains('text') ||
        filename.endsWith('.md');
  }

  String get fileSizeFormatted {
    if (fileSize < 1024) return '$fileSize B';
    if (fileSize < 1024 * 1024) return '${(fileSize / 1024).toStringAsFixed(1)} KB';
    return '${(fileSize / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  String get extension => filename.contains('.')
      ? filename.split('.').last.toLowerCase()
      : '';
}
