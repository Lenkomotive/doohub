import SwiftUI
import MarkdownUI

struct PipelineDetailScreen: View {
    let pipelineKey: String

    @EnvironmentObject private var pipelinesStore: PipelinesStore
    @EnvironmentObject private var sessionsStore: SessionsStore
    @EnvironmentObject private var router: AppRouter
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.openURL) private var openURL

    private var pipeline: Pipeline? {
        pipelinesStore.pipelines.first { $0.pipelineKey == pipelineKey }
    }

    private var mergeStatus: MergeStatus? {
        pipelinesStore.mergeStatuses[pipelineKey]
    }

    private var isMerging: Bool {
        pipelinesStore.mergingKeys.contains(pipelineKey)
    }

    var body: some View {
        ScrollView {
            if let pipeline {
                VStack(spacing: 16) {
                    // Status card
                    StatusCard(pipeline: pipeline)

                    // Info card
                    InfoCard(pipeline: pipeline)

                    // Plan card
                    if let plan = pipeline.plan, !plan.isEmpty {
                        PlanCard(plan: plan)
                    }

                    // PR card
                    if let prUrl = pipeline.prUrl {
                        PRCard(prUrl: prUrl, prNumber: pipeline.prNumber)
                    }

                    // Merge card
                    if pipeline.status == "done", let status = mergeStatus {
                        MergeCard(
                            mergeStatus: status,
                            isMerging: isMerging,
                            onMerge: {
                                Task { await pipelinesStore.mergePipeline(key: pipelineKey) }
                            },
                            onResolveConflicts: {
                                Task {
                                    if let session = await sessionsStore.createSession(
                                        model: pipeline.model,
                                        mode: "general",
                                        projectPath: pipeline.repoPath
                                    ) {
                                        router.selectedTab = .sessions
                                        router.navigate(to: .chat(sessionKey: session.sessionKey))
                                    }
                                }
                            }
                        )
                    }

                    // Error card
                    if let error = pipeline.error, !error.isEmpty {
                        ErrorCard(error: error)
                    }

                    // Action buttons
                    if pipeline.isActive {
                        Button(role: .destructive) {
                            Task { await pipelinesStore.cancelPipeline(key: pipelineKey) }
                        } label: {
                            Label("Cancel Pipeline", systemImage: "stop.circle")
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 12)
                        }
                        .buttonStyle(.bordered)
                        .tint(.red)
                    }
                }
                .padding(16)
            } else {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .background(MeshBackground())
        .navigationTitle(pipeline?.issueTitle ?? "Pipeline")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button(role: .destructive) {
                    Task {
                        await pipelinesStore.deletePipeline(key: pipelineKey)
                    }
                } label: {
                    Image(systemName: "trash")
                }
            }
        }
        .task {
            if let pipeline, pipeline.status == "done" {
                await pipelinesStore.checkMergeStatus(key: pipelineKey)
            }
        }
    }
}

// MARK: - Subviews

private struct StatusCard: View {
    let pipeline: Pipeline
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        SolidCard {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Status")
                        .font(.subheadline)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                    Spacer()
                    StatusBadge(status: pipeline.status)
                }

                Divider()

                HStack {
                    Text("Created")
                        .font(.caption)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                    Spacer()
                    Text(pipeline.createdAt, style: .relative)
                        .font(.caption)
                }

                HStack {
                    Text("Updated")
                        .font(.caption)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                    Spacer()
                    Text(pipeline.updatedAt, style: .relative)
                        .font(.caption)
                }

                if pipeline.reviewRound > 0 {
                    HStack {
                        Text("Review Rounds")
                            .font(.caption)
                            .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                        Spacer()
                        Text("\(pipeline.reviewRound)")
                            .font(.caption)
                    }
                }
            }
            .padding(16)
        }
    }
}

private struct InfoCard: View {
    let pipeline: Pipeline
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        SolidCard {
            VStack(alignment: .leading, spacing: 8) {
                infoRow("Repository", value: pipeline.repoPath)
                infoRow("Model", value: pipeline.model.capitalized)

                if let templateName = pipeline.templateName {
                    infoRow("Template", value: templateName)
                }

                if let issueNumber = pipeline.issueNumber {
                    infoRow("Issue", value: "#\(issueNumber)")
                }

                if let branch = pipeline.branch {
                    infoRow("Branch", value: branch)
                }

                infoRow("Cost", value: String(format: "$%.4f", pipeline.totalCostUsd))
            }
            .padding(16)
        }
    }

    private func infoRow(_ label: String, value: String) -> some View {
        HStack {
            Text(label)
                .font(.caption)
                .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
            Spacer()
            Text(value)
                .font(.caption)
                .fontWeight(.medium)
        }
    }
}

