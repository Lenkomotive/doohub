import SwiftUI
import FirebaseCore
import FirebaseMessaging

@main
struct DooHubApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var delegate
    @StateObject private var dependencies = AppDependencies()
    @StateObject private var router = AppRouter()

    var body: some Scene {
        WindowGroup {
            AppContent()
                .environmentObject(dependencies)
                .environmentObject(dependencies.authStore)
                .environmentObject(dependencies.sessionsStore)
                .environmentObject(dependencies.pipelinesStore)
                .environmentObject(dependencies.templatesStore)
                .environmentObject(dependencies.settingsStore)
                .environmentObject(dependencies.notificationSettingsStore)
                .environmentObject(router)
                .task {
                    await dependencies.initialize()
                }
        }
    }
}

private struct AppContent: View {
    @EnvironmentObject private var settings: SettingsStore

    var body: some View {
        RootView()
            .preferredColorScheme(settings.resolvedColorScheme)
    }
}
