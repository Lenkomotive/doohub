import SwiftUI

struct TemplateDetailScreen: View {
    let templateId: Int

    @EnvironmentObject private var templatesStore: TemplatesStore
    @Environment(\.colorScheme) private var colorScheme

    private var template: PipelineTemplate? {
        templatesStore.templateDetails[templateId]
    }

    var body: some View {
        ZStack {
            MeshBackground()

            if let template, let definition = template.definition {
                GraphView(definition: definition)
            } else {
                ProgressView()
            }
        }
        .navigationTitle(template?.name ?? "Template")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await templatesStore.fetchTemplateDetail(id: templateId)
        }
    }
}

// MARK: - Graph View

private struct GraphView: View {
    let definition: TemplateDefinition
    @Environment(\.colorScheme) private var colorScheme
    @State private var selectedNode: TemplateNode?

    private let nodeWidth: CGFloat = 140
    private let nodeHeight: CGFloat = 50
    private let layerSpacing: CGFloat = 120
    private let nodeSpacing: CGFloat = 80

    var body: some View {
        let layout = computeLayout()

        ScrollView([.horizontal, .vertical]) {
            ZStack {
                // Draw edges
                Canvas { context, size in
                    for edge in definition.edges {
                        guard let fromPos = layout[edge.from],
                              let toPos = layout[edge.to] else { continue }

                        let from = CGPoint(x: fromPos.x + nodeWidth / 2, y: fromPos.y + nodeHeight)
                        let to = CGPoint(x: toPos.x + nodeWidth / 2, y: toPos.y)

                        var path = Path()
                        path.move(to: from)

                        let controlY = (from.y + to.y) / 2
                        path.addCurve(
                            to: to,
                            control1: CGPoint(x: from.x, y: controlY),
                            control2: CGPoint(x: to.x, y: controlY)
                        )

                        context.stroke(
                            path,
                            with: .color(AppTheme.textSecondaryColor(for: colorScheme).opacity(0.5)),
                            lineWidth: 1.5
                        )

                        // Arrow head
                        let arrowSize: CGFloat = 8
                        let angle = atan2(to.y - controlY, to.x - to.x)
                        var arrow = Path()
                        arrow.move(to: to)
                        arrow.addLine(to: CGPoint(
                            x: to.x - arrowSize * cos(angle - .pi / 6),
                            y: to.y - arrowSize * sin(angle - .pi / 6)
                        ))
                        arrow.move(to: to)
                        arrow.addLine(to: CGPoint(
                            x: to.x - arrowSize * cos(angle + .pi / 6),
                            y: to.y - arrowSize * sin(angle + .pi / 6)
                        ))
                        context.stroke(
                            arrow,
                            with: .color(AppTheme.textSecondaryColor(for: colorScheme).opacity(0.5)),
                            lineWidth: 1.5
                        )
                    }
                }

                // Draw nodes
                ForEach(definition.nodes) { node in
                    if let pos = layout[node.id] {
                        NodeView(node: node, isSelected: selectedNode?.id == node.id)
                            .position(x: pos.x + nodeWidth / 2, y: pos.y + nodeHeight / 2)
                            .onTapGesture {
                                withAnimation {
                                    selectedNode = selectedNode?.id == node.id ? nil : node
                                }
                            }
                    }
                }
            }
            .frame(
                width: max(400, computeCanvasSize(layout).width + 80),
                height: max(400, computeCanvasSize(layout).height + 80)
            )
            .padding(40)
        }
        .overlay(alignment: .bottom) {
            if let node = selectedNode {
                nodeInfoOverlay(node)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
    }

    @ViewBuilder
    private func nodeInfoOverlay(_ node: TemplateNode) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(node.name ?? node.id)
                .font(.headline)

            if let model = node.model {
                Text("Model: \(model)")
                    .font(.caption)
            }

            if let condition = node.conditionField {
                Text("Condition: \(condition)")
                    .font(.caption)
            }

            Text("Type: \(node.type)")
                .font(.caption)
                .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .padding(16)
    }

    // BFS topological layout
    private func computeLayout() -> [String: CGPoint] {
        var result: [String: CGPoint] = [:]

        // Build adjacency list
        var children: [String: [String]] = [:]
        var parents: [String: [String]] = [:]

        for node in definition.nodes {
            children[node.id] = []
            parents[node.id] = []
        }

        for edge in definition.edges {
            children[edge.from, default: []].append(edge.to)
            parents[edge.to, default: []].append(edge.from)
        }

        // Find root nodes (no parents)
        let roots = definition.nodes.filter { (parents[$0.id] ?? []).isEmpty }

        // BFS to assign layers
        var layers: [[String]] = []
        var visited = Set<String>()
        var queue = roots.map { $0.id }
        visited.formUnion(queue)

        while !queue.isEmpty {
            layers.append(queue)
            var nextQueue: [String] = []
            for nodeId in queue {
                for childId in children[nodeId] ?? [] {
                    if !visited.contains(childId) {
                        visited.insert(childId)
                        nextQueue.append(childId)
                    }
                }
            }
            queue = nextQueue
        }

        // Add any unvisited nodes
        let unvisited = definition.nodes.filter { !visited.contains($0.id) }
        if !unvisited.isEmpty {
            layers.append(unvisited.map { $0.id })
        }

        // Position nodes
        let maxNodesInLayer = layers.map { $0.count }.max() ?? 1

        for (layerIndex, layer) in layers.enumerated() {
            let layerWidth = CGFloat(layer.count) * (nodeWidth + nodeSpacing) - nodeSpacing
            let maxWidth = CGFloat(maxNodesInLayer) * (nodeWidth + nodeSpacing) - nodeSpacing
            let offsetX = (maxWidth - layerWidth) / 2

            for (nodeIndex, nodeId) in layer.enumerated() {
                let x = offsetX + CGFloat(nodeIndex) * (nodeWidth + nodeSpacing)
                let y = CGFloat(layerIndex) * (nodeHeight + layerSpacing)
                result[nodeId] = CGPoint(x: x, y: y)
            }
        }

        return result
    }

    private func computeCanvasSize(_ layout: [String: CGPoint]) -> CGSize {
        var maxX: CGFloat = 0
        var maxY: CGFloat = 0
        for pos in layout.values {
            maxX = max(maxX, pos.x + nodeWidth)
            maxY = max(maxY, pos.y + nodeHeight)
        }
        return CGSize(width: maxX, height: maxY)
    }
}

// MARK: - Node View

private struct NodeView: View {
    let node: TemplateNode
    let isSelected: Bool
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        Group {
            switch node.type {
            case "start", "end", "failed":
                CircleNodeView(node: node, isSelected: isSelected)
            default:
                RectNodeView(node: node, isSelected: isSelected)
            }
        }
    }
}

