import SwiftUI

struct TemplatesScreen: View {
    @EnvironmentObject private var templatesStore: TemplatesStore
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        ZStack {
            MeshBackground()

            if templatesStore.isLoading && templatesStore.templates.isEmpty {
                ProgressView()
            } else if templatesStore.templates.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "rectangle.3.group")
                        .font(.system(size: 48))
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                    Text("No Templates")
                        .font(.title3)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                }
            } else {
                List {
                    ForEach(templatesStore.templates) { template in
                        NavigationLink(value: Route.templateDetail(templateId: template.id)) {
                            TemplateTile(template: template)
                        }
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                        .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
                    }
                }
                .listStyle(.plain)
                .refreshable {
                    await templatesStore.fetchTemplates()
                }
            }
        }
        .navigationTitle("Templates")
        .task {
            await templatesStore.fetchTemplates()
        }
    }
}
