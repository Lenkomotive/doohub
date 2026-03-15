import SwiftUI

struct LiquidGlassModifier<S: Shape>: ViewModifier {
    let shape: S
    var interactive: Bool = false

    func body(content: Content) -> some View {
        if #available(iOS 26.0, *) {
            content
                .glassEffect(interactive ? .regular.interactive() : .regular, in: shape)
        } else {
            content
                .background(shape.fill(.ultraThinMaterial))
        }
    }
}

extension View {
    func liquidGlass<S: Shape>(shape: S, interactive: Bool = false) -> some View {
        modifier(LiquidGlassModifier(shape: shape, interactive: interactive))
    }
}