private struct CircleNodeView: View {
    let node: TemplateNode
    let isSelected: Bool
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        ZStack {
            Circle()
                .fill(nodeColor.opacity(0.15))
                .frame(width: 50, height: 50)

            Circle()
                .stroke(nodeColor, lineWidth: isSelected ? 3 : 2)
                .frame(width: 50, height: 50)

            Text(node.name ?? node.type.capitalized)
                .font(.caption2)
                .fontWeight(.semibold)
                .foregroundColor(nodeColor)
        }
    }

    private var nodeColor: Color {
        switch node.type {
        case "start": return AppColors.success
        case "end": return AppTheme.textSecondaryColor(for: colorScheme)
        case "failed": return AppColors.error
        default: return AppTheme.primaryColor(for: colorScheme)
        }
    }
}

private struct RectNodeView: View {
    let node: TemplateNode
    let isSelected: Bool
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        VStack(spacing: 2) {
            Text(node.name ?? node.id)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(AppTheme.textPrimaryColor(for: colorScheme))
                .lineLimit(2)
                .multilineTextAlignment(.center)

            if let model = node.model {
                Text(model)
                    .font(.caption2)
                    .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
            } else if let condition = node.conditionField {
                Text(condition)
                    .font(.caption2)
                    .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .frame(width: 140)
        .background(AppTheme.cardColor(for: colorScheme))
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(borderColor, lineWidth: isSelected ? 3 : 2)
        )
    }

    private var borderColor: Color {
        node.type == "condition" ? AppColors.warning : AppTheme.primaryColor(for: colorScheme)
    }
}
