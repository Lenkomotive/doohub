import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:image_picker/image_picker.dart';

import '../models/session.dart';
import '../models/message.dart';
import '../bloc/sessions/sessions_cubit.dart';
import '../bloc/sessions/sessions_state.dart';

class ChatScreen extends StatefulWidget {
  final String sessionKey;

  const ChatScreen({super.key, required this.sessionKey});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _inputController = TextEditingController();
  final _scrollController = ScrollController();
  final _imagePicker = ImagePicker();
  bool _showScrollToBottom = false;
  List<XFile> _pendingImages = [];

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

  void _showImageSourceSheet() {
    showModalBottomSheet(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt),
              title: const Text('Camera'),
              onTap: () {
                Navigator.pop(ctx);
                _pickImage(ImageSource.camera);
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Photo Library'),
              onTap: () {
                Navigator.pop(ctx);
                _pickMultipleImages();
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _pickImage(ImageSource source) async {
    final image = await _imagePicker.pickImage(source: source, maxWidth: 1024, imageQuality: 80);
    if (image != null) {
      setState(() => _pendingImages = [..._pendingImages, image]);
    }
  }

  Future<void> _pickMultipleImages() async {
    final images = await _imagePicker.pickMultiImage(maxWidth: 1024, imageQuality: 80, limit: 5);
    if (images.isNotEmpty) {
      final remaining = 5 - _pendingImages.length;
      final toAdd = images.take(remaining).toList();
      setState(() => _pendingImages = [..._pendingImages, ...toAdd]);
    }
  }

  void _removeImage(int index) {
    setState(() {
      _pendingImages = List.from(_pendingImages)..removeAt(index);
    });
  }

  Future<void> _sendMessage() async {
    final text = _inputController.text.trim();
    final hasImages = _pendingImages.isNotEmpty;
    if (text.isEmpty && !hasImages) return;

    List<String>? imageDataUris;
    if (hasImages) {
      imageDataUris = [];
      for (final file in _pendingImages) {
        final bytes = await file.readAsBytes();
        final ext = file.name.split('.').last.toLowerCase();
        final mime = ext == 'png' ? 'image/png' : 'image/jpeg';
        imageDataUris.add('data:$mime;base64,${base64Encode(bytes)}');
      }
    }

    _inputController.clear();
    setState(() => _pendingImages = []);

    if (!mounted) return;
    context.read<SessionsCubit>().sendMessage(
      widget.sessionKey,
      text,
      images: imageDataUris,
    );
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

              // Image preview strip
              if (_pendingImages.isNotEmpty)
                Container(
                  height: 80,
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  decoration: BoxDecoration(
                    border: Border(top: BorderSide(color: Colors.grey.shade800, width: 0.5)),
                  ),
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    itemCount: _pendingImages.length,
                    itemBuilder: (context, index) {
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: Stack(
                          children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: Image.file(
                                File(_pendingImages[index].path),
                                width: 68,
                                height: 68,
                                fit: BoxFit.cover,
                              ),
                            ),
                            Positioned(
                              top: 0,
                              right: 0,
                              child: GestureDetector(
                                onTap: () => _removeImage(index),
                                child: Container(
                                  decoration: const BoxDecoration(
                                    color: Colors.black54,
                                    shape: BoxShape.circle,
                                  ),
                                  padding: const EdgeInsets.all(2),
                                  child: const Icon(Icons.close, size: 14, color: Colors.white),
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    },
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
                        onPressed: session.sending ? null : _showImageSourceSheet,
                        icon: const Icon(Icons.add_photo_alternate_outlined, size: 22),
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

class _MessageBubble extends StatelessWidget {
  final Message message;

  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == 'user';
    final images = message.imageUrls;

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
            if (images != null && images.isNotEmpty)
              Padding(
                padding: EdgeInsets.only(bottom: message.content.isNotEmpty ? 8 : 0),
                child: Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: images.map((url) {
                    final bytes = _decodeDataUri(url);
                    if (bytes == null) return const SizedBox.shrink();
                    return GestureDetector(
                      onTap: () => _showFullImage(context, bytes),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.memory(
                          bytes,
                          width: images.length == 1 ? 220 : 120,
                          fit: BoxFit.cover,
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
            if (message.content.isNotEmpty)
              SelectableText(
                message.content,
                style: TextStyle(
                  fontSize: 14,
                  color: isUser ? Theme.of(context).colorScheme.onPrimary : Theme.of(context).colorScheme.onSurface,
                ),
              ),
          ],
        ),
      ),
    );
  }

  static Uint8List? _decodeDataUri(String uri) {
    final match = RegExp(r'^data:[^;]+;base64,(.+)$').firstMatch(uri);
    if (match == null) return null;
    try {
      return base64Decode(match.group(1)!);
    } catch (_) {
      return null;
    }
  }

  static void _showFullImage(BuildContext context, Uint8List bytes) {
    showDialog(
      context: context,
      builder: (_) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.all(16),
        child: InteractiveViewer(
          child: Image.memory(bytes),
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
