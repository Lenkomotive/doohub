import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../models/pipeline.dart';
import '../../services/api.dart';
import '../bloc/create_pipeline_cubit.dart';
import '../bloc/create_pipeline_state.dart';
import '../bloc/pipelines_cubit.dart';
import '../bloc/pipelines_state.dart';

class PipelinesScreen extends StatelessWidget {
  const PipelinesScreen({super.key});

  void _openDetail(BuildContext context, Pipeline pipeline) {
    context.push('/pipelines/${pipeline.pipelineKey}');
  }

  void _showCreateSheet(BuildContext context) {
    final pipelinesCubit = context.read<PipelinesCubit>();
    final api = context.read<ApiService>();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => BlocProvider(
        create: (_) => CreatePipelineCubit(api: api, pipelinesCubit: pipelinesCubit),
        child: const _CreatePipelineSheet(),
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
                                  Icon(Icons.device_hub_outlined, size: 32, color: Colors.grey.shade600),
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
                if (pipeline.templateName != null)
                  Row(
                    children: [
                      const Icon(Icons.dashboard_outlined, size: 12, color: Colors.grey),
                      const SizedBox(width: 4),
                      Text(pipeline.templateName!, style: const TextStyle(fontSize: 12, color: Colors.grey)),
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
                if (pipeline.templateName != null)
                  Row(
                    children: [
                      const Icon(Icons.description_outlined, size: 12, color: Colors.grey),
                      const SizedBox(width: 4),
                      Text(
                        pipeline.templateName!,
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
  const _CreatePipelineSheet();

  @override
  State<_CreatePipelineSheet> createState() => _CreatePipelineSheetState();
}

class _CreatePipelineSheetState extends State<_CreatePipelineSheet> {
  final _issueScrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _issueScrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _issueScrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_issueScrollController.position.pixels >=
        _issueScrollController.position.maxScrollExtent - 100) {
      context.read<CreatePipelineCubit>().loadMoreIssues();
    }
  }

  void _showIssueDetail(BuildContext context, Map<String, dynamic> issue) {
    final cubit = context.read<CreatePipelineCubit>();
    final number = issue['number'] as int;
    showDialog(
      context: context,
      builder: (ctx) => _IssueDetailDialog(
        api: cubit.api,
        repoPath: cubit.state.selectedRepo,
        issueNumber: number,
      ),
    );
  }

  Future<void> _submit(BuildContext context) async {
    final cubit = context.read<CreatePipelineCubit>();
    final success = await cubit.submit();
    if (success && context.mounted) {
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return BlocBuilder<CreatePipelineCubit, CreatePipelineState>(
      builder: (context, state) {
        final cubit = context.read<CreatePipelineCubit>();
        final activeIssueNumbers = cubit.activeIssueNumbers;

        return ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.75),
          child: Padding(
            padding: EdgeInsets.fromLTRB(20, 20, 20, MediaQuery.of(context).viewInsets.bottom + 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('New Pipeline', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600)),
                const SizedBox(height: 16),
                if (state.loadingRepos)
                  const Center(child: CircularProgressIndicator())
                else
                  DropdownButtonFormField<String>(
                    initialValue: state.selectedRepo.isNotEmpty ? state.selectedRepo : null,
                    decoration: const InputDecoration(labelText: 'Repository', border: OutlineInputBorder()),
                    items: state.repos.map((r) => DropdownMenuItem(value: r, child: Text(r.split('/').last))).toList(),
                    onChanged: (v) => cubit.selectRepo(v ?? ''),
                  ),
                const SizedBox(height: 12),
                if (state.templates.isNotEmpty) ...[
                  DropdownButtonFormField<int>(
                    value: state.selectedTemplateId,
                    decoration: const InputDecoration(labelText: 'Template', border: OutlineInputBorder()),
                    items: [
                      const DropdownMenuItem<int>(value: null, child: Text('None (use model)')),
                      ...state.templates.map((t) => DropdownMenuItem(value: t.id, child: Text(t.name))),
                    ],
                    onChanged: (v) => cubit.selectTemplate(v),
                  ),
                  const SizedBox(height: 12),
                ],
                if (!state.useTemplate)
                  DropdownButtonFormField<String>(
                    initialValue: state.selectedModel,
                    decoration: const InputDecoration(labelText: 'Model', border: OutlineInputBorder()),
                    items: const [
                      DropdownMenuItem(value: 'claude-sonnet-4-6', child: Text('Sonnet')),
                      DropdownMenuItem(value: 'claude-opus-4-6', child: Text('Opus')),
                      DropdownMenuItem(value: 'claude-haiku-4-5-20251001', child: Text('Haiku')),
                    ],
                    onChanged: (v) => cubit.selectModel(v ?? 'claude-opus-4-6'),
                  ),
                const SizedBox(height: 12),
                Text('Select issues', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey)),
                const SizedBox(height: 8),
                Flexible(
                  child: state.loadingIssues
                      ? const Center(child: Padding(padding: EdgeInsets.all(20), child: CircularProgressIndicator()))
                      : state.issues.isEmpty
                          ? Center(child: Padding(
                              padding: const EdgeInsets.all(20),
                              child: Text(
                                state.selectedRepo.isEmpty ? 'Select a repository' : 'No open issues',
                                style: TextStyle(color: Colors.grey.shade600),
                              ),
                            ))
                          : ListView.builder(
                              controller: _issueScrollController,
                              shrinkWrap: true,
                              itemCount: state.issues.length + (state.hasMoreIssues ? 1 : 0),
                              itemBuilder: (context, index) {
                                if (index >= state.issues.length) {
                                  return const Padding(
                                    padding: EdgeInsets.all(12),
                                    child: Center(child: SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))),
                                  );
                                }
                                final issue = state.issues[index];
                                final number = issue['number'] as int;
                                final title = issue['title'] as String? ?? '';
                                final labels = (issue['labels'] as List?)
                                    ?.map((l) => l is Map ? (l['name'] as String? ?? '') : '')
                                    .where((l) => l.isNotEmpty)
                                    .toList() ?? [];
                                final selected = state.selectedIssueNumbers.contains(number);
                                final running = activeIssueNumbers.contains(number);

                                return Card(
                                  margin: const EdgeInsets.only(bottom: 4),
                                  color: running
                                      ? cs.surfaceContainerHighest.withValues(alpha: 0.5)
                                      : selected ? cs.primaryContainer : null,
                                  child: ListTile(
                                    dense: true,
                                    enabled: !running,
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                    leading: running
                                        ? Icon(Icons.hourglass_top, color: Colors.grey.shade400, size: 20)
                                        : selected
                                            ? Icon(Icons.check_box, color: cs.primary, size: 20)
                                            : Icon(Icons.check_box_outline_blank, color: Colors.grey.shade400, size: 20),
                                    title: Text(
                                      '#$number  $title',
                                      style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
                                        color: running ? Colors.grey : null,
                                      ),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    subtitle: labels.isNotEmpty
                                        ? Padding(
                                            padding: const EdgeInsets.only(top: 4),
                                            child: Wrap(
                                              spacing: 4,
                                              children: labels.map((l) => Container(
                                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                                                decoration: BoxDecoration(
                                                  color: cs.surfaceContainerHighest,
                                                  borderRadius: BorderRadius.circular(8),
                                                ),
                                                child: Text(l, style: const TextStyle(fontSize: 10)),
                                              )).toList(),
                                            ),
                                          )
                                        : null,
                                    onTap: running ? null : () => cubit.toggleIssue(number),
                                    onLongPress: () => _showIssueDetail(context, issue),
                                  ),
                                );
                              },
                            ),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: state.submitting || state.selectedIssueNumbers.isEmpty ? null : () => _submit(context),
                  child: state.submitting
                      ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : Text(state.selectedIssueNumbers.length <= 1
                          ? 'Create'
                          : 'Create ${state.selectedIssueNumbers.length} Pipelines'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _IssueDetailDialog extends StatefulWidget {
  final ApiService api;
  final String repoPath;
  final int issueNumber;

  const _IssueDetailDialog({required this.api, required this.repoPath, required this.issueNumber});

  @override
  State<_IssueDetailDialog> createState() => _IssueDetailDialogState();
}

class _IssueDetailDialogState extends State<_IssueDetailDialog> {
  Map<String, dynamic>? _issue;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await widget.api.getIssue(widget.repoPath, widget.issueNumber);
      if (mounted) setState(() { _issue = data; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: _loading
          ? const Text('Loading...')
          : Text('#${_issue?['number']}  ${_issue?['title'] ?? 'Issue'}', style: const TextStyle(fontSize: 16)),
      content: SizedBox(
        width: double.maxFinite,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : SingleChildScrollView(
                child: Text(
                  (_issue?['body'] as String?)?.isNotEmpty == true
                      ? _issue!['body'] as String
                      : 'No description.',
                  style: const TextStyle(fontSize: 13),
                ),
              ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Close')),
      ],
    );
  }
}
