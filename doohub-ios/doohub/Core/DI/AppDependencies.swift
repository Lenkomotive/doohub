import SwiftUI

@MainActor
class AppDependencies: ObservableObject {
    let apiService: APIService
    let authStore: AuthStore
    let sessionsStore: SessionsStore
    let pipelinesStore: PipelinesStore
    let templatesStore: TemplatesStore
    let settingsStore: SettingsStore
    let notificationSettingsStore: NotificationSettingsStore

    init() {
        let api = APIService()
        self.apiService = api
        self.authStore = AuthStore(apiService: api)
        self.sessionsStore = SessionsStore(apiService: api)
        self.pipelinesStore = PipelinesStore(apiService: api)
        self.templatesStore = TemplatesStore(apiService: api)
        self.settingsStore = SettingsStore()
        self.notificationSettingsStore = NotificationSettingsStore(apiService: api)
    }

    func initialize() async {
        await authStore.checkAuth()
    }
}
