import SwiftUI

struct TypingBubble: View {
    @State private var animationPhase = 0.0
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack {
            HStack(spacing: 4) {
                ForEach(0..<3, id: \.self) { index in
                    Circle()
                        .fill(AppTheme.textSecondaryColor(for: colorScheme))
                        .frame(width: 8, height: 8)
                        .offset(y: dotOffset(for: index))
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 14)
            .background(AppTheme.cardColor(for: colorScheme))
            .clipShape(RoundedRectangle(cornerRadius: 18))

            Spacer(minLength: 60)
        }
        .onAppear {
            withAnimation(.easeInOut(duration: 0.6).repeatForever(autoreverses: true)) {
                animationPhase = 1.0
            }
        }
    }

    private func dotOffset(for index: Int) -> CGFloat {
        let delay = Double(index) * 0.15
        let adjustedPhase = max(0, animationPhase - delay)
        return -adjustedPhase * 6
    }
}
