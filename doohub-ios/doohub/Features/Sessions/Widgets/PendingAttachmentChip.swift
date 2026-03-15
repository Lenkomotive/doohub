import SwiftUI

struct PendingAttachmentChip: View {
    let attachment: SessionsStore.PendingAttachment
    let onRemove: () -> Void
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "doc")
                .font(.caption)

            VStack(alignment: .leading, spacing: 1) {
                Text(attachment.filename)
                    .font(.caption2)
                    .fontWeight(.medium)
                    .lineLimit(1)

                Text(attachment.fileSizeFormatted)
                    .font(.caption2)
                    .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
            }

            Button {
                onRemove()
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.caption)
                    .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(AppTheme.cardColor(for: colorScheme))
        .clipShape(Capsule())
    }
}
