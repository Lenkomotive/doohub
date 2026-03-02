import 'dart:async';
import 'package:flutter/material.dart';
import '../models/pipeline.dart';
import '../services/api.dart';

class PipelinesScreen extends StatefulWidget {
  final ApiService api;

  const PipelinesScreen({super.key, required this.api});

  @override
  State<PipelinesScreen> createState() => _PipelinesScreenState();
}

class _PipelinesScreenState extends State<PipelinesScreen> {
  List<Pipeline> _pipelines = [];
  int _total = 0;
  String? _filter;
  bool _loading = true;
  Timer? _timer;

  final _filters = [
    (label: 'All', value: null),
    (label: 'Active', value: 'active'),
    (label: 'Done', value: 'done'),
    (label: 'Failed', value: 'failed'),
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
      final data = await widget.api.getPipelines(status: _filter);
      if (!mounted) return;
      setState(() {
        _pipelines = (data['pipelines'] as List).map((e) => Pipeline.fromJson(e)).toList();
        _total = data['total'] ?? _pipelines.length;
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _setFilter(String? value) {
    setState(() {
      _filter = value;
      _loading = true;
    });
    _fetch();
  }

  String _timeAgo(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inSeconds < 60) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
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
              Text('Pipelines', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w500)),
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
          child: _loading && _pipelines.isEmpty
              ? const Center(child: CircularProgressIndicator())
              : _pipelines.isEmpty
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
                      onRefresh: _fetch,
                      child: ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        itemCount: _pipelines.length,
                        itemBuilder: (context, index) {
                          final p = _pipelines[index];
                          return _PipelineTile(pipeline: p, timeAgo: _timeAgo);
                        },
                      ),
                    ),
        ),
      ],
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
