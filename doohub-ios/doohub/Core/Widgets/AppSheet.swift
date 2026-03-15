import SwiftUI

struct AppSheet<Content: View>: View {
    let title: String?
    let systemImage: String?
    @ViewBuilder let content: () -> Content

    init(title: String? = nil, systemImage: String? = nil, @ViewBuilder content: @escaping () -> Content) {
        self.title = title
        self.systemImage = systemImage
        self.content = content
    }

    var body: some View {
        VStack(spacing: 0) {
            RoundedRectangle(cornerRadius: 2)
                .fill(Color.primary.opacity(0.2))
                .frame(width: 40, height: 4)
                .padding(.top, 12)

            if let title {
                HStack(spacing: 8) {
                    if let systemImage {
                        Image(systemName: systemImage)
                    }
                    Text(title).font(.headline)
                }
                .padding(.top, 16)
                .padding(.bottom, 8)
            }

            content()
        }
        .background(
            ZStack { MeshBackground() }
                .clipShape(UnevenRoundedRectangle(topLeadingRadius: 20, topTrailingRadius: 20))
        )
    }
}
