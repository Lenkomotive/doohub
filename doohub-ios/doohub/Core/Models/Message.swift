import Foundation

struct Message: Codable, Identifiable {
    let id: Int
    let role: String
    let content: String
    let createdAt: Date
    let attachments: [Attachment]?

    var isUser: Bool { role == "user" }
    var isAssistant: Bool { role == "assistant" }
}

struct Attachment: Codable, Identifiable {
    let id: Int?
    let filename: String
    let mimeType: String
    let fileSize: Int
    let url: String?

    var isDocument: Bool {
        let ext = fileExtension.lowercased()
        return ["pdf", "txt", "md", "doc", "docx"].contains(ext)
    }

    var fileExtension: String {
        (filename as NSString).pathExtension
    }

    var fileSizeFormatted: String {
        if fileSize < 1024 {
            return "\(fileSize) B"
        } else if fileSize < 1024 * 1024 {
            return String(format: "%.1f KB", Double(fileSize) / 1024.0)
        } else {
            return String(format: "%.1f MB", Double(fileSize) / (1024.0 * 1024.0))
        }
    }
}
