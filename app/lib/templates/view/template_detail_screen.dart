import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../models/pipeline_template.dart';
import '../../services/api.dart';

// ── Layout constants ──

const double _nodeW = 160;
const double _nodeH = 56;
const double _circleSize = 48;
const double _hGap = 40;
const double _vGap = 80;
const double _padding = 40;

// ── Simple DAG layout (BFS layers) ──

class _LayoutNode {
  final TemplateNode node;
  double x = 0;
  double y = 0;
  Size get size => _isCircle(node.type)
      ? const Size(_circleSize, _circleSize)
      : const Size(_nodeW, _nodeH);

  _LayoutNode(this.node);
}

bool _isCircle(String type) => type == 'start' || type == 'end' || type == 'failed';

List<_LayoutNode> _layoutNodes(TemplateDefinition def) {
  final nodeMap = <String, _LayoutNode>{};
  for (final n in def.nodes) {
    nodeMap[n.id] = _LayoutNode(n);
  }

  // Build adjacency
  final children = <String, List<String>>{};
  final inDegree = <String, int>{};
  for (final n in def.nodes) {
    children[n.id] = [];
    inDegree[n.id] = 0;
  }
  for (final e in def.edges) {
    children[e.from]?.add(e.to);
    inDegree[e.to] = (inDegree[e.to] ?? 0) + 1;
  }

  // BFS layering (topological)
  final layers = <List<String>>[];
  var current = inDegree.entries.where((e) => e.value == 0).map((e) => e.key).toList();
  final visited = <String>{};

  while (current.isNotEmpty) {
    layers.add(current);
    visited.addAll(current);
    final next = <String>{};
    for (final id in current) {
      for (final child in children[id] ?? []) {
        if (!visited.contains(child)) next.add(child);
      }
    }
    current = next.toList();
  }

  // Add any disconnected nodes
  for (final n in def.nodes) {
    if (!visited.contains(n.id)) {
      if (layers.isEmpty) layers.add([]);
      layers.last.add(n.id);
    }
  }

  // Calculate max layer width for centering
  double maxLayerWidth = 0;
  for (final layer in layers) {
    final w = layer.fold<double>(0, (s, id) => s + nodeMap[id]!.size.width) +
        (layer.length - 1) * _hGap;
    maxLayerWidth = max(maxLayerWidth, w);
  }

  // Position nodes centered per layer
  double y = _padding;
  for (final layer in layers) {
    final totalWidth = layer.fold<double>(0, (sum, id) => sum + nodeMap[id]!.size.width) +
        (layer.length - 1) * _hGap;
    double x = _padding + (maxLayerWidth - totalWidth) / 2;

    for (final id in layer) {
      final ln = nodeMap[id]!;
      ln.x = x;
      ln.y = y;
      x += ln.size.width + _hGap;
    }

    final maxH = layer.fold<double>(0, (h, id) => max(h, nodeMap[id]!.size.height));
    y += maxH + _vGap;
  }

  return nodeMap.values.toList();
}

// ── Edge painter ──

class _EdgePainter extends CustomPainter {
  final List<_LayoutNode> nodes;
  final List<TemplateEdge> edges;
  final Color color;

