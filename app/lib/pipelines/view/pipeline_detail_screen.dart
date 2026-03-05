import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../models/pipeline.dart';
import '../bloc/pipelines_cubit.dart';
import '../bloc/pipelines_state.dart' show MergeStatus, PipelinesState;

class PipelineDetailScreen extends StatefulWidget {
  final String pipelineKey;

  const PipelineDetailScreen({super.key, required this.pipelineKey});

  @override
  State<PipelineDetailScreen> createState() => _PipelineDetailScreenState();
}

class _PipelineDetailScreenState extends State<PipelineDetailScreen> {
  bool _mergeChecked = false;

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<PipelinesCubit, PipelinesState>(
      builder: (context, state) {
        final pipeline = state.byKey(widget.pipelineKey);
        if (pipeline == null) {
          return Scaffold(
            appBar: AppBar(),
            body: const Center(child: Text('Pipeline not found')),
          );
        }

        // Auto-check merge status when pipeline is done and has a PR
        if (pipeline.status == 'done' &&
            pipeline.prUrl != null &&
            !_mergeChecked &&
            !state.mergeStatuses.containsKey(widget.pipelineKey)) {
          _mergeChecked = true;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            context.read<PipelinesCubit>().checkMergeStatus(widget.pipelineKey);
          });
        }

        final mergeStatus = state.mergeStatuses[widget.pipelineKey];
        final isMerging = state.mergingKeys.contains(widget.pipelineKey);

        return Scaffold(
          appBar: AppBar(
            title: Text(
              pipeline.displayTitle,
              style: const TextStyle(fontSize: 16),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            actions: [
              if (pipeline.isActive)
                IconButton(
                  icon: const Icon(Icons.cancel_outlined),
                  onPressed: () {
                    context.read<PipelinesCubit>().cancelPipeline(widget.pipelineKey);
                  },
                ),
            ],
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _StatusCard(pipeline: pipeline),
              const SizedBox(height: 12),
              _InfoCard(pipeline: pipeline),
              if (pipeline.plan != null) ...[
                const SizedBox(height: 12),
                _PlanCard(plan: pipeline.plan!),
              ],
              if (pipeline.prUrl != null) ...[
                const SizedBox(height: 12),
                _PrCard(prUrl: pipeline.prUrl!, prNumber: pipeline.prNumber),
              ],
              if (pipeline.status == 'done' && pipeline.prUrl != null) ...[
                const SizedBox(height: 12),
                _MergeCard(
                  pipelineKey: widget.pipelineKey,
                  mergeStatus: mergeStatus,
                  isMerging: isMerging,
                  prUrl: pipeline.prUrl!,
                ),
              ],
              if (pipeline.error != null) ...[
                const SizedBox(height: 12),
                _ErrorCard(error: pipeline.error!),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _StatusCard extends StatelessWidget {
  final Pipeline pipeline;

  const _StatusCard({required this.pipeline});

  @override
  Widget build(BuildContext context) {
    final (color, _) = _statusStyle(pipeline.status);
    final fmt = DateFormat('MMM d, HH:mm');

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    pipeline.status,
                    style: TextStyle(color: color, fontWeight: FontWeight.w600),
                  ),
                ),
                const Spacer(),
                if (pipeline.reviewRound > 0)
                  Text(
                    'Review round ${pipeline.reviewRound}',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Icon(Icons.schedule, size: 14, color: Colors.grey.shade500),
                const SizedBox(width: 4),
                Text(
                  'Created ${fmt.format(pipeline.createdAt.toLocal())}',
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(Icons.update, size: 14, color: Colors.grey.shade500),
                const SizedBox(width: 4),
                Text(
                  'Updated ${fmt.format(pipeline.updatedAt.toLocal())}',
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final Pipeline pipeline;

  const _InfoCard({required this.pipeline});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _row(Icons.folder_outlined, 'Repo', pipeline.repoPath.split('/').last),
            _row(Icons.memory, 'Model', pipeline.model),
            if (pipeline.issueNumber != null)
              _row(Icons.bug_report_outlined, 'Issue', '#${pipeline.issueNumber}'),
            if (pipeline.branch != null)
              _row(Icons.fork_right, 'Branch', pipeline.branch!),
            if (pipeline.totalCostUsd > 0)
              _row(Icons.attach_money, 'Cost', '\$${pipeline.totalCostUsd.toStringAsFixed(4)}'),
          ],
        ),
      ),
    );
  }

  Widget _row(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, size: 16, color: Colors.grey),
          const SizedBox(width: 8),
          Text('$label: ', style: const TextStyle(fontSize: 13, color: Colors.grey)),
          Expanded(
            child: Text(value, style: const TextStyle(fontSize: 13), overflow: TextOverflow.ellipsis),
          ),
        ],
      ),
    );
  }
}

