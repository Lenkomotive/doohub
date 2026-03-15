import SwiftUI

struct CreatePipelineSheet: View {
    @EnvironmentObject private var pipelinesStore: PipelinesStore
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme

    @State private var repos: [Repository] = []
    @State private var templates: [PipelineTemplate] = []
    @State private var issues: [Issue] = []
    @State private var selectedRepo: Repository?
    @State private var selectedModel = "sonnet"
    @State private var selectedTemplate: PipelineTemplate?
    @State private var selectedIssueNumbers: Set<Int> = []
    @State private var issueCursor: String?
    @State private var isLoadingIssues = false
    @State private var isCreating = false

    private let models = ["opus", "sonnet", "haiku"]
    private let apiService = APIService()

    // Issues that already have active pipelines
    private var activeIssueNumbers: Set<Int> {
        guard let repo = selectedRepo else { return [] }
        return Set(
            pipelinesStore.pipelines
                .filter { $0.repoPath == repo.path && $0.isActive }
                .compactMap { $0.issueNumber }
        )
    }

    var body: some View {
        NavigationStack {
            AppSheet(title: "New Pipeline", systemImage: "plus.diamond") {
                ScrollView {
                    VStack(spacing: 20) {
                        // Repo picker
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Repository")
                                .font(.subheadline)
                                .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))

                            Picker("Repository", selection: $selectedRepo) {
                                Text("Select a repository").tag(nil as Repository?)
                                ForEach(repos) { repo in
                                    Text(repo.displayName).tag(repo as Repository?)
                                }
                            }
                            .pickerStyle(.menu)
                        }

                        // Template picker (optional)
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Template (optional)")
                                .font(.subheadline)
                                .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))

                            Picker("Template", selection: $selectedTemplate) {
                                Text("None").tag(nil as PipelineTemplate?)
                                ForEach(templates) { template in
                                    Text(template.name).tag(template as PipelineTemplate?)
                                }
                            }
                            .pickerStyle(.menu)
                        }

                        // Model picker (only if no template)
                        if selectedTemplate == nil {
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
                        }

                        // Issues list
                        if selectedRepo != nil {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Issues")
                                    .font(.subheadline)
                                    .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))

                                if isLoadingIssues && issues.isEmpty {
                                    ProgressView()
                                        .frame(maxWidth: .infinity, minHeight: 100)
                                } else if issues.isEmpty {
                                    Text("No open issues")
                                        .font(.subheadline)
                                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                                        .frame(maxWidth: .infinity, minHeight: 60)
                                } else {
                                    LazyVStack(spacing: 6) {
                                        ForEach(issues) { issue in
                                            IssueRow(
                                                issue: issue,
                                                isSelected: selectedIssueNumbers.contains(issue.number),
                                                isActive: activeIssueNumbers.contains(issue.number),
                                                onTap: {
                                                    if !activeIssueNumbers.contains(issue.number) {
                                                        if selectedIssueNumbers.contains(issue.number) {
                                                            selectedIssueNumbers.remove(issue.number)
                                                        } else {
                                                            selectedIssueNumbers.insert(issue.number)
                                                        }
                                                    }
                                                },
                                                onLongPress: {
                                                    // Show issue detail dialog handled via state
                                                }
                                            )
                                        }

                                        if issueCursor != nil {
                                            Button("Load More") {
                                                Task { await loadMoreIssues() }
                                            }
                                            .frame(maxWidth: .infinity)
                                            .padding(.vertical, 8)
                                        }
                                    }
                                }
                            }
                        }

                        // Create button
                        Button {
                            Task { await createPipelines() }
                        } label: {
                            Group {
                                if isCreating {
                                    ProgressView().tint(.white)
                                } else {
                                    Text(selectedIssueNumbers.count > 1
                                         ? "Create \(selectedIssueNumbers.count) Pipelines"
                                         : "Create Pipeline")
                                        .fontWeight(.semibold)
                                }
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .background(AppTheme.primaryColor(for: colorScheme))
                            .foregroundColor(.white)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                        .disabled(selectedRepo == nil || selectedIssueNumbers.isEmpty || isCreating)
                        .opacity(selectedRepo == nil || selectedIssueNumbers.isEmpty ? 0.6 : 1.0)
                    }
                    .padding(20)
                }
            }
        }
        .presentationDetents([.large])
        .onChange(of: selectedRepo) { _ in
            issues = []
            selectedIssueNumbers = []
            issueCursor = nil
            if selectedRepo != nil {
                Task { await loadIssues() }
            }
        }
        .task {
            await loadReposAndTemplates()
        }
    }

    private func loadReposAndTemplates() async {
        do {
            async let reposTask = apiService.getRepos()
            async let templatesTask = apiService.getTemplates()
            repos = try await reposTask
            templates = try await templatesTask
        } catch {
            // Silent
        }
    }

    private func loadIssues() async {
        guard let repo = selectedRepo else { return }
        isLoadingIssues = true
        do {
            let response = try await apiService.getIssues(repoPath: repo.path)
            issues = response.issues
            issueCursor = response.cursor
        } catch {
            // Silent
        }
        isLoadingIssues = false
    }

    private func loadMoreIssues() async {
        guard let repo = selectedRepo, let cursor = issueCursor else { return }
        isLoadingIssues = true
        do {
            let response = try await apiService.getIssues(repoPath: repo.path, cursor: cursor)
            issues.append(contentsOf: response.issues)
            issueCursor = response.cursor
        } catch {
            // Silent
        }
        isLoadingIssues = false
    }

    private func createPipelines() async {
        guard let repo = selectedRepo else { return }
        isCreating = true

        for issueNumber in selectedIssueNumbers {
            let _ = await pipelinesStore.createPipeline(
                repoPath: repo.path,
                issueNumber: issueNumber,
                taskDescription: nil,
                model: selectedTemplate == nil ? selectedModel : nil,
                templateId: selectedTemplate?.id
            )
        }

        isCreating = false
        dismiss()
    }
}

