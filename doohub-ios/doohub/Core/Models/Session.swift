import Foundation

struct Session: Codable, Identifiable {
    let sessionKey: String
    let name: String
    let status: String
    let model: String
    let projectPath: String?
    let claudeSessionId: String?
    let mode: String?

    var id: String { sessionKey }

    var isActive: Bool {
        status == "busy"
    }
}