class _PlanCard extends StatefulWidget {
  final String plan;

  const _PlanCard({required this.plan});

  @override
  State<_PlanCard> createState() => _PlanCardState();
}

class _PlanCardState extends State<_PlanCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => setState(() => _expanded = !_expanded),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.description_outlined, size: 18),
                  const SizedBox(width: 8),
                  const Text('Plan', style: TextStyle(fontWeight: FontWeight.w600)),
                  const Spacer(),
                  Icon(_expanded ? Icons.expand_less : Icons.expand_more),
                ],
              ),
              if (_expanded) ...[
                const SizedBox(height: 12),
                SelectableText(
                  widget.plan,
                  style: const TextStyle(fontSize: 13, height: 1.5),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _PrCard extends StatelessWidget {
  final String prUrl;
  final int? prNumber;

  const _PrCard({required this.prUrl, this.prNumber});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        leading: const Icon(Icons.open_in_new, color: Colors.blue),
        title: Text(
          prNumber != null ? 'PR #$prNumber' : 'Pull Request',
          style: const TextStyle(fontWeight: FontWeight.w500),
        ),
        subtitle: Text(prUrl, style: const TextStyle(fontSize: 12, color: Colors.grey)),
        onTap: () => launchUrl(Uri.parse(prUrl)),
      ),
    );
  }
}

class _MergeCard extends StatelessWidget {
  final String pipelineKey;
  final MergeStatus? mergeStatus;
  final bool isMerging;
  final String prUrl;

  const _MergeCard({
    required this.pipelineKey,
    required this.mergeStatus,
    required this.isMerging,
    required this.prUrl,
  });

  @override
  Widget build(BuildContext context) {
    if (mergeStatus == null) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Row(
            children: [
              SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
              SizedBox(width: 12),
              Text('Checking merge status...', style: TextStyle(fontSize: 13)),
            ],
          ),
        ),
      );
    }

    if (mergeStatus!.error != null) {
      return Card(
        child: ListTile(
          leading: const Icon(Icons.error_outline, color: Colors.red),
          title: Text(mergeStatus!.error!, style: const TextStyle(fontSize: 13, color: Colors.red)),
          trailing: TextButton(
            onPressed: () => context.read<PipelinesCubit>().checkMergeStatus(pipelineKey),
            child: const Text('Retry'),
          ),
        ),
      );
    }

    if (mergeStatus!.alreadyMerged) {
      return Card(
        child: ListTile(
          leading: const Icon(Icons.check_circle, color: Colors.green),
          title: const Text('Already merged', style: TextStyle(fontWeight: FontWeight.w500)),
        ),
      );
    }

    if (mergeStatus!.closed) {
      return Card(
        child: ListTile(
          leading: const Icon(Icons.cancel, color: Colors.grey),
          title: const Text('PR is closed', style: TextStyle(fontWeight: FontWeight.w500)),
        ),
      );
    }

    if (mergeStatus!.hasConflicts) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: Colors.orange),
                icon: const Icon(Icons.warning_amber_rounded),
                label: const Text('Resolve Conflicts'),
                onPressed: () => launchUrl(Uri.parse('$prUrl/conflicts')),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () {
                  context.read<PipelinesCubit>().checkMergeStatus(pipelineKey);
                },
                child: const Text('Re-check status'),
              ),
            ],
          ),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: FilledButton.icon(
          style: FilledButton.styleFrom(backgroundColor: Colors.green),
          icon: isMerging
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : const Icon(Icons.merge),
          label: Text(isMerging ? 'Merging...' : 'Merge'),
          onPressed: isMerging
              ? null
              : () => context.read<PipelinesCubit>().mergePipeline(pipelineKey),
        ),
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  final String error;

  const _ErrorCard({required this.error});

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Colors.red.withValues(alpha: 0.1),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.error_outline, color: Colors.red, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: SelectableText(
                error,
                style: const TextStyle(fontSize: 13, color: Colors.red),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

(Color, String) _statusStyle(String status) {
  return switch (status) {
    'planning' || 'planned' => (Colors.blue, status),
    'developing' || 'developed' => (Colors.orange, status),
    'reviewing' => (Colors.purple, status),
    'done' || 'merged' => (Colors.green, status),
    'failed' => (Colors.red, status),
    'cancelled' => (Colors.grey, status),
    _ => (Colors.grey, status),
  };
}
