import SwiftUI

struct SessionTile: View {
    let session: Session
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        SolidCard {
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(session.name)
                        .font(.headline)
                        .foregroundColor(AppTheme.textPrimaryColor(for: colorScheme))
                        .lineLimit(1)

                    HStack(spacing: 8) {
                        Label(session.model.capitalized, systemImage: "cpu")
                            .font(.caption)
                            .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))

                        if let path = session.projectPath, !path.isEmpty {
                            Text(path.components(separatedBy: "/").last ?? path)
                                .font(.caption)
                                .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                                .lineLimit(1)
                        }
                    }
                }

                Spacer()

                StatusBadge(
                    status: session.status,
                    color: AppTheme.sessionStatusColor(for: session.status)
                )
            }
            .padding(16)
        }
    }
}
