import SwiftUI

struct AttachmentCard: View {
    let attachment: Attachment
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.openURL) private var openURL

    var body: some View {
        Button {
            if let urlString = attachment.url, let url = URL(string: urlString) {
                openURL(url)
            }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: iconName)
                    .foregroundColor(AppTheme.primaryColor(for: colorScheme))

                VStack(alignment: .leading, spacing: 2) {
                    Text(attachment.filename)
                        .font(.caption)
                        .fontWeight(.medium)
                        .foregroundColor(AppTheme.textPrimaryColor(for: colorScheme))
                        .lineLimit(1)

                    Text(attachment.fileSizeFormatted)
                        .font(.caption2)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                }

                Spacer()
            }
            .padding(10)
            .background(AppTheme.cardColor(for: colorScheme))
            .clipShape(RoundedRectangle(cornerRadius: 10))
        }
    }

    private var iconName: String {
        let ext = attachment.fileExtension.lowercased()
        switch ext {
        case "pdf": return "doc.richtext"
        case "txt", "md": return "doc.text"
        default: return "doc"
        }
    }
}
