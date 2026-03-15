import SwiftUI

struct HomeShell: View {
    @EnvironmentObject private var router: AppRouter
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        TabView(selection: $router.selectedTab) {
            NavigationStack(path: $router.path) {
                SessionsScreen()
                    .navigationDestination(for: Route.self) { route in
                        destinationView(for: route)
                    }
            }
            .tabItem {
                Label(AppRouter.Tab.sessions.title, systemImage: AppRouter.Tab.sessions.icon)
            }
            .tag(AppRouter.Tab.sessions)

            NavigationStack {
                PipelinesScreen()
                    .navigationDestination(for: Route.self) { route in
                        destinationView(for: route)
                    }
            }
            .tabItem {
                Label(AppRouter.Tab.pipelines.title, systemImage: AppRouter.Tab.pipelines.icon)
            }
            .tag(AppRouter.Tab.pipelines)

            NavigationStack {
                TemplatesScreen()
                    .navigationDestination(for: Route.self) { route in
                        destinationView(for: route)
                    }
            }
            .tabItem {
                Label(AppRouter.Tab.templates.title, systemImage: AppRouter.Tab.templates.icon)
            }
            .tag(AppRouter.Tab.templates)

            NavigationStack {
                SettingsScreen()
            }
            .tabItem {
                Label(AppRouter.Tab.settings.title, systemImage: AppRouter.Tab.settings.icon)
            }
            .tag(AppRouter.Tab.settings)
        }
        .tint(AppTheme.primaryColor(for: colorScheme))
    }

    @ViewBuilder
    private func destinationView(for route: Route) -> some View {
        switch route {
        case .chat(let sessionKey):
            ChatScreen(sessionKey: sessionKey)
        case .pipelineDetail(let pipelineKey):
            PipelineDetailScreen(pipelineKey: pipelineKey)
        case .templateDetail(let templateId):
            TemplateDetailScreen(templateId: templateId)
        default:
            EmptyView()
        }
    }
}