struct IssueRow: View {
    let issue: Issue
    let isSelected: Bool
    let isActive: Bool
    let onTap: () -> Void
    let onLongPress: () -> Void
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 10) {
                Image(systemName: isActive ? "hourglass" : (isSelected ? "checkmark.circle.fill" : "circle"))
                    .foregroundColor(
                        isActive ? AppTheme.textSecondaryColor(for: colorScheme)
                        : isSelected ? AppTheme.primaryColor(for: colorScheme)
                        : AppTheme.textSecondaryColor(for: colorScheme)
                    )

                VStack(alignment: .leading, spacing: 2) {
                    Text("#\(issue.number) \(issue.title)")
                        .font(.subheadline)
                        .foregroundColor(
                            isActive ? AppTheme.textSecondaryColor(for: colorScheme)
                            : AppTheme.textPrimaryColor(for: colorScheme)
                        )
                        .lineLimit(2)

                    if let labels = issue.labels, !labels.isEmpty {
                        HStack(spacing: 4) {
                            ForEach(labels, id: \.name) { label in
                                Text(label.name)
                                    .font(.caption2)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(labelColor(label).opacity(0.2))
                                    .foregroundColor(labelColor(label))
                                    .clipShape(Capsule())
                            }
                        }
                    }
                }

                Spacer()
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
            .background(isSelected ? AppTheme.primaryColor(for: colorScheme).opacity(0.08) : Color.clear)
            .clipShape(RoundedRectangle(cornerRadius: 10))
        }
        .disabled(isActive)
    }

    private func labelColor(_ label: IssueLabel) -> Color {
        guard let hex = label.color, !hex.isEmpty else {
            return AppTheme.primaryColor(for: colorScheme)
        }
        let cleanHex = hex.hasPrefix("#") ? String(hex.dropFirst()) : hex
        guard let value = UInt(cleanHex, radix: 16) else {
            return AppTheme.primaryColor(for: colorScheme)
        }
        return Color(hex: value)
    }
}
