import SwiftUI

struct LoginScreen: View {
    @EnvironmentObject private var authStore: AuthStore
    @Environment(\.colorScheme) private var colorScheme

    @State private var username = ""
    @State private var password = ""

    private var isLoading: Bool {
        authStore.state == .loading
    }

    private var errorMessage: String? {
        if case .loginFailure(let message) = authStore.state {
            return message
        }
        return nil
    }

    var body: some View {
        ZStack {
            MeshBackground()

            VStack(spacing: 32) {
                Spacer()

                // Logo
                VStack(spacing: 8) {
                    Image(systemName: "circle.hexagongrid.fill")
                        .font(.system(size: 64))
                        .foregroundColor(AppTheme.primaryColor(for: colorScheme))

                    Text("DooHub")
                        .font(.largeTitle)
                        .fontWeight(.bold)
                        .foregroundColor(AppTheme.textPrimaryColor(for: colorScheme))
                }

                // Form
                VStack(spacing: 16) {
                    TextField("Username", text: $username)
                        .textFieldStyle(.roundedBorder)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .disabled(isLoading)

                    SecureField("Password", text: $password)
                        .textFieldStyle(.roundedBorder)
                        .disabled(isLoading)

                    if let errorMessage {
                        Text(errorMessage)
                            .font(.caption)
                            .foregroundColor(AppColors.error)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }

                    Button {
                        Task {
                            await authStore.login(username: username, password: password)
                        }
                    } label: {
                        Group {
                            if isLoading {
                                ProgressView()
                                    .tint(.white)
                            } else {
                                Text("Sign In")
                                    .fontWeight(.semibold)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(AppTheme.primaryColor(for: colorScheme))
                        .foregroundColor(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .disabled(username.isEmpty || password.isEmpty || isLoading)
                    .opacity(username.isEmpty || password.isEmpty ? 0.6 : 1.0)
                }
                .padding(.horizontal, 32)

                Spacer()
                Spacer()
            }
        }
    }
}
