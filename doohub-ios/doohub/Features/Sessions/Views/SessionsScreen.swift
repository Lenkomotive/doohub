import SwiftUI

struct SessionsScreen: View {
    @EnvironmentObject private var sessionsStore: SessionsStore
    @EnvironmentObject private var router: AppRouter
    @Environment(\.colorScheme) private var colorScheme

    @State private var showCreateSheet = false

    var body: some View {
        ZStack {
            MeshBackground()

            if sessionsStore.isLoading && sessionsStore.sessions.isEmpty {
                ProgressView()
            } else if sessionsStore.sessions.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "bubble.left.and.bubble.right")
                        .font(.system(size: 48))
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                    Text("No Sessions")
                        .font(.title3)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                    Text("Create a new session to get started")
                        .font(.subheadline)
                        .foregroundColor(AppTheme.textSecondaryColor(for: colorScheme))
                }
            } else {
                List {
                    ForEach(sessionsStore.sessions) { session in
                        SessionTile(session: session)
                            .listRowBackground(Color.clear)
                            .listRowSeparator(.hidden)
                            .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    Task { await sessionsStore.deleteSession(key: session.sessionKey) }
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                            .onTapGesture {
                                router.navigate(to: .chat(sessionKey: session.sessionKey))
                            }
                    }
                }
                .listStyle(.plain)
                .refreshable {
                    await sessionsStore.fetchSessions()
                }
            }
        }
        .navigationTitle("Sessions")
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
            CreateSessionSheet()
        }
        .task {
            await sessionsStore.fetchSessions()
            sessionsStore.connectSSE()
        }
        .onDisappear {
            // Don't disconnect SSE on disappear since we want real-time updates
        }
    }
}
