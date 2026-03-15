import SwiftUI

struct TemplateTile: View {
    let template: PipelineTemplate
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        SolidCard {
            VStack(alignment: .leading, spacing: 6) {
                Text(template.name)
                    .font(.headline)
                    .foregroundColor(AppTheme.textPrimaryColor(for: colorScheme))

                if let description = template.description, !description.isEmpty {
                    Text(description)
                        .font(.subheadline)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                        .lineLimit(2)
                } else if let definition = template.definition {
                    Text("\(definition.nodes.count) nodes")
                        .font(.subheadline)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                }

                Text(template.updatedAt, style: .relative)
                    .font(.caption)
                    .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
