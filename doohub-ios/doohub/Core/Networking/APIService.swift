import Foundation

enum APIError: Error, LocalizedError {
    case unauthorized
    case badRequest(String)
    case serverError(String)
    case networkError(Error)
    case decodingError(Error)
    case unknown

    var errorDescription: String? {
        switch self {
        case .unauthorized: return "Unauthorized"
        case .badRequest(let msg): return msg
        case .serverError(let msg): return msg
        case .networkError(let error): return error.localizedDescription
        case .decodingError(let error): return "Decoding error: \(error.localizedDescription)"
        case .unknown: return "Unknown error"
        }
    }
}

actor APIService {
    private let baseURL: String
    private let session: URLSession
    private let decoder: JSONDecoder

    init(baseURL: String = AppConstants.apiBaseUrl) {
        self.baseURL = baseURL
        self.session = URLSession.shared
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
                let f3 = DateFormatter()
                f3.dateFormat = "yyyy-MM-dd'T'HH:mm:ssZ"
                f3.timeZone = TimeZone(identifier: "UTC")
                return [f1, f2, f3]
            }()

            for formatter in formatters {
                if let date = formatter.date(from: dateString) {
                    return date
                }
            }

            let iso = ISO8601DateFormatter()
            iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = iso.date(from: dateString) {
                return date
            }

            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Cannot decode date: \(dateString)")
        }
        self.decoder = decoder
    }

    // MARK: - Token Management

    private var accessToken: String? {
        get { KeychainHelper.get(key: "access_token") }
    }

    private var refreshToken: String? {
        get { KeychainHelper.get(key: "refresh_token") }
    }

    func setTokens(access: String, refresh: String) {
        KeychainHelper.set(key: "access_token", value: access)
        KeychainHelper.set(key: "refresh_token", value: refresh)
    }

    func clearTokens() {
        KeychainHelper.delete(key: "access_token")
        KeychainHelper.delete(key: "refresh_token")
    }

    var hasTokens: Bool {
        accessToken != nil
    }

    // MARK: - Request Building

    private func makeRequest(path: String, method: String = "GET", body: Data? = nil, queryItems: [URLQueryItem]? = nil) -> URLRequest {
        var components = URLComponents(string: "\(baseURL)\(path)")!
        if let queryItems {
            components.queryItems = queryItems
        }
        var request = URLRequest(url: components.url!)
        request.httpMethod = method
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    // MARK: - Request Execution

    private func execute<T: Decodable>(_ request: URLRequest) async throws -> T {
        print("[API] \(request.httpMethod ?? "?") \(request.url?.absoluteString ?? "??")")
        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.unknown
        }

        print("[API] Response: \(httpResponse.statusCode) | Body: \(String(data: data, encoding: .utf8) ?? "nil")")

        if httpResponse.statusCode == 401 {
            // Try token refresh
            if let _ = refreshToken {
                let refreshed = try await performRefresh()
                if refreshed {
                    var retryRequest = request
                    if let token = accessToken {
                        retryRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
                    }
                    let (retryData, retryResponse) = try await session.data(for: retryRequest)
                    guard let retryHttp = retryResponse as? HTTPURLResponse else {
                        throw APIError.unknown
                    }
                    if retryHttp.statusCode == 401 {
                        throw APIError.unauthorized
                    }
                    return try decoder.decode(T.self, from: retryData)
                }
            }
            throw APIError.unauthorized
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            if let errorBody = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let detail = errorBody["detail"] as? String {
                throw APIError.serverError(detail)
            }
            throw APIError.serverError("HTTP \(httpResponse.statusCode)")
        }

        return try decoder.decode(T.self, from: data)
    }

    private func executeNoContent(_ request: URLRequest) async throws {
        print("[API] \(request.httpMethod ?? "?") \(request.url?.absoluteString ?? "??") (no content)")
        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.unknown
        }

        print("[API] Response: \(httpResponse.statusCode) | Body: \(String(data: data, encoding: .utf8) ?? "nil")")

        if httpResponse.statusCode == 401 {
            if let _ = refreshToken {
                let refreshed = try await performRefresh()
                if refreshed {
                    var retryRequest = request
                    if let token = accessToken {
                        retryRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
                    }
                    let (_, retryResponse) = try await session.data(for: retryRequest)
                    guard let retryHttp = retryResponse as? HTTPURLResponse else {
                        throw APIError.unknown
                    }
                    if retryHttp.statusCode == 401 {
                        throw APIError.unauthorized
                    }
                    return
                }
            }
            throw APIError.unauthorized
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            if let errorBody = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let detail = errorBody["detail"] as? String {
                throw APIError.serverError(detail)
            }
            throw APIError.serverError("HTTP \(httpResponse.statusCode)")
        }
    }

    private func performRefresh() async throws -> Bool {
        guard let refresh = refreshToken else { return false }

        var request = URLRequest(url: URL(string: "\(baseURL)/auth/refresh")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = ["refresh_token": refresh]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            clearTokens()
            return false
        }

        struct TokenResponse: Decodable {
            let access_token: String
            let refresh_token: String
        }

        let tokens = try JSONDecoder().decode(TokenResponse.self, from: data)
        setTokens(access: tokens.access_token, refresh: tokens.refresh_token)
        return true
    }

    // MARK: - Auth Endpoints

    struct LoginResponse: Decodable {
        let accessToken: String
        let refreshToken: String
    }

    struct UserResponse: Decodable {
        let username: String
    }

    func login(username: String, password: String) async throws -> LoginResponse {
        let body = try JSONSerialization.data(withJSONObject: ["username": username, "password": password])
        let request = makeRequest(path: "/auth/login", method: "POST", body: body)
        return try await execute(request)
    }

    func getMe() async throws -> UserResponse {
        let request = makeRequest(path: "/auth/me")
        return try await execute(request)
    }

    func registerFcmToken(_ token: String) async throws {
        let body = try JSONSerialization.data(withJSONObject: ["fcm_token": token])
        let request = makeRequest(path: "/auth/fcm-token", method: "PUT", body: body)
        try await executeNoContent(request)
    }

    struct NotificationSettings: Codable {
        var sessions: Bool
        var pipelines: Bool
    }

    func getNotificationSettings() async throws -> NotificationSettings {
        let request = makeRequest(path: "/auth/notifications")
        return try await execute(request)
    }

    func updateNotificationSettings(_ settings: NotificationSettings) async throws {
        let body = try JSONEncoder().encode(settings)
        let request = makeRequest(path: "/auth/notifications", method: "PUT", body: body)
        try await executeNoContent(request)
    }

    // MARK: - Sessions Endpoints

    struct SessionsWrapper: Decodable {
        let sessions: [Session]
    }

    func getSessions(status: String? = nil) async throws -> [Session] {
        var queryItems: [URLQueryItem]? = nil
        if let status {
            queryItems = [URLQueryItem(name: "status", value: status)]
        }
        let request = makeRequest(path: "/sessions", queryItems: queryItems)
        let wrapper: SessionsWrapper = try await execute(request)
        return wrapper.sessions
    }

    func getSession(key: String) async throws -> Session {
        let request = makeRequest(path: "/sessions/\(key)")
        return try await execute(request)
    }

    struct CreateSessionRequest: Encodable {
        let model: String
        let mode: String
        let projectPath: String?

        enum CodingKeys: String, CodingKey {
            case model, mode
            case projectPath = "project_path"
        }
    }

    struct CreateSessionResponse: Decodable {
        let sessionKey: String
        let name: String
        let mode: String?
    }

    func createSession(model: String, mode: String, projectPath: String?) async throws -> Session {
        let reqBody = CreateSessionRequest(model: model, mode: mode, projectPath: projectPath)
        let body = try JSONEncoder().encode(reqBody)
        let request = makeRequest(path: "/sessions", method: "POST", body: body)
        let response: CreateSessionResponse = try await execute(request)
        return Session(
            sessionKey: response.sessionKey,
            name: response.name,
            status: "idle",
            model: model,
            projectPath: projectPath,
            claudeSessionId: nil,
            mode: response.mode ?? mode
        )
    }

    func deleteSession(key: String) async throws {
        let request = makeRequest(path: "/sessions/\(key)", method: "DELETE")
        try await executeNoContent(request)
    }

    func cancelSession(key: String) async throws {
        let request = makeRequest(path: "/sessions/\(key)/cancel", method: "POST")
        try await executeNoContent(request)
    }

    struct MessageHistoryResponse: Decodable {
        let messages: [Message]
    }

    func getMessageHistory(sessionKey: String, limit: Int = 50, offset: Int = 0) async throws -> [Message] {
        let queryItems = [
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "offset", value: "\(offset)")
        ]
        let request = makeRequest(path: "/sessions/\(sessionKey)/history", queryItems: queryItems)
        let response: MessageHistoryResponse = try await execute(request)
        return response.messages
    }

    func sendMessage(sessionKey: String, content: String, attachments: [(data: Data, filename: String, mimeType: String)]) async throws -> Message {
        let boundary = UUID().uuidString
        var bodyData = Data()

        // Add content field
        bodyData.append("--\(boundary)\r\n".data(using: .utf8)!)
        bodyData.append("Content-Disposition: form-data; name=\"content\"\r\n\r\n".data(using: .utf8)!)
        bodyData.append("\(content)\r\n".data(using: .utf8)!)

        // Add file attachments
        for attachment in attachments {
            bodyData.append("--\(boundary)\r\n".data(using: .utf8)!)
            bodyData.append("Content-Disposition: form-data; name=\"files\"; filename=\"\(attachment.filename)\"\r\n".data(using: .utf8)!)
            bodyData.append("Content-Type: \(attachment.mimeType)\r\n\r\n".data(using: .utf8)!)
            bodyData.append(attachment.data)
            bodyData.append("\r\n".data(using: .utf8)!)
        }

        bodyData.append("--\(boundary)--\r\n".data(using: .utf8)!)

        var request = makeRequest(path: "/sessions/\(sessionKey)/messages", method: "POST")
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        request.httpBody = bodyData

        return try await execute(request)
    }

    // MARK: - SSE Streaming

    func sessionEventsURL() -> URL? {
        guard let token = accessToken else { return nil }
        return URL(string: "\(baseURL)/sessions/events?token=\(token)")
    }

    func pipelineEventsURL() -> URL? {
        guard let token = accessToken else { return nil }
        return URL(string: "\(baseURL)/pipelines/events?token=\(token)")
    }

    // MARK: - Pipelines Endpoints

    struct PipelinesWrapper: Decodable {
        let pipelines: [Pipeline]
    }

    func getPipelines() async throws -> [Pipeline] {
        let request = makeRequest(path: "/pipelines")
        let wrapper: PipelinesWrapper = try await execute(request)
        return wrapper.pipelines
    }

    struct CreatePipelineRequest: Encodable {
        let repoPath: String
        let issueNumber: Int?
        let taskDescription: String?
        let model: String?
        let templateId: Int?

        enum CodingKeys: String, CodingKey {
            case repoPath = "repo_path"
            case issueNumber = "issue_number"
            case taskDescription = "task_description"
            case model
            case templateId = "template_id"
        }
    }

    struct CreatePipelineResponse: Decodable {
        let pipelineKey: String
        let status: String
    }

    func createPipeline(repoPath: String, issueNumber: Int?, taskDescription: String?, model: String?, templateId: Int?) async throws -> Pipeline {
        let reqBody = CreatePipelineRequest(repoPath: repoPath, issueNumber: issueNumber, taskDescription: taskDescription, model: model, templateId: templateId)
        let encoder = JSONEncoder()
        let body = try encoder.encode(reqBody)
        let request = makeRequest(path: "/pipelines", method: "POST", body: body)
        let response: CreatePipelineResponse = try await execute(request)
        return Pipeline(
            pipelineKey: response.pipelineKey,
            repoPath: repoPath,
            issueNumber: issueNumber,
            issueTitle: nil,
            taskDescription: taskDescription,
            status: response.status,
            plan: nil,
            branch: nil,
            prNumber: nil,
            prUrl: nil,
            error: nil,
            reviewRound: 0,
            model: model ?? "sonnet",
            totalCostUsd: 0,
            templateId: templateId,
            templateName: nil,
            createdAt: Date(),
            updatedAt: Date()
        )
    }

    func cancelPipeline(key: String) async throws {
        let request = makeRequest(path: "/pipelines/\(key)/cancel", method: "POST")
        try await executeNoContent(request)
    }

    func deletePipeline(key: String) async throws {
        let request = makeRequest(path: "/pipelines/\(key)", method: "DELETE")
        try await executeNoContent(request)
    }

    func getMergeStatus(key: String) async throws -> MergeStatus {
        let request = makeRequest(path: "/pipelines/\(key)/merge-status")
        return try await execute(request)
    }

    func mergePipeline(key: String) async throws {
        let request = makeRequest(path: "/pipelines/\(key)/merge", method: "POST")
        try await executeNoContent(request)
    }

    // MARK: - Templates Endpoints

    func getTemplates() async throws -> [PipelineTemplate] {
        let request = makeRequest(path: "/pipeline-templates")
        return try await execute(request)
    }

    func getTemplate(id: Int) async throws -> PipelineTemplate {
        let request = makeRequest(path: "/pipeline-templates/\(id)")
        return try await execute(request)
    }

    // MARK: - Repos Endpoints

    struct ReposWrapper: Decodable {
        let repos: [Repository]
    }

    func getRepos() async throws -> [Repository] {
        let request = makeRequest(path: "/repos")
        let wrapper: ReposWrapper = try await execute(request)
        return wrapper.repos
    }

    struct IssuesResponse: Decodable {
        let issues: [Issue]
        let hasMore: Bool?
        let endCursor: String?

        var cursor: String? { endCursor }
    }

    func getIssues(repoPath: String, perPage: Int = 30, cursor: String? = nil) async throws -> IssuesResponse {
        var queryItems = [
            URLQueryItem(name: "repo_path", value: repoPath),
            URLQueryItem(name: "per_page", value: "\(perPage)")
        ]
        if let cursor {
            queryItems.append(URLQueryItem(name: "cursor", value: cursor))
        }
        let request = makeRequest(path: "/repos/issues", queryItems: queryItems)
        return try await execute(request)
    }

    func getIssue(repoPath: String, issueNumber: Int) async throws -> Issue {
        let queryItems = [
            URLQueryItem(name: "repo_path", value: repoPath),
            URLQueryItem(name: "issue_number", value: "\(issueNumber)")
        ]
        let request = makeRequest(path: "/repos/issue", queryItems: queryItems)
        return try await execute(request)
    }

    struct RoleResponse: Decodable {
        let name: String
        let title: String
    }

    func getRoles() async throws -> [RoleResponse] {
        let request = makeRequest(path: "/roles")
        struct RolesWrapper: Decodable {
            let roles: [String: RoleDetail]
            struct RoleDetail: Decodable {
                let title: String
            }
        }
        let wrapper: RolesWrapper = try await execute(request)
        return wrapper.roles.map { RoleResponse(name: $0.key, title: $0.value.title) }
            .sorted { $0.name < $1.name }
    }
}
