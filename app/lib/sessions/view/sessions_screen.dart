import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../models/session.dart';
import '../../services/api.dart';
import '../bloc/sessions_cubit.dart';
import '../bloc/sessions_state.dart';
import 'chat_screen.dart';

class SessionsScreen extends StatelessWidget {
  const SessionsScreen({super.key});

  void _openChat(BuildContext context, Session session) {
    final sessionsCubit = context.read<SessionsCubit>();

    // Fetch history if not loaded yet
    if (session.chatStatus == ChatStatus.initial) {
      sessionsCubit.fetchHistory(session.sessionKey);
    }

    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => BlocProvider.value(
        value: sessionsCubit,
        child: ChatScreen(sessionKey: session.sessionKey),
      ),
    ));
  }

  void _showCreateSheet(BuildContext context) {
    final sessionsCubit = context.read<SessionsCubit>();
    final api = context.read<ApiService>();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => _CreateSessionSheet(
        api: api,
        cubit: sessionsCubit,
        onCreated: (sessionKey) {
          sessionsCubit.fetchHistory(sessionKey);
          Navigator.of(context).push(MaterialPageRoute(
            builder: (_) => BlocProvider.value(
              value: sessionsCubit,
              child: ChatScreen(sessionKey: sessionKey),
            ),
          ));
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<SessionsCubit, SessionsState>(
      builder: (context, state) {
        final sessionsCubit = context.read<SessionsCubit>();

        return Stack(
          children: [
            Column(
              children: [
                // Header
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
                  child: Row(
                    children: [
                      Text('Sessions', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w500)),
                    ],
                  ),
                ),

                // List
                Expanded(
                  child: state.status == SessionsStatus.loading && state.sessions.isEmpty
                      ? const Center(child: CircularProgressIndicator())
                      : state.sessions.isEmpty
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
                              onRefresh: sessionsCubit.fetchSessions,
                              child: ListView.builder(
                                padding: const EdgeInsets.fromLTRB(20, 0, 20, 80),
                                itemCount: state.sessions.length,
                                itemBuilder: (context, index) {
                                  final session = state.sessions[index];
                                  return _SessionTile(
                                    session: session,
                                    onTap: () => _openChat(context, session),
                                    onDelete: () => sessionsCubit.deleteSession(session.sessionKey),
                                  );
                                },
                              ),
                            ),
                ),
              ],
            ),

            // FAB
            Positioned(
              bottom: 20,
              right: 20,
              child: FloatingActionButton(
                onPressed: () => _showCreateSheet(context),
                child: const Icon(Icons.add),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _CreateSessionSheet extends StatefulWidget {
  final ApiService api;
  final SessionsCubit cubit;
  final void Function(String sessionKey) onCreated;

  const _CreateSessionSheet({required this.api, required this.cubit, required this.onCreated});

  @override
  State<_CreateSessionSheet> createState() => _CreateSessionSheetState();
}

class _CreateSessionSheetState extends State<_CreateSessionSheet> {
  List<String> _repos = [];
  String _selectedProject = '';
  String _selectedModel = 'opus';
  bool _loading = false;
  bool _loadingRepos = true;

  String _nextName() {
    final existing = widget.cubit.state.sessions.map((s) => s.name).toSet();
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    for (final c in chars.split('')) {
      if (!existing.contains(c)) return c;
    }
    return chars[existing.length % chars.length];
  }

  @override
  void initState() {
    super.initState();
    _loadRepos();
  }

  Future<void> _loadRepos() async {
    try {
      final data = await widget.api.getRepos();
      final repos = (data['repos'] as List).map((r) => r['path'] as String).toList();
      setState(() { _repos = repos; _loadingRepos = false; });
    } catch (_) {
      setState(() => _loadingRepos = false);
    }
  }

  Future<void> _submit() async {
    setState(() => _loading = true);
    try {
      final key = await widget.cubit.createSession(name: _nextName(), projectPath: _selectedProject, model: _selectedModel);
      if (mounted) {
        Navigator.of(context).pop();
        widget.onCreated(key);
      }
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final projectItems = [
      const DropdownMenuItem<String>(value: '', child: Text('General')),
      ..._repos.map((r) => DropdownMenuItem(value: r, child: Text(r.split('/').last))),
    ];

    return Padding(
      padding: EdgeInsets.fromLTRB(20, 20, 20, MediaQuery.of(context).viewInsets.bottom + 20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('New Session', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            value: _selectedModel,
            decoration: const InputDecoration(labelText: 'Model', border: OutlineInputBorder()),
            items: const [
              DropdownMenuItem(value: 'sonnet', child: Text('Sonnet')),
              DropdownMenuItem(value: 'opus', child: Text('Opus')),
              DropdownMenuItem(value: 'haiku', child: Text('Haiku')),
            ],
            onChanged: (v) => setState(() => _selectedModel = v ?? 'sonnet'),
          ),
          const SizedBox(height: 12),
          if (_loadingRepos)
            const Center(child: CircularProgressIndicator())
          else
            DropdownButtonFormField<String>(
              value: _selectedProject,
              decoration: const InputDecoration(labelText: 'Project', border: OutlineInputBorder()),
              items: projectItems,
              onChanged: (v) => setState(() => _selectedProject = v ?? ''),
            ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _loading ? null : _submit,
            child: _loading
                ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Text('Create'),
          ),
        ],
      ),
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
            title: Text(session.name, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
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
            trailing: _StatusBadge(status: session.sending ? 'busy' : session.status),
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
      'busy' => Colors.red,
      'idle' => Colors.green,
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
