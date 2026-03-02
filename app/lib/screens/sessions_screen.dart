import 'dart:async';
import 'package:flutter/material.dart';
import '../models/session.dart';
import '../services/api.dart';
import 'chat_screen.dart';

class SessionsScreen extends StatefulWidget {
  final ApiService api;

  const SessionsScreen({super.key, required this.api});

  @override
  State<SessionsScreen> createState() => _SessionsScreenState();
}

class _SessionsScreenState extends State<SessionsScreen> {
  List<Session> _sessions = [];
  int _total = 0;
  String? _filter;
  bool _loading = true;
  Timer? _timer;

  final _filters = [
    (label: 'All', value: null),
    (label: 'Busy', value: 'busy'),
    (label: 'Idle', value: 'idle'),
  ];

  @override
  void initState() {
    super.initState();
    _fetch();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => _fetch());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetch() async {
    try {
      final data = await widget.api.getSessions(status: _filter);
      if (!mounted) return;
      setState(() {
        _sessions = (data['sessions'] as List).map((e) => Session.fromJson(e)).toList();
        _total = data['total'] ?? _sessions.length;
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _deleteSession(String key) async {
    setState(() {
      _sessions.removeWhere((s) => s.sessionKey == key);
      _total = _total - 1;
    });
    try {
      await widget.api.deleteSession(key);
    } catch (_) {
      _fetch();
    }
  }

  void _setFilter(String? value) {
    setState(() {
      _filter = value;
      _loading = true;
    });
    _fetch();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
          child: Row(
            children: [
              Text('Sessions', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w500)),
              const SizedBox(width: 8),
              Text('($_total)', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey)),
              const Spacer(),
              ...(_filters.map((f) => Padding(
                padding: const EdgeInsets.only(left: 2),
                child: ChoiceChip(
                  label: Text(f.label, style: const TextStyle(fontSize: 12)),
                  selected: _filter == f.value,
                  onSelected: (_) => _setFilter(f.value),
                  visualDensity: VisualDensity.compact,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ))),
            ],
          ),
        ),

        // List
        Expanded(
          child: _loading && _sessions.isEmpty
              ? const Center(child: CircularProgressIndicator())
              : _sessions.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.chat_outlined, size: 32, color: Colors.grey.shade600),
                          const SizedBox(height: 8),
                          Text('No sessions', style: TextStyle(color: Colors.grey.shade600)),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _fetch,
                      child: ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        itemCount: _sessions.length,
                        itemBuilder: (context, index) {
                          final session = _sessions[index];
                          return _SessionTile(
                            session: session,
                            onTap: () {
                              Navigator.of(context).push(MaterialPageRoute(
                                builder: (_) => ChatScreen(api: widget.api, sessionKey: session.sessionKey),
                              ));
                            },
                            onDelete: () => _deleteSession(session.sessionKey),
                          );
                        },
                      ),
                    ),
        ),
      ],
    );
  }
}

class _SessionTile extends StatelessWidget {
  final Session session;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  const _SessionTile({required this.session, required this.onTap, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Dismissible(
        key: ValueKey(session.sessionKey),
        direction: DismissDirection.endToStart,
        onDismissed: (_) => onDelete(),
        background: Container(
          alignment: Alignment.centerRight,
          padding: const EdgeInsets.only(right: 20),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.error,
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(Icons.delete_outline, color: Colors.white),
        ),
        child: Card(
          margin: EdgeInsets.zero,
          child: ListTile(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            onTap: onTap,
            title: Text(session.sessionKey, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 4),
                Row(
                  children: [
                    const Icon(Icons.memory, size: 12, color: Colors.grey),
                    const SizedBox(width: 4),
                    Text(session.model, style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  ],
                ),
                Row(
                  children: [
                    const Icon(Icons.folder_outlined, size: 12, color: Colors.grey),
                    const SizedBox(width: 4),
                    Text(
                      session.projectPath.split('/').last,
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ],
                ),
              ],
            ),
            trailing: _StatusBadge(status: session.status),
          ),
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final String status;

  const _StatusBadge({required this.status});

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'busy' => Colors.green,
      'idle' => Colors.grey,
      'failed' => Colors.red,
      _ => Colors.grey,
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        status,
        style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w500),
      ),
    );
  }
}
