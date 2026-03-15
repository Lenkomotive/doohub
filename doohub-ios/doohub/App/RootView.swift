import SwiftUI

struct RootView: View {
    @EnvironmentObject private var authStore: AuthStore

    var body: some View {
        Group {
            switch authStore.state {
            case .initial, .loading:
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(MeshBackground())
            case .authenticated:
                HomeShell()
            case .unauthenticated, .loginFailure:
                LoginScreen()
            }
        }
        .animation(.easeInOut, value: authStore.state)
    }
}