  _EdgePainter({required this.nodes, required this.edges, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final nodeMap = <String, _LayoutNode>{};
    for (final n in nodes) {
      nodeMap[n.node.id] = n;
    }

    final linePaint = Paint()
      ..color = color
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;

    final arrowPaint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;

    for (final edge in edges) {
      final from = nodeMap[edge.from];
      final to = nodeMap[edge.to];
      if (from == null || to == null) continue;

      final startX = from.x + from.size.width / 2;
      final startY = from.y + from.size.height;
      final endX = to.x + to.size.width / 2;
      final endY = to.y;

      final path = Path()
        ..moveTo(startX, startY)
        ..cubicTo(
          startX, startY + (endY - startY) * 0.4,
          endX, endY - (endY - startY) * 0.4,
          endX, endY,
        );
      canvas.drawPath(path, linePaint);

      // Arrow head
      const arrowSize = 5.0;
      final arrowPath = Path()
        ..moveTo(endX, endY)
        ..lineTo(endX - arrowSize, endY - arrowSize * 1.5)
        ..lineTo(endX + arrowSize, endY - arrowSize * 1.5)
        ..close();
      canvas.drawPath(arrowPath, arrowPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _EdgePainter old) => true;
}

// ── Node widgets ──

class _CircleNode extends StatelessWidget {
  final TemplateNode node;

  const _CircleNode({required this.node});

  @override
  Widget build(BuildContext context) {
    final (color, icon, label) = switch (node.type) {
      'start' => (Colors.green, Icons.play_arrow, 'Start'),
      'end' => (Colors.grey, Icons.stop, 'Done'),
      'failed' => (Colors.red, Icons.stop, 'Failed'),
      _ => (Colors.grey, Icons.circle, node.type),
    };

    return SizedBox(
      width: _circleSize,
      height: _circleSize,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: _circleSize,
            height: _circleSize - 14,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: color, width: 2),
              color: color.withValues(alpha: 0.1),
            ),
            child: Icon(icon, color: color, size: 18),
          ),
          Text(label, style: TextStyle(fontSize: 9, color: color)),
        ],
      ),
    );
  }
}

class _RectNode extends StatelessWidget {
  final TemplateNode node;

  const _RectNode({required this.node});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isCondition = node.type == 'condition';

    final borderColor = isCondition ? Colors.amber : cs.primary;
    final bgColor = isCondition ? Colors.amber.withValues(alpha: 0.05) : cs.surface;

    return Container(
      width: _nodeW,
      height: _nodeH,
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: borderColor.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              Icon(
                isCondition ? Icons.fork_right : Icons.smart_toy_outlined,
                size: 14,
                color: borderColor,
              ),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  node.displayName,
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text(
            isCondition
                ? (node.conditionField ?? 'condition')
                : (node.model ?? 'default'),
            style: TextStyle(fontSize: 10, color: Colors.grey.shade500),
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

// ── Detail screen ──

class TemplateDetailScreen extends StatefulWidget {
  final int templateId;

  const TemplateDetailScreen({super.key, required this.templateId});

  @override
  State<TemplateDetailScreen> createState() => _TemplateDetailScreenState();
}

class _TemplateDetailScreenState extends State<TemplateDetailScreen> {
  PipelineTemplate? _template;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = context.read<ApiService>();
      final data = await api.getTemplate(widget.templateId);
      if (mounted) {
        setState(() {
          _template = PipelineTemplate.fromJson(data);
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_template?.name ?? 'Template', style: const TextStyle(fontSize: 16)),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _template == null
              ? const Center(child: Text('Template not found'))
              : _GraphView(template: _template!),
    );
  }
}

class _GraphView extends StatelessWidget {
  final PipelineTemplate template;

  const _GraphView({required this.template});

  @override
  Widget build(BuildContext context) {
    final layoutNodes = _layoutNodes(template.definition);
    if (layoutNodes.isEmpty) {
      return const Center(child: Text('No nodes', style: TextStyle(color: Colors.grey)));
    }

    // Calculate canvas size
    double maxX = 0, maxY = 0;
    for (final n in layoutNodes) {
      maxX = max(maxX, n.x + n.size.width);
      maxY = max(maxY, n.y + n.size.height);
    }
    final canvasSize = Size(maxX + _padding * 2, maxY + _padding + 20);

    final edgeColor = Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.25);

    return InteractiveViewer(
      constrained: false,
      boundaryMargin: const EdgeInsets.all(100),
      minScale: 0.3,
      maxScale: 2.0,
      child: SizedBox(
        width: canvasSize.width,
        height: canvasSize.height,
        child: Stack(
          children: [
            // Edges
            Positioned.fill(
              child: CustomPaint(
                painter: _EdgePainter(
                  nodes: layoutNodes,
                  edges: template.definition.edges,
                  color: edgeColor,
                ),
              ),
            ),
            // Nodes
            for (final ln in layoutNodes)
              Positioned(
                left: ln.x,
                top: ln.y,
                child: _isCircle(ln.node.type)
                    ? _CircleNode(node: ln.node)
                    : _RectNode(node: ln.node),
              ),
          ],
        ),
      ),
    );
  }
}
