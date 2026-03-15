import SwiftUI

struct GlassCard<Content: View>: View {
    var cornerRadius: CGFloat = 16
    var isCircle: Bool = false
    var interactive: Bool = false
    @ViewBuilder let content: () -> Content

    var body: some View {
        if isCircle {
            if #available(iOS 26.0, *) {
                content()
                    .glassEffect(interactive ? .regular.interactive() : .regular, in: .circle)
            } else {
                content()
                    .background(.ultraThinMaterial)
                    .clipShape(Circle())
            }
        } else {
            if #available(iOS 26.0, *) {
                content()
                    .glassEffect(interactive ? .regular.interactive() : .regular, in: RoundedRectangle(cornerRadius: cornerRadius))
            } else {
                content()
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: cornerRadius))
            }
        }
    }
}

struct SolidCard<Content: View>: View {
    @Environment(\.colorScheme) private var colorScheme
    var cornerRadius: CGFloat = 16
    @ViewBuilder let content: () -> Content

    var body: some View {
        content()
            .background(AppTheme.cardColor(for: colorScheme))
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius))
    }
}
