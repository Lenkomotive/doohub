class TemplateNode {
  final String id;
  final String type;
  final String? name;
  final String? promptTemplate;
  final String? model;
  final String? statusLabel;
  final String? conditionField;

  TemplateNode({
    required this.id,
    required this.type,
    this.name,
    this.promptTemplate,
    this.model,
    this.statusLabel,
    this.conditionField,
  });

  factory TemplateNode.fromJson(Map<String, dynamic> json) {
    return TemplateNode(
      id: json['id'] as String,
      type: json['type'] as String,
      name: json['name'] as String?,
      promptTemplate: json['prompt_template'] as String?,
      model: json['model'] as String?,
      statusLabel: json['status_label'] as String?,
      conditionField: json['condition_field'] as String?,
    );
  }

  String get displayName => name ?? id;
}

class TemplateEdge {
  final String from;
  final String to;

  TemplateEdge({required this.from, required this.to});

  factory TemplateEdge.fromJson(Map<String, dynamic> json) {
    return TemplateEdge(
      from: json['from'] as String,
      to: json['to'] as String,
    );
  }
}

class TemplateDefinition {
  final String name;
  final List<TemplateNode> nodes;
  final List<TemplateEdge> edges;

  TemplateDefinition({
    required this.name,
    required this.nodes,
    required this.edges,
  });

  factory TemplateDefinition.fromJson(Map<String, dynamic> json) {
    return TemplateDefinition(
      name: json['name'] as String? ?? '',
      nodes: (json['nodes'] as List?)
              ?.map((e) => TemplateNode.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      edges: (json['edges'] as List?)
              ?.map((e) => TemplateEdge.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}

class PipelineTemplate {
  final int id;
  final String name;
  final String? description;
  final TemplateDefinition definition;
  final DateTime createdAt;
  final DateTime updatedAt;

  PipelineTemplate({
    required this.id,
    required this.name,
    this.description,
    required this.definition,
    required this.createdAt,
    required this.updatedAt,
  });

  factory PipelineTemplate.fromJson(Map<String, dynamic> json) {
    return PipelineTemplate(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      definition: TemplateDefinition.fromJson(
        json['definition'] as Map<String, dynamic>? ?? {'name': '', 'nodes': [], 'edges': []},
      ),
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}
