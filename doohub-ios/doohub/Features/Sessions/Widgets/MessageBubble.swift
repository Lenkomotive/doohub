import SwiftUI
import MarkdownUI

struct MessageBubble: View {
    let message: Message
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.openURL) private var openURL

    var body: some View {
        HStack {
            if message.isUser { Spacer(minLength: 60) }

            VStack(alignment: message.isUser ? .trailing : .leading, spacing: 6) {
                if message.isUser {
                    // User message with link detection
                    Text(attributedContent)
                        .textSelection(.enabled)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(AppTheme.primaryColor(for: colorScheme))
                        .foregroundColor(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 18))
                } else {
                    // Assistant message with markdown
                    Markdown(message.content)
                        .markdownTheme(.gitHub)
                        .textSelection(.enabled)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(AppTheme.cardColor(for: colorScheme))
                        .clipShape(RoundedRectangle(cornerRadius: 18))
                }

                // Attachments
                if let attachments = message.attachments, !attachments.isEmpty {
                    ForEach(attachments) { attachment in
                        AttachmentCard(attachment: attachment)
                    }
                }

                // Timestamp
                Text(message.createdAt, style: .time)
                    .font(.caption2)
                    .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
            }

            if message.isAssistant { Spacer(minLength: 60) }
        }
    }

    private var attributedContent: AttributedString {
        var attributed = AttributedString(message.content)

        // Simple URL detection
        let urlPattern = try? NSRegularExpression(pattern: "https?://[^\\s)>\\]]+", options: [])
        let nsString = message.content as NSString
        let results = urlPattern?.matches(in: message.content, range: NSRange(location: 0, length: nsString.length)) ?? []

        for match in results {
            if let range = Range(match.range, in: message.content),
               let attrRange = Range(range, in: attributed),
               let url = URL(string: String(message.content[range]).trimmingCharacters(in: CharacterSet(charactersIn: ".,;:!?)>]'\""))) {
                attributed[attrRange].link = url
                attributed[attrRange].foregroundColor = .cyan
            }
        }

        return attributed
    }
}
