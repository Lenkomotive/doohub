import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen_ai_chat_ui/flutter_gen_ai_chat_ui.dart';
import '../models/session.dart' as app;
import '../bloc/chat/chat_cubit.dart';
import '../bloc/chat/chat_state.dart';

class ChatScreen extends StatefulWidget {
  final String sessionKey;

  const ChatScreen({super.key, required this.sessionKey});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _chatController = ChatMessagesController();

  static const _currentUser = ChatUser(id: 'user', firstName: 'You');
  static const _aiUser = ChatUser(id: 'assistant', firstName: 'Claude');

  int _lastSyncedCount = 0;

  @override
  void dispose() {
    _chatController.dispose();
    super.dispose();
  }

  void _syncMessages(List<app.Message> messages) {
    if (messages.length == _lastSyncedCount) return;
    _chatController.clearMessages();
    for (final msg in messages.reversed) {
      _chatController.addMessage(ChatMessage(
        text: msg.content,
        user: msg.role == 'user' ? _currentUser : _aiUser,
        createdAt: msg.createdAt,
        isMarkdown: msg.role == 'assistant',
      ));
    }
    _lastSyncedCount = messages.length;
  }

  void _onSendMessage(ChatMessage message) {
    context.read<ChatCubit>().sendMessage(message.text);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return BlocConsumer<ChatCubit, ChatState>(
      listenWhen: (prev, curr) => prev.messages.length != curr.messages.length,
      listener: (context, state) => _syncMessages(state.messages),
      builder: (context, state) {
        final cubit = context.read<ChatCubit>();
        final status = state.session?['status'] ?? 'loading';

        // Sync on first build
        if (_lastSyncedCount == 0 && state.messages.isNotEmpty) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            _syncMessages(state.messages);
          });
        }

        return Scaffold(
          appBar: AppBar(
            titleSpacing: 0,
            title: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(widget.sessionKey, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                      decoration: BoxDecoration(
                        color: (status == 'busy' ? Colors.green : Colors.grey).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        status,
                        style: TextStyle(
                          fontSize: 10,
                          color: status == 'busy' ? Colors.green : Colors.grey,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
                if (state.session != null)
                  Text(
                    '${state.session!['model'] ?? ''} · ${(state.session!['project_path'] ?? '').toString().split('/').last}',
                    style: const TextStyle(fontSize: 11, color: Colors.grey),
                  ),
              ],
            ),
            actions: [
              if (status == 'busy')
                IconButton(
                  icon: const Icon(Icons.cancel_outlined, size: 20),
                  onPressed: cubit.cancelSession,
                ),
              IconButton(
                icon: Icon(Icons.delete_outline, size: 20, color: Theme.of(context).colorScheme.error),
                onPressed: () async {
                  await cubit.deleteSession();
                  if (context.mounted) Navigator.of(context).pop();
                },
              ),
            ],
          ),
          body: AiChatWidget(
            currentUser: _currentUser,
            aiUser: _aiUser,
            controller: _chatController,
            onSendMessage: _onSendMessage,
            enableMarkdownStreaming: true,
            loadingConfig: LoadingConfig(isLoading: state.sending),
            messageOptions: MessageOptions(
              showTime: true,
              showCopyButton: true,
              bubbleStyle: BubbleStyle(
                userBubbleColor: Theme.of(context).colorScheme.primary,
                aiBubbleColor: isDark ? const Color(0xFF1E1E2E) : const Color(0xFFF5F5FF),
                userBubbleTopLeftRadius: 16,
                userBubbleTopRightRadius: 16,
                aiBubbleTopLeftRadius: 16,
                aiBubbleTopRightRadius: 16,
                bottomLeftRadius: 16,
                bottomRightRadius: 16,
              ),
              userTextColor: Theme.of(context).colorScheme.onPrimary,
              aiTextColor: isDark ? Colors.white : Colors.black87,
            ),
            inputOptions: InputOptions(
              sendOnEnter: true,
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
            ),
          ),
        );
      },
    );
  }
}
