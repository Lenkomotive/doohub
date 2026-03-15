import SwiftUI

struct CreateSessionSheet: View {
    @EnvironmentObject private var sessionsStore: SessionsStore
    @EnvironmentObject private var router: AppRouter
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme

    @State private var selectedModel = "sonnet"
    @State private var selectedMode = "general"
    @State private var projectPath = ""
    @State private var modes: [String] = ["general"]
    @State private var isCreating = false

    private let models = ["opus", "sonnet", "haiku"]

    private let apiService = APIService()

    var body: some View {
        AppSheet(title: "New Session", systemImage: "plus.bubble") {
            VStack(spacing: 20) {
                // Model picker
                VStack(alignment: .leading, spacing: 6) {
                    Text("Model")
                        .font(.subheadline)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))

                    Picker("Model", selection: $selectedModel) {
                        ForEach(models, id: \.self) { model in
                            Text(model.capitalized).tag(model)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                // Mode picker
                VStack(alignment: .leading, spacing: 6) {
                    Text("Mode")
                        .font(.subheadline)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))

                    Picker("Mode", selection: $selectedMode) {
                        ForEach(modes, id: \.self) { mode in
                            Text(mode.capitalized).tag(mode)
                        }
                    }
                    .pickerStyle(.menu)
                }

                // Project path
                VStack(alignment: .leading, spacing: 6) {
                    Text("Project Path (optional)")
                        .font(.subheadline)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))

                    TextField("e.g. /home/user/project", text: $projectPath)
                        .textFieldStyle(.roundedBorder)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                }

                Button {
                    Task {
                        isCreating = true
                        let path = projectPath.isEmpty ? nil : projectPath
                        if let session = await sessionsStore.createSession(
                            model: selectedModel,
                            mode: selectedMode,
                            projectPath: path
                        ) {
                            dismiss()
                            router.navigate(to: .chat(sessionKey: session.sessionKey))
                        }
                        isCreating = false
                    }
                } label: {
                    Group {
                        if isCreating {
                            ProgressView().tint(.white)
                        } else {
                            Text("Create Session")
                                .fontWeight(.semibold)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(AppTheme.primaryColor(for: colorScheme))
                    .foregroundColor(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .disabled(isCreating)

                Spacer()
            }
            .padding(20)
        }
        .presentationDetents([.medium])
        .task {
            do {
                let roles = try await apiService.getRoles()
                modes = roles.map { $0.name }
                if !modes.contains(selectedMode) {
                    selectedMode = modes.first ?? "general"
                }
            } catch {
                // Use default
            }
        }
    }
}
