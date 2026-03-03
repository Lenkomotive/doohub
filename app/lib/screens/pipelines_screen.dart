import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../models/pipeline.dart';
import '../services/api.dart';
import '../bloc/pipelines/pipelines_cubit.dart';
import '../bloc/pipelines/pipelines_state.dart';
import 'pipeline_detail_screen.dart';

class PipelinesScreen extends StatelessWidget {
  const PipelinesScreen({super.key});

  void _openDetail(BuildContext context, Pipeline pipeline) {
    final cubit = context.read<PipelinesCubit>();
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => BlocProvider.value(
        value: cubit,
        child: PipelineDetailScreen(pipelineKey: pipeline.pipelineKey),
      ),
    ));
  }

  void _showCreateSheet(BuildContext context) {
    final cubit = context.read<PipelinesCubit>();
    final api = context.read<ApiService>();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => _CreatePipelineSheet(
        api: api,
        cubit: cubit,
        onCreated: (key) {
          // Navigate to detail after creation
          final pipeline = cubit.state.byKey(key);
          if (pipeline != null) {
            _openDetail(context, pipeline);
          }
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<PipelinesCubit, PipelinesState>(
      builder: (context, state) {
        final cubit = context.read<PipelinesCubit>();

        return Stack(
          children: [
            Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
                  child: Row(
                    children: [
                      Text('Pipelines', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w500)),
                    ],
                  ),
                ),
                Expanded(
                  child: state.status == PipelinesStatus.loading && state.pipelines.isEmpty
                      ? const Center(child: CircularProgressIndicator())
                      : state.pipelines.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.rocket_launch_outlined, size: 32, color: Colors.grey.shade600),
                                  const SizedBox(height: 8),
                                  Text('No pipelines', style: TextStyle(color: Colors.grey.shade600)),
                                ],
                              ),
                            )
                          : RefreshIndicator(
                              onRefresh: cubit.fetchPipelines,
                              child: ListView.builder(
                                padding: const EdgeInsets.fromLTRB(20, 0, 20, 80),
                                itemCount: state.pipelines.length,
                                itemBuilder: (context, index) {
                                  final pipeline = state.pipelines[index];
                                  return _PipelineTile(
                                    pipeline: pipeline,
                                    onTap: () => _openDetail(context, pipeline),
                                    onDelete: () => cubit.deletePipeline(pipeline.pipelineKey),
                                  );
                                },
                              ),
                            ),
                ),
              ],
            ),
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

class _PipelineTile extends StatelessWidget {
  final Pipeline pipeline;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  const _PipelineTile({required this.pipeline, required this.onTap, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Dismissible(
        key: ValueKey(pipeline.pipelineKey),
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
            title: Text(
              pipeline.displayTitle,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 4),
                Row(
                  children: [
                    const Icon(Icons.memory, size: 12, color: Colors.grey),
                    const SizedBox(width: 4),
                    Text(pipeline.model, style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  ],
                ),
                Row(
                  children: [
                    const Icon(Icons.folder_outlined, size: 12, color: Colors.grey),
                    const SizedBox(width: 4),
                    Text(
                      pipeline.repoPath.split('/').last,
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ],
                ),
              ],
            ),
            trailing: _StatusBadge(status: pipeline.status),
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
    final (color, label) = switch (status) {
      'planning' || 'planned' => (Colors.blue, status),
      'developing' || 'developed' => (Colors.orange, status),
      'reviewing' => (Colors.purple, status),
      'done' => (Colors.green, status),
      'failed' => (Colors.red, status),
      'cancelled' => (Colors.grey, status),
      _ => (Colors.grey, status),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w500),
      ),
    );
  }
}

class _CreatePipelineSheet extends StatefulWidget {
  final ApiService api;
  final PipelinesCubit cubit;
  final void Function(String pipelineKey) onCreated;

  const _CreatePipelineSheet({required this.api, required this.cubit, required this.onCreated});

  @override
  State<_CreatePipelineSheet> createState() => _CreatePipelineSheetState();
}

class _CreatePipelineSheetState extends State<_CreatePipelineSheet> {
  List<String> _repos = [];
  String _selectedRepo = '';
  String _selectedModel = 'claude-sonnet-4-6';
  final _issueController = TextEditingController();
  final _descController = TextEditingController();
  bool _loading = false;
  bool _loadingRepos = true;

  @override
  void initState() {
    super.initState();
    _loadRepos();
  }

  @override
  void dispose() {
    _issueController.dispose();
    _descController.dispose();
    super.dispose();
  }

  Future<void> _loadRepos() async {
    try {
      final data = await widget.api.getRepos();
      final repos = (data['repos'] as List).map((r) => r['path'] as String).toList();
      setState(() { _repos = repos; _selectedRepo = repos.isNotEmpty ? repos.first : ''; _loadingRepos = false; });
    } catch (_) {
      setState(() => _loadingRepos = false);
    }
  }

  Future<void> _submit() async {
    if (_selectedRepo.isEmpty) return;
    final issueNum = int.tryParse(_issueController.text.trim());
    final desc = _descController.text.trim();
    if (issueNum == null && desc.isEmpty) return;

    setState(() => _loading = true);
    try {
      final key = await widget.cubit.createPipeline(
        repoPath: _selectedRepo,
        issueNumber: issueNum,
        taskDescription: desc.isNotEmpty ? desc : null,
        model: _selectedModel,
      );
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
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 20, 20, MediaQuery.of(context).viewInsets.bottom + 20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('New Pipeline', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          if (_loadingRepos)
            const Center(child: CircularProgressIndicator())
          else
            DropdownButtonFormField<String>(
              initialValue: _selectedRepo.isNotEmpty ? _selectedRepo : null,
              decoration: const InputDecoration(labelText: 'Repository', border: OutlineInputBorder()),
              items: _repos.map((r) => DropdownMenuItem(value: r, child: Text(r.split('/').last))).toList(),
              onChanged: (v) => setState(() => _selectedRepo = v ?? ''),
            ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _selectedModel,
            decoration: const InputDecoration(labelText: 'Model', border: OutlineInputBorder()),
            items: const [
              DropdownMenuItem(value: 'claude-sonnet-4-6', child: Text('Sonnet')),
              DropdownMenuItem(value: 'claude-opus-4-6', child: Text('Opus')),
              DropdownMenuItem(value: 'claude-haiku-4-5-20251001', child: Text('Haiku')),
            ],
            onChanged: (v) => setState(() => _selectedModel = v ?? 'claude-sonnet-4-6'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _issueController,
            decoration: const InputDecoration(
              labelText: 'Issue number (optional)',
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _descController,
            decoration: const InputDecoration(
              labelText: 'Task description',
              border: OutlineInputBorder(),
            ),
            maxLines: 3,
            minLines: 2,
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
