import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../models/attachment.dart';
import '../../models/session.dart';
import '../../models/message.dart';
import '../bloc/sessions_cubit.dart';
import '../bloc/sessions_state.dart';

class ChatScreen extends StatefulWidget {
  final String sessionKey;

  const ChatScreen({super.key, required this.sessionKey});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _inputController = TextEditingController();
  final _scrollController = ScrollController();
  bool _showScrollToBottom = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(() {
      final scrolledUp = _scrollController.offset > 200;
      if (scrolledUp != _showScrollToBottom) {
        setState(() => _showScrollToBottom = scrolledUp);
      }
    });
  }

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _sendMessage() {
    final text = _inputController.text.trim();
    final session = context.read<SessionsCubit>().state.sessionByKey(widget.sessionKey);
    final hasPending = session?.pendingAttachments.isNotEmpty ?? false;
    if (text.isEmpty && !hasPending) return;
    _inputController.clear();
    context.read<SessionsCubit>().sendMessage(widget.sessionKey, text);
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.any,
    );
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;
    if (file.path == null) return;

    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('File too large. Maximum size is 10MB.')),
        );
      }
      return;
    }

    final mimeType = switch (file.extension?.toLowerCase()) {
      'pdf' => 'application/pdf',
      'txt' => 'text/plain',
      'md' => 'text/markdown',
      _ => 'application/octet-stream',
    };

    final attachment = Attachment(
      filename: file.name,
      mimeType: mimeType,
      fileSize: file.size,
      localPath: file.path,
    );

    if (mounted) {
      context.read<SessionsCubit>().addPendingAttachment(widget.sessionKey, attachment);
    }
  }

  @override
  Widget build(BuildContext context) {
    return BlocSelector<SessionsCubit, SessionsState, Session?>(
      selector: (state) => state.sessionByKey(widget.sessionKey),
      builder: (context, session) {
        if (session == null) {
          return const Scaffold(body: Center(child: Text('Session not found')));
        }

        final cubit = context.read<SessionsCubit>();
        final status = session.sending ? 'busy' : session.status;
        final messages = session.messages;
        final pendingAttachments = session.pendingAttachments;

        return Scaffold(
          appBar: AppBar(
            titleSpacing: 0,
            title: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(session.name, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                      decoration: BoxDecoration(
                        color: (status == 'busy' ? Colors.red : Colors.green).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        status,
                        style: TextStyle(
                          fontSize: 10,
                          color: status == 'busy' ? Colors.red : Colors.green,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
                Text(
                  '${session.model} · ${session.projectPath.split('/').last}',
                  style: const TextStyle(fontSize: 11, color: Colors.grey),
                ),
              ],
            ),
            actions: [
              if (status == 'busy')
                IconButton(
                  icon: const Icon(Icons.cancel_outlined, size: 20),
                  onPressed: () => cubit.cancelSession(widget.sessionKey),
                ),
              IconButton(
                icon: Icon(Icons.delete_outline, size: 20, color: Theme.of(context).colorScheme.error),
                onPressed: () async {
                  await cubit.deleteSession(widget.sessionKey);
                  if (context.mounted) Navigator.of(context).pop();
                },
              ),
            ],
          ),
          body: Column(
            children: [
              Expanded(
                child: messages.isEmpty && !session.sending
                    ? const Center(child: Text('Send a message to start', style: TextStyle(color: Colors.grey)))
                    : Stack(
                        children: [
                          ListView.builder(
                            controller: _scrollController,
                            reverse: true,
                            padding: const EdgeInsets.all(12),
                            itemCount: messages.length + (session.sending ? 1 : 0),
                            itemBuilder: (context, index) {
                              if (session.sending && index == 0) {
                                return const Align(
                                  alignment: Alignment.centerLeft,
                                  child: Padding(
                                    padding: EdgeInsets.only(top: 8),
                                    child: _TypingBubble(),
                                  ),
                                );
                              }
                              final msgIndex = session.sending ? index - 1 : index;
                              return _MessageBubble(message: messages[messages.length - 1 - msgIndex]);
                            },
                          ),
                          if (_showScrollToBottom)
                            Positioned(
                              right: 12,
                              bottom: 12,
                              child: FloatingActionButton.small(
                                onPressed: () => _scrollController.animateTo(
                                  0,
                                  duration: const Duration(milliseconds: 300),
                                  curve: Curves.easeOut,
                                ),
                                child: const Icon(Icons.keyboard_arrow_down),
                              ),
                            ),
                        ],
                      ),
              ),

              // Pending attachments chips
              if (pendingAttachments.isNotEmpty)
                Container(
                  padding: const EdgeInsets.fromLTRB(12, 4, 12, 0),
                  alignment: Alignment.centerLeft,
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: [
                      for (var i = 0; i < pendingAttachments.length; i++)
                        _PendingAttachmentChip(
                          attachment: pendingAttachments[i],
                          onRemove: () => cubit.removePendingAttachment(widget.sessionKey, i),
                        ),
                    ],
                  ),
                ),

              Container(
                padding: EdgeInsets.fromLTRB(12, 8, 12, MediaQuery.of(context).padding.bottom + 8),
                decoration: BoxDecoration(
                  border: Border(top: BorderSide(color: Colors.grey.shade800, width: 0.5)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    SizedBox(
                      height: 40,
                      width: 40,
                      child: IconButton(
                        onPressed: session.sending ? null : _pickFile,
                        icon: const Icon(Icons.attach_file, size: 20),
                        padding: EdgeInsets.zero,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: TextField(
                        controller: _inputController,
                        maxLines: 4,
                        minLines: 1,
                        textInputAction: TextInputAction.send,
                        onSubmitted: (_) => _sendMessage(),
                        decoration: InputDecoration(
                          hintText: 'Send a message...',
                          hintStyle: TextStyle(color: Colors.grey.shade600),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(20),
                            borderSide: BorderSide(color: Colors.grey.shade700),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(20),
                            borderSide: BorderSide(color: Colors.grey.shade700),
                          ),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                          isDense: true,
                        ),
                        enabled: !session.sending,
                      ),
                    ),
                    const SizedBox(width: 8),
                    SizedBox(
                      height: 40,
                      width: 40,
                      child: IconButton.filled(
                        onPressed: session.sending ? null : _sendMessage,
                        icon: const Icon(Icons.send, size: 18),
                        padding: EdgeInsets.zero,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _PendingAttachmentChip extends StatelessWidget {
  final Attachment attachment;
  final VoidCallback onRemove;

  const _PendingAttachmentChip({required this.attachment, required this.onRemove});

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: Icon(_iconForExtension(attachment.extension), size: 16),
      label: Text(
        '${_truncate(attachment.filename, 20)} (${attachment.fileSizeFormatted})',
        style: const TextStyle(fontSize: 12),
      ),
      deleteIcon: const Icon(Icons.close, size: 16),
      onDeleted: onRemove,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
      visualDensity: VisualDensity.compact,
    );
  }
}

class _AttachmentCard extends StatelessWidget {
  final Attachment attachment;
  final bool isUser;

  const _AttachmentCard({required this.attachment, required this.isUser});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        final url = attachment.url;
        if (url != null) {
          launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
        }
      },
      child: Container(
        margin: const EdgeInsets.only(top: 6),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: (isUser
                  ? Theme.of(context).colorScheme.onPrimary
                  : Theme.of(context).colorScheme.onSurface)
              .withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _iconForExtension(attachment.extension),
              size: 18,
              color: isUser
                  ? Theme.of(context).colorScheme.onPrimary
                  : Theme.of(context).colorScheme.onSurface,
            ),
            const SizedBox(width: 8),
            Flexible(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    attachment.filename,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: isUser
                          ? Theme.of(context).colorScheme.onPrimary
                          : Theme.of(context).colorScheme.onSurface,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    attachment.fileSizeFormatted,
                    style: TextStyle(
                      fontSize: 10,
                      color: (isUser
                              ? Theme.of(context).colorScheme.onPrimary
                              : Theme.of(context).colorScheme.onSurface)
                          .withValues(alpha: 0.7),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

IconData _iconForExtension(String ext) {
  return switch (ext) {
    'pdf' => Icons.picture_as_pdf,
    'txt' => Icons.description,
    'md' => Icons.article,
    _ => Icons.insert_drive_file,
  };
}

String _truncate(String text, int maxLen) {
  if (text.length <= maxLen) return text;
  return '${text.substring(0, maxLen)}...';
}

class _MessageBubble extends StatelessWidget {
  final Message message;

  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == 'user';

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.85),
        decoration: BoxDecoration(
          color: isUser
              ? Theme.of(context).colorScheme.primary
              : Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (message.content.isNotEmpty)
              SelectableText(
                message.content,
                style: TextStyle(
                  fontSize: 14,
                  color: isUser ? Theme.of(context).colorScheme.onPrimary : Theme.of(context).colorScheme.onSurface,
                ),
              ),
            for (final att in message.attachments)
              _AttachmentCard(attachment: att, isUser: isUser),
          ],
        ),
      ),
    );
  }
}

class _TypingBubble extends StatefulWidget {
  const _TypingBubble();

  @override
  State<_TypingBubble> createState() => _TypingBubbleState();
}

class _TypingBubbleState extends State<_TypingBubble> with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
      ),
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, _) {
          return Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(3, (i) {
              final delay = i * 0.2;
              final t = (_controller.value - delay) % 1.0;
              final opacity = (t < 0.5) ? 0.3 + 0.7 * (t / 0.5) : 0.3 + 0.7 * ((1.0 - t) / 0.5);
              return Padding(
                padding: EdgeInsets.only(left: i == 0 ? 0 : 4),
                child: Opacity(
                  opacity: opacity.clamp(0.3, 1.0),
                  child: Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              );
            }),
          );
        },
      ),
    );
  }
}
