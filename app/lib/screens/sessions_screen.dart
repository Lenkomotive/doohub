import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../models/session.dart';
import '../services/api.dart';
import '../bloc/sessions/sessions_cubit.dart';
import '../bloc/sessions/sessions_state.dart';
import '../bloc/chat/chat_cubit.dart';
import 'chat_screen.dart';

class SessionsScreen extends StatelessWidget {
  const SessionsScreen({super.key});

  static const _filters = [
    (label: 'All', value: null),
    (label: 'Busy', value: 'busy'),
    (label: 'Idle', value: 'idle'),
  ];

  void _showCreateSheet(BuildContext context) {
    final cubit = context.read<SessionsCubit>();
    final api = context.read<ApiService>();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => _CreateSessionSheet(api: api, cubit: cubit),
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<SessionsCubit, SessionsState>(
      builder: (context, state) {
        final cubit = context.read<SessionsCubit>();

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
                      const SizedBox(width: 8),
                      Text('(${state.total})', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey)),
                      const Spacer(),
                      ...(_filters.map((f) => Padding(
                        padding: const EdgeInsets.only(left: 2),
                        child: ChoiceChip(
                          label: Text(f.label, style: const TextStyle(fontSize: 12)),
                          selected: state.filter == f.value,
                          onSelected: (_) => cubit.setFilter(f.value),
                          visualDensity: VisualDensity.compact,
                          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                      ))),
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
                              onRefresh: cubit.fetchSessions,
                              child: ListView.builder(
                                padding: const EdgeInsets.fromLTRB(20, 0, 20, 80),
                                itemCount: state.sessions.length,
                                itemBuilder: (context, index) {
                                  final session = state.sessions[index];
                                  return _SessionTile(
                                    session: session,
                                    onTap: () {
                                      final api = context.read<ApiService>();
                                      Navigator.of(context).push(MaterialPageRoute(
                                        builder: (_) => BlocProvider(
                                          create: (_) => ChatCubit(api: api, sessionKey: session.sessionKey),
                                          child: ChatScreen(sessionKey: session.sessionKey),
                                        ),
                                      ));
                                    },
                                    onDelete: () => cubit.deleteSession(session.sessionKey),
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

  const _CreateSessionSheet({required this.api, required this.cubit});

  @override
  State<_CreateSessionSheet> createState() => _CreateSessionSheetState();
}

class _CreateSessionSheetState extends State<_CreateSessionSheet> {
  final _keyController = TextEditingController();
  final _pathController = TextEditingController();
  List<String> _repos = [];
  String? _selectedRepo;
  bool _loading = false;
  bool _loadingRepos = true;

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
    final key = _keyController.text.trim();
    final path = _selectedRepo ?? _pathController.text.trim();
    if (key.isEmpty || path.isEmpty) return;

    setState(() => _loading = true);
    try {
      await widget.cubit.createSession(sessionKey: key, projectPath: path);
      if (mounted) Navigator.of(context).pop();
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 20, 20, MediaQuery.of(context).viewInsets.bottom + 20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('New Session', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          TextField(
            controller: _keyController,
            decoration: const InputDecoration(labelText: 'Session name', border: OutlineInputBorder()),
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 12),
          if (_loadingRepos)
            const Center(child: CircularProgressIndicator())
          else if (_repos.isNotEmpty)
            DropdownButtonFormField<String>(
              initialValue: _selectedRepo,
              decoration: const InputDecoration(labelText: 'Project', border: OutlineInputBorder()),
              items: _repos.map((r) => DropdownMenuItem(value: r, child: Text(r.split('/').last))).toList(),
              onChanged: (v) => setState(() => _selectedRepo = v),
            )
          else
            TextField(
              controller: _pathController,
              decoration: const InputDecoration(labelText: 'Project path', border: OutlineInputBorder()),
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
