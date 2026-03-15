import SwiftUI

struct StatusBadge: View {
    let status: String
    var color: Color? = nil

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        Text(status.capitalized)
            .font(.caption2)
            .fontWeight(.semibold)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(badgeColor.opacity(0.15))
            .foregroundColor(badgeColor)
            .clipShape(Capsule())
    }

    private var badgeColor: Color {
        if let color { return color }
        return AppTheme.pipelineStatusColor(for: status)
    }
}
