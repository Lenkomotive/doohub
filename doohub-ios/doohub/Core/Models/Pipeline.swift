import Foundation

struct Pipeline: Codable, Identifiable {
    let pipelineKey: String
    let repoPath: String
    let issueNumber: Int?
    let issueTitle: String?
    let taskDescription: String?
    let status: String
    let plan: String?
    let branch: String?
    let prNumber: Int?
    let prUrl: String?
    let error: String?
    let reviewRound: Int
    let model: String
    let totalCostUsd: Double
    let templateId: Int?
    let templateName: String?
    let createdAt: Date
    let updatedAt: Date

    var id: String { pipelineKey }

    var isActive: Bool {
        ["planning", "planned", "developing", "developed", "reviewing"].contains(status)
    }
}

struct MergeStatus: Codable {
    let mergeable: Bool
    let hasConflicts: Bool
    let alreadyMerged: Bool
    let closed: Bool
    let error: String?
}
