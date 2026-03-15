import SwiftUI

struct PipelinesScreen: View {
    @EnvironmentObject private var pipelinesStore: PipelinesStore
    @EnvironmentObject private var router: AppRouter
    @Environment(\.colorScheme) private var colorScheme

    @State private var showCreateSheet = false

    var body: some View {
        ZStack {
            MeshBackground()

            if pipelinesStore.isLoading && pipelinesStore.pipelines.isEmpty {
                ProgressView()
            } else if pipelinesStore.pipelines.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "point.3.connected.trianglepath.dotted")
                        .font(.system(size: 48))
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                    Text("No Pipelines")
                        .font(.title3)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                    Text("Create a pipeline to automate development")
                        .font(.subheadline)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                }
            } else {
                List {
                    ForEach(pipelinesStore.pipelines) { pipeline in
                        PipelineTile(pipeline: pipeline)
                            .listRowBackground(Color.clear)
                            .listRowSeparator(.hidden)
                            .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    Task { await pipelinesStore.deletePipeline(key: pipeline.pipelineKey) }
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                            .onTapGesture {
                                router.navigate(to: .pipelineDetail(pipelineKey: pipeline.pipelineKey))
                            }
                    }
                }
                .listStyle(.plain)
                .refreshable {
                    await pipelinesStore.fetchPipelines()
                }
            }
        }
        .navigationTitle("Pipelines")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    showCreateSheet = true
                } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .sheet(isPresented: $showCreateSheet) {
            CreatePipelineSheet()
        }
        .task {
            await pipelinesStore.fetchPipelines()
            pipelinesStore.connectSSE()
        }
    }
}
