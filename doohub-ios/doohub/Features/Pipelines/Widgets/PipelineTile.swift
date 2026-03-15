import SwiftUI

struct PipelineTile: View {
    let pipeline: Pipeline
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        SolidCard {
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    // Title: issue title or repo name
                    Text(pipeline.issueTitle ?? pipeline.repoPath.components(separatedBy: "/").last ?? pipeline.repoPath)
                        .font(.headline)
                        .foregroundColor(AppTheme.textPrimaryColor(for: colorScheme))
                        .lineLimit(1)

                    HStack(spacing: 8) {
                        Label(pipeline.model.capitalized, systemImage: "cpu")
                            .font(.caption)
                            .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))

                        Text(pipeline.repoPath.components(separatedBy: "/").last ?? pipeline.repoPath)
                            .font(.caption)
                            .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                            .lineLimit(1)

                        if let templateName = pipeline.templateName {
                            Text(templateName)
                                .font(.caption)
                                .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                                .lineLimit(1)
                        }
                    }
                }

                Spacer()

                StatusBadge(status: pipeline.status)
            }
            .padding(16)
        }
    }
}
