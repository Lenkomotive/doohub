import SwiftUI

enum Route: Hashable {
    case login
    case sessions
    case chat(sessionKey: String)
    case pipelines
    case pipelineDetail(pipelineKey: String)
    case templates
    case templateDetail(templateId: Int)
    case settings
}

class AppRouter: ObservableObject {
    @Published var path = NavigationPath()
    @Published var selectedTab: Tab = .sessions

    enum Tab: Int, CaseIterable {
        case sessions = 0
        case pipelines = 1
        case templates = 2
        case settings = 3

        var title: String {
            switch self {
            case .sessions: return "Sessions"
            case .pipelines: return "Pipelines"
            case .templates: return "Templates"
            case .settings: return "Settings"
            }
        }

        var icon: String {
            switch self {
            case .sessions: return "bubble.left.and.bubble.right"
            case .pipelines: return "point.3.connected.trianglepath.dotted"
            case .templates: return "rectangle.3.group"
            case .settings: return "gearshape"
            }
        }
    }

    func navigate(to route: Route) {
        path.append(route)
    }

    func pop() {
        if !path.isEmpty {
            path.removeLast()
        }
    }

    func popToRoot() {
        path = NavigationPath()
    }
}
