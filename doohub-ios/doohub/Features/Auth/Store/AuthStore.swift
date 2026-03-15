import SwiftUI
import FirebaseMessaging

enum AuthState: Equatable {
    case initial
    case loading
    case authenticated(username: String)
    case unauthenticated
    case loginFailure(message: String)

    static func == (lhs: AuthState, rhs: AuthState) -> Bool {
        switch (lhs, rhs) {
        case (.initial, .initial), (.loading, .loading), (.unauthenticated, .unauthenticated):
            return true
        case (.authenticated(let a), .authenticated(let b)):
            return a == b
        case (.loginFailure(let a), .loginFailure(let b)):
            return a == b
        default:
            return false
        }
    }

    var isAuthenticated: Bool {
        if case .authenticated = self { return true }
        return false
    }
}

@MainActor
class AuthStore: ObservableObject {
    @Published var state: AuthState = .initial

    private let apiService: APIService

    init(apiService: APIService) {
        self.apiService = apiService
    }

    func checkAuth() async {
        let hasTokens = await apiService.hasTokens
        guard hasTokens else {
            state = .unauthenticated
            return
        }

        state = .loading
        do {
            let user = try await apiService.getMe()
            state = .authenticated(username: user.username)
            await registerFcmToken()
        } catch {
            state = .unauthenticated
        }
    }

    func login(username: String, password: String) async {
        state = .loading
        do {
            let response = try await apiService.login(username: username, password: password)
            await apiService.setTokens(access: response.accessToken, refresh: response.refreshToken)
            let user = try await apiService.getMe()
            state = .authenticated(username: user.username)
            await registerFcmToken()
        } catch let error as APIError {
            print("[Auth] Login APIError: \(error)")
            state = .loginFailure(message: error.localizedDescription)
        } catch {
            print("[Auth] Login error: \(error)")
            state = .loginFailure(message: error.localizedDescription)
        }
    }

    func logout() async {
        await apiService.clearTokens()
        state = .unauthenticated
    }

    private func registerFcmToken() async {
        do {
            if let token = Messaging.messaging().fcmToken {
                try await apiService.registerFcmToken(token)
            }
        } catch {
            // Silent failure for FCM registration
        }
    }
}
