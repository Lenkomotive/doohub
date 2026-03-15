import SwiftUI

@MainActor
class NotificationSettingsStore: ObservableObject {
    @Published var sessions: Bool = true
    @Published var pipelines: Bool = true
    @Published var isLoading: Bool = false

    private let apiService: APIService

    init(apiService: APIService) {
        self.apiService = apiService
    }

    func load() async {
        isLoading = true
        do {
            let settings = try await apiService.getNotificationSettings()
            sessions = settings.sessions
            pipelines = settings.pipelines
        } catch {
            // Use defaults
        }
        isLoading = false
    }

    func toggleSessions() async {
        let previous = sessions
        sessions.toggle()
        do {
            try await apiService.updateNotificationSettings(
                APIService.NotificationSettings(sessions: sessions, pipelines: pipelines)
            )
        } catch {
            sessions = previous
        }
    }

    func togglePipelines() async {
        let previous = pipelines
        pipelines.toggle()
        do {
            try await apiService.updateNotificationSettings(
                APIService.NotificationSettings(sessions: sessions, pipelines: pipelines)
            )
        } catch {
            pipelines = previous
        }
    }
}
