import 'dart:async';
import 'package:flutter/material.dart';
import '../models/session.dart';
import '../services/api.dart';

class ChatScreen extends StatefulWidget {
  final ApiService api;
  final String sessionKey;

  const ChatScreen({super.key, required this.api, required this.sessionKey});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _inputController = TextEditingController();
  final _scrollController = ScrollController();
  List<Message> _messages = [];
  Map<String, dynamic>? _session;
  bool _sending = false;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchSession();
    _fetchHistory();
    _timer = Timer.periodic(const Duration(seconds: 3), (_) => _fetchSession());
  }

  @override
  void dispose() {
    _timer?.cancel();
    _inputController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _fetchSession() async {
    try {
      final data = await widget.api.getSession(widget.sessionKey);
      if (mounted) setState(() => _session = data);
    } catch (_) {}
  }

  Future<void> _fetchHistory() async {
    try {
      final data = await widget.api.getHistory(widget.sessionKey);
      if (!mounted) return;
      setState(() {
        _messages = (data['messages'] as List).map((e) => Message.fromJson(e)).toList();
      });
      _scrollToBottom();
    } catch (_) {}
  }

  Future<void> _sendMessage() async {
    final text = _inputController.text.trim();
    if (text.isEmpty || _sending) return;

    _inputController.clear();
    setState(() {
      _sending = true;
      _messages.add(Message(
        id: DateTime.now().millisecondsSinceEpoch,
        role: 'user',
        content: text,
        createdAt: DateTime.now(),
      ));
    });
    _scrollToBottom();

    try {
      final res = await widget.api.sendMessage(widget.sessionKey, text);
      if (mounted) {
        setState(() {
          _messages.add(Message(
            id: DateTime.now().millisecondsSinceEpoch + 1,
            role: 'assistant',
            content: res['content'] ?? '',
            createdAt: DateTime.now(),
          ));
          _sending = false;
        });
        _scrollToBottom();
        _fetchSession();
      }
    } catch (_) {
      if (mounted) {
        setState(() => _sending = false);
        _fetchHistory();
      }
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _cancelSession() async {
    await widget.api.cancelSession(widget.sessionKey);
    _fetchSession();
  }

  Future<void> _deleteSession() async {
    await widget.api.deleteSession(widget.sessionKey);
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final status = _session?['status'] ?? 'loading';

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
            if (_session != null)
              Text(
                '${_session!['model'] ?? ''} · ${(_session!['project_path'] ?? '').toString().split('/').last}',
                style: const TextStyle(fontSize: 11, color: Colors.grey),
              ),
          ],
        ),
        actions: [
          if (status == 'busy')
            IconButton(
              icon: const Icon(Icons.cancel_outlined, size: 20),
              onPressed: _cancelSession,
            ),
          IconButton(
            icon: Icon(Icons.delete_outline, size: 20, color: Theme.of(context).colorScheme.error),
            onPressed: _deleteSession,
          ),
        ],
      ),
      body: Column(
        children: [
          // Messages
          Expanded(
            child: _messages.isEmpty && !_sending
                ? const Center(child: Text('Send a message to start', style: TextStyle(color: Colors.grey)))
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(12),
                    itemCount: _messages.length + (_sending ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == _messages.length) {
                        // Typing indicator
                        return const Align(
                          alignment: Alignment.centerLeft,
                          child: Padding(
                            padding: EdgeInsets.only(top: 8),
                            child: _TypingBubble(),
                          ),
                        );
                      }
                      return _MessageBubble(message: _messages[index]);
                    },
                  ),
          ),

          // Input
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
                    enabled: !_sending,
                  ),
                ),
                const SizedBox(width: 8),
                SizedBox(
                  height: 40,
                  width: 40,
                  child: IconButton.filled(
                    onPressed: _sending ? null : _sendMessage,
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
