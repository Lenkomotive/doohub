import SwiftUI

struct MeshBackground: View {
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        if colorScheme == .dark {
            Color.black.ignoresSafeArea()
        } else {
            Color(hex: 0xF8F9FA).ignoresSafeArea()
        }
    }
}
