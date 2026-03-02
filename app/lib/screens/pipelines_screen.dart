import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../models/pipeline.dart';
import '../bloc/pipelines/pipelines_cubit.dart';
import '../bloc/pipelines/pipelines_state.dart';

class PipelinesScreen extends StatelessWidget {
  const PipelinesScreen({super.key});

  static const _filters = [
    (label: 'All', value: null),
    (label: 'Active', value: 'active'),
    (label: 'Done', value: 'done'),
    (label: 'Failed', value: 'failed'),
  ];

  static String _timeAgo(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inSeconds < 60) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<PipelinesCubit, PipelinesState>(
      builder: (context, state) {
        final cubit = context.read<PipelinesCubit>();

        return Column(
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
              child: Row(
                children: [
                  Text('Pipelines', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w500)),
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
              child: state.status == PipelinesStatus.loading && state.pipelines.isEmpty
                  ? const Center(child: CircularProgressIndicator())
                  : state.pipelines.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.account_tree_outlined, size: 32, color: Colors.grey.shade600),
                              const SizedBox(height: 8),
                              Text('No pipelines', style: TextStyle(color: Colors.grey.shade600)),
                            ],
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: cubit.fetchPipelines,
                          child: ListView.builder(
                            padding: const EdgeInsets.symmetric(horizontal: 20),
                            itemCount: state.pipelines.length,
                            itemBuilder: (context, index) {
                              final p = state.pipelines[index];
                              return _PipelineTile(pipeline: p, timeAgo: _timeAgo);
                            },
                          ),
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
  final String Function(DateTime) timeAgo;

  const _PipelineTile({required this.pipeline, required this.timeAgo});

  @override
  Widget build(BuildContext context) {
    final statusColor = switch (pipeline.status) {
      'done' => Colors.green,
      'failed' => Colors.red,
      'planning' || 'developing' || 'reviewing' => Colors.blue,
      _ => Colors.grey,
    };

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    '#${pipeline.issueNumber} ${pipeline.issueTitle}',
                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    pipeline.status,
                    style: TextStyle(fontSize: 11, color: statusColor, fontWeight: FontWeight.w500),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.account_tree_outlined, size: 12, color: Colors.grey),
                const SizedBox(width: 4),
                Text(pipeline.repo, style: const TextStyle(fontSize: 12, color: Colors.grey)),
              ],
            ),
            if (pipeline.branch != null) ...[
              const SizedBox(height: 2),
              Row(
                children: [
                  const Icon(Icons.fork_right, size: 12, color: Colors.grey),
                  const SizedBox(width: 4),
                  Text(pipeline.branch!, style: const TextStyle(fontSize: 12, color: Colors.grey)),
                ],
              ),
            ],
            if (pipeline.prNumber != null) ...[
              const SizedBox(height: 2),
              Row(
                children: [
                  const Icon(Icons.merge, size: 12, color: Colors.grey),
                  const SizedBox(width: 4),
                  Text(
                    'PR #${pipeline.prNumber}${pipeline.reviewRound > 0 ? ' (review round ${pipeline.reviewRound})' : ''}',
                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                ],
              ),
            ],
            if (pipeline.error != null) ...[
              const SizedBox(height: 2),
              Row(
                children: [
                  Icon(Icons.error_outline, size: 12, color: Theme.of(context).colorScheme.error),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      pipeline.error!,
                      style: TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.error),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 2),
            Row(
              children: [
                const Icon(Icons.access_time, size: 12, color: Colors.grey),
                const SizedBox(width: 4),
                Text(timeAgo(pipeline.updatedAt), style: const TextStyle(fontSize: 12, color: Colors.grey)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