private struct PlanCard: View {
    let plan: String
    @State private var isExpanded = false
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        SolidCard {
            VStack(alignment: .leading, spacing: 8) {
                Button {
                    withAnimation { isExpanded.toggle() }
                } label: {
                    HStack {
                        Text("Plan")
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(AppTheme.textPrimaryColor(for: colorScheme))
                        Spacer()
                        Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                            .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                    }
                }

                if isExpanded {
                    Divider()
                    Markdown(plan)
                        .markdownTheme(.gitHub)
                        .textSelection(.enabled)
                }
            }
            .padding(16)
        }
    }
}

private struct PRCard: View {
    let prUrl: String
    let prNumber: Int?
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.openURL) private var openURL

    var body: some View {
        SolidCard {
            Button {
                if let url = URL(string: prUrl) {
                    openURL(url)
                }
            } label: {
                HStack {
                    Image(systemName: "link")
                        .foregroundColor(AppTheme.primaryColor(for: colorScheme))

                    VStack(alignment: .leading, spacing: 2) {
                        Text("Pull Request")
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(AppTheme.textPrimaryColor(for: colorScheme))

                        Text(prNumber != nil ? "PR #\(prNumber!)" : prUrl)
                            .font(.caption)
                            .foregroundColor(AppTheme.primaryColor(for: colorScheme))
                            .lineLimit(1)
                    }

                    Spacer()

                    Image(systemName: "arrow.up.right.square")
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                }
                .padding(16)
            }
        }
    }
}

private struct MergeCard: View {
    let mergeStatus: MergeStatus
    let isMerging: Bool
    let onMerge: () -> Void
    let onResolveConflicts: () -> Void
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        SolidCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text("Merge Status")
                        .font(.subheadline)
                        .fontWeight(.medium)
                    Spacer()
                    mergeStatusBadge
                }

                if mergeStatus.alreadyMerged {
                    Label("Already merged", systemImage: "checkmark.circle.fill")
                        .font(.subheadline)
                        .foregroundColor(AppColors.success)
                } else if mergeStatus.closed {
                    Label("PR is closed", systemImage: "xmark.circle.fill")
                        .font(.subheadline)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                } else if mergeStatus.hasConflicts {
                    Label("Has merge conflicts", systemImage: "exclamationmark.triangle.fill")
                        .font(.subheadline)
                        .foregroundColor(AppColors.warning)

                    Button {
                        onResolveConflicts()
                    } label: {
                        Text("Resolve Conflicts")
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 10)
                    }
                    .buttonStyle(.bordered)
                    .tint(AppColors.warning)
                } else if mergeStatus.mergeable {
                    Button {
                        onMerge()
                    } label: {
                        Group {
                            if isMerging {
                                ProgressView().tint(.white)
                            } else {
                                Label("Merge", systemImage: "arrow.triangle.merge")
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(AppColors.success)
                        .foregroundColor(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    }
                    .disabled(isMerging)
                } else {
                    Label("Not mergeable", systemImage: "xmark.circle")
                        .font(.subheadline)
                        .foregroundColor(AppColors.error)

                    if let error = mergeStatus.error {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                    }
                }
            }
            .padding(16)
        }
    }

    @ViewBuilder
    private var mergeStatusBadge: some View {
        if mergeStatus.alreadyMerged {
            StatusBadge(status: "merged", color: AppColors.success)
        } else if mergeStatus.hasConflicts {
            StatusBadge(status: "conflicts", color: AppColors.warning)
        } else if mergeStatus.mergeable {
            StatusBadge(status: "ready", color: AppColors.success)
        } else {
            StatusBadge(status: "blocked", color: AppColors.error)
        }
    }
}

private struct ErrorCard: View {
    let error: String
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        SolidCard {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(AppColors.error)
                    Text("Error")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(AppColors.error)
                }

                Divider()

                Markdown(error)
                    .markdownTheme(.gitHub)
                    .textSelection(.enabled)
            }
            .padding(16)
        }
    }
}
