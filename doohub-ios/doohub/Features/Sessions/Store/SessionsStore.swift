import SwiftUI
import Foundation

@MainActor
class SessionsStore: ObservableObject {
    @Published var sessions: [Session] = []
    @Published var isLoading: Bool = false
    @Published var messageCache: [String: [Message]] = [:]
    @Published var sendingKeys: Set<String> = []
    @Published var pendingAttachments: [String: [PendingAttachment]] = [:]

    private let apiService: APIService
    private var sseClient: SSEClient?

    struct PendingAttachment: Identifiable {
        let id = UUID()
        let data: Data
        let filename: String
        let mimeType: String
        let fileSize: Int

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

    init(apiService: APIService) {
        self.apiService = apiService
    }

    func fetchSessions() async {
        isLoading = true
        do {
            let fetched = try await apiService.getSessions()
            sessions = fetched
        } catch {
            // Silent failure
        }
        isLoading = false
    }

    func createSession(model: String, mode: String, projectPath: String?) async -> Session? {
        do {
            let session = try await apiService.createSession(model: model, mode: mode, projectPath: projectPath)
            sessions.insert(session, at: 0)
            return session
        } catch {
            return nil
        }
    }

    func deleteSession(key: String) async {
        sessions.removeAll { $0.sessionKey == key }
        do {
            try await apiService.deleteSession(key: key)
        } catch {
            await fetchSessions()
        }
    }

    func cancelSession(key: String) async {
        do {
            try await apiService.cancelSession(key: key)
        } catch {
            // Silent
        }
    }

    func fetchHistory(sessionKey: String) async {
        do {
            let messages = try await apiService.getMessageHistory(sessionKey: sessionKey)
            messageCache[sessionKey] = messages
        } catch {
            // Silent
        }
    }

    func sendMessage(sessionKey: String, content: String) async {
        guard !content.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }

        sendingKeys.insert(sessionKey)

        // Create optimistic user message
        let optimisticMessage = Message(
            id: Int.random(in: 100000...999999),
            role: "user",
            content: content,
            createdAt: Date(),
            attachments: nil
        )

        var currentMessages = messageCache[sessionKey] ?? []
        currentMessages.append(optimisticMessage)
        messageCache[sessionKey] = currentMessages

        let attachments = pendingAttachments[sessionKey] ?? []
        let uploadAttachments = attachments.map { (data: $0.data, filename: $0.filename, mimeType: $0.mimeType) }
        pendingAttachments[sessionKey] = []

        do {
            let _ = try await apiService.sendMessage(
                sessionKey: sessionKey,
                content: content,
                attachments: uploadAttachments
            )
            // Refresh history to get server-side message
            await fetchHistory(sessionKey: sessionKey)
        } catch {
            // Remove optimistic message on failure
            messageCache[sessionKey]?.removeAll { $0.id == optimisticMessage.id }
        }

        sendingKeys.remove(sessionKey)
    }

    func addPendingAttachment(sessionKey: String, data: Data, filename: String, mimeType: String) {
        guard data.count <= AppConstants.maxFileSize else { return }
        let attachment = PendingAttachment(data: data, filename: filename, mimeType: mimeType, fileSize: data.count)
        var current = pendingAttachments[sessionKey] ?? []
        current.append(attachment)
        pendingAttachments[sessionKey] = current
    }

    func removePendingAttachment(sessionKey: String, attachmentId: UUID) {
        pendingAttachments[sessionKey]?.removeAll { $0.id == attachmentId }
    }

    // MARK: - SSE

    func connectSSE() {
        Task {
            guard let url = await apiService.sessionEventsURL() else { return }
            sseClient?.disconnect()
            sseClient = SSEClient(url: url)
            sseClient?.connect { [weak self] event in
                Task { @MainActor in
                    self?.handleSSEEvent(event)
                }
            }
        }
    }

    func disconnectSSE() {
        sseClient?.disconnect()
        sseClient = nil
    }

    private func handleSSEEvent(_ event: SSEEvent) {
        guard let data = event.data.data(using: .utf8) else { return }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)
            let formatters: [DateFormatter] = {
                let f1 = DateFormatter()
                f1.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
                f1.timeZone = TimeZone(identifier: "UTC")
                let f2 = DateFormatter()
                f2.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
                f2.timeZone = TimeZone(identifier: "UTC")
                return [f1, f2]
            }()
            for formatter in formatters {
                if let date = formatter.date(from: dateString) { return date }
            }
            let iso = ISO8601DateFormatter()
            iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = iso.date(from: dateString) { return date }
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Cannot decode date: \(dateString)")
        }

        switch event.event {
        case "snapshot":
            // Backend sends {"sessions": {"key1": {...}, "key2": {...}}}
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let sessionsDict = json["sessions"] as? [String: [String: Any]] {
                var parsed: [Session] = []
                for (key, info) in sessionsDict {
                    let s = Session(
                        sessionKey: key,
                        name: info["name"] as? String ?? key,
                        status: info["status"] as? String ?? "idle",
                        model: info["model"] as? String ?? "sonnet",
                        projectPath: info["project_path"] as? String,
                        claudeSessionId: info["claude_session_id"] as? String,
                        mode: info["mode"] as? String
                    )
                    parsed.append(s)
                }
                sessions = parsed
            }
        case "status":
            if let statusUpdate = try? decoder.decode(SessionStatusUpdate.self, from: data) {
                if let index = sessions.firstIndex(where: { $0.sessionKey == statusUpdate.sessionKey }) {
                    let old = sessions[index]
                    sessions[index] = Session(
                        sessionKey: old.sessionKey,
                        name: old.name,
                        status: statusUpdate.status,
                        model: old.model,
                        projectPath: old.projectPath,
                        claudeSessionId: old.claudeSessionId,
                        mode: old.mode
                    )
                    // Auto-refresh history when session becomes idle
                    if statusUpdate.status == "idle" && old.status == "busy" {
                        Task {
                            await fetchHistory(sessionKey: statusUpdate.sessionKey)
                        }
                    }
                }
            }
        default:
            break
        }
    }
}

struct SessionStatusUpdate: Decodable {
    let sessionKey: String
    let status: String
}
