import Foundation

struct Repository: Codable, Identifiable, Hashable {
    let path: String
    let name: String?

    var id: String { path }

    var displayName: String {
        name ?? path.components(separatedBy: "/").last ?? path
    }
}
