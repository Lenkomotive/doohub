import SwiftUI

struct SettingsScreen: View {
    @EnvironmentObject private var settingsStore: SettingsStore
    @EnvironmentObject private var notificationStore: NotificationSettingsStore
    @EnvironmentObject private var authStore: AuthStore
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        List {
            Section("Appearance") {
                Toggle("Dark Mode", isOn: Binding(
                    get: { settingsStore.isDarkMode },
                    set: { _ in settingsStore.toggleDarkMode() }
                ))
            }

            Section("Notifications") {
                Toggle("Session Replies", isOn: Binding(
                    get: { notificationStore.sessions },
                    set: { _ in
                        Task { await notificationStore.toggleSessions() }
                    }
                ))

                Toggle("Pipeline Updates", isOn: Binding(
                    get: { notificationStore.pipelines },
                    set: { _ in
                        Task { await notificationStore.togglePipelines() }
                    }
                ))
            }

            Section("Account") {
                if case .authenticated(let username) = authStore.state {
                    HStack {
                        Text("Signed in as")
                            .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                        Spacer()
                        Text(username)
                            .fontWeight(.medium)
                    }
                }

                Button(role: .destructive) {
                    Task { await authStore.logout() }
                } label: {
                    HStack {
                        Spacer()
                        Text("Sign Out")
                        Spacer()
                    }
                }
            }
        }
        .navigationTitle("Settings")
        .task {
            await notificationStore.load()
        }
    }
}
