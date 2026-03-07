import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../models/pipeline_template.dart';
import '../../services/api.dart';
import '../bloc/templates_cubit.dart';

class TemplatesScreen extends StatelessWidget {
  const TemplatesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) => TemplatesCubit(context.read<ApiService>()),
      child: const _TemplatesBody(),
    );
  }
}

class _TemplatesBody extends StatelessWidget {
  const _TemplatesBody();

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<TemplatesCubit, TemplatesState>(
      builder: (context, state) {
        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
              child: Row(
                children: [
                  Text('Templates', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w500)),
                  const SizedBox(width: 8),
                  Text('(${state.templates.length})', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey)),
                ],
              ),
            ),
            Expanded(
              child: state.isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : state.templates.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.account_tree_outlined, size: 32, color: Colors.grey.shade600),
                              const SizedBox(height: 8),
                              Text('No templates', style: TextStyle(color: Colors.grey.shade600)),
                              const SizedBox(height: 4),
                              Text('Create templates from the web dashboard', style: TextStyle(color: Colors.grey.shade500, fontSize: 12)),
                            ],
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: context.read<TemplatesCubit>().fetchTemplates,
                          child: ListView.builder(
                            padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                            itemCount: state.templates.length,
                            itemBuilder: (context, index) {
                              final template = state.templates[index];
                              return _TemplateTile(
                                template: template,
                                onTap: () => context.push('/templates/${template.id}'),
                              );
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

class _TemplateTile extends StatelessWidget {
  final PipelineTemplate template;
  final VoidCallback onTap;

  const _TemplateTile({required this.template, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Card(
        margin: EdgeInsets.zero,
        child: ListTile(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          onTap: onTap,
          leading: Icon(Icons.account_tree_outlined, color: cs.primary, size: 22),
          title: Text(
            template.name,
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
          ),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              template.description != null && template.description!.isNotEmpty
                  ? template.description!
                  : '${template.definition.nodes.length} nodes',
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          trailing: Text(
            _formatDate(template.updatedAt),
            style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
          ),
        ),
      ),
    );
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);
    if (diff.inDays == 0) return 'Today';
    if (diff.inDays == 1) return 'Yesterday';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return '${date.month}/${date.day}';
  }
}
