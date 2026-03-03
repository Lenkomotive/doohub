import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
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
    if (text.isEmpty) return;
    _inputController.clear();
    context.read<SessionsCubit>().sendMessage(widget.sessionKey, text);
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

              Container(
                padding: EdgeInsets.fromLTRB(12, 8, 12, MediaQuery.of(context).padding.bottom + 8),
                decoration: BoxDecoration(
                  border: Border(top: BorderSide(color: Colors.grey.shade800, width: 0.5)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
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
        child: SelectableText(
          message.content,
          style: TextStyle(
            fontSize: 14,
            color: isUser ? Theme.of(context).colorScheme.onPrimary : Theme.of(context).colorScheme.onSurface,
          ),
        ),
      ),
    );
  }
}

class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
      ),
      child: const SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(strokeWidth: 2),
      ),
    );
  }
}
