import Foundation

struct PipelineTemplate: Codable, Identifiable, Hashable {
    static func == (lhs: PipelineTemplate, rhs: PipelineTemplate) -> Bool {
        lhs.id == rhs.id
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    let id: Int
    let name: String
    let description: String?
    let definition: TemplateDefinition?
    let createdAt: Date
    let updatedAt: Date
}

struct TemplateDefinition: Codable {
    let name: String
    let nodes: [TemplateNode]
    let edges: [TemplateEdge]
}

struct TemplateNode: Codable, Identifiable {
    let id: String
    let type: String
    let name: String?
    let promptTemplate: String?
    let model: String?
    let statusLabel: String?
    let conditionField: String?
}

struct TemplateEdge: Codable {
    let from: String
    let to: String
}
