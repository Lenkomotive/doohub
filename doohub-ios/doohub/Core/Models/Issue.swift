import Foundation

struct Issue: Codable, Identifiable {
    let number: Int
    let title: String
    let body: String?
    let labels: [IssueLabel]?

    var id: Int { number }
}

struct IssueLabel: Codable {
    let name: String
    let color: String?
}
