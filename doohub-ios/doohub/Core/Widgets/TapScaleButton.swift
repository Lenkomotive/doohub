import SwiftUI

struct TapScaleButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.92 : 1.0)
            .animation(.easeInOut(duration: 0.12), value: configuration.isPressed)
    }
}

extension View {
    func tapScale(onTap: @escaping () -> Void) -> some View {
        Button(action: onTap) { self }
            .buttonStyle(TapScaleButtonStyle())
    }
}
