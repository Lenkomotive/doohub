import SwiftUI
import MarkdownUI
import UniformTypeIdentifiers

struct ChatScreen: View {
    let sessionKey: String

    @EnvironmentObject private var sessionsStore: SessionsStore
    @Environment(\.colorScheme) private var colorScheme

    @State private var messageText = ""
    @State private var showFilePicker = false
    @State private var isAtBottom = true
    @FocusState private var isInputFocused: Bool

    private var session: Session? {
        sessionsStore.sessions.first { $0.sessionKey == sessionKey }
    }

    private var messages: [Message] {
        sessionsStore.messageCache[sessionKey] ?? []
    }

    private var isSending: Bool {
        sessionsStore.sendingKeys.contains(sessionKey)
    }

    private var pendingAttachments: [SessionsStore.PendingAttachment] {
        sessionsStore.pendingAttachments[sessionKey] ?? []
    }

    var body: some View {
        VStack(spacing: 0) {
            // Messages list
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(messages) { message in
                            MessageBubble(message: message)
                                .id(message.id)
                        }

                        if session?.status == "busy" && !isSending {
                            TypingBubble()
                                .id("typing")
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                }
                .onChange(of: messages.count) { _ in
                    if isAtBottom, let lastId = messages.last?.id {
                        withAnimation {
                            proxy.scrollTo(lastId, anchor: .bottom)
                        }
                    }
                }
                .onChange(of: session?.status) { _ in
                    if session?.status == "busy", isAtBottom {
                        withAnimation {
                            proxy.scrollTo("typing", anchor: .bottom)
                        }
                    }
                }
                .onAppear {
                    if let lastId = messages.last?.id {
                        proxy.scrollTo(lastId, anchor: .bottom)
                    }
                }
            }

            // Pending attachments
            if !pendingAttachments.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(pendingAttachments) { attachment in
                            PendingAttachmentChip(
                                attachment: attachment,
                                onRemove: {
                                    sessionsStore.removePendingAttachment(
                                        sessionKey: sessionKey,
                                        attachmentId: attachment.id
                                    )
                                }
                            )
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 6)
                }
            }

            Divider()

            // Input bar
            HStack(alignment: .bottom, spacing: 8) {
                Button {
                    showFilePicker = true
                } label: {
                    Image(systemName: "paperclip")
                        .font(.title3)
                        .foregroundColor(AppTheme.primaryColor(for: colorScheme))
                }
                .padding(.bottom, 6)

                TextField("Message...", text: $messageText, axis: .vertical)
                    .textFieldStyle(.plain)
                    .lineLimit(1...6)
                    .focused($isInputFocused)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(AppTheme.cardColor(for: colorScheme))
                    .clipShape(RoundedRectangle(cornerRadius: 20))

                Button {
                    let text = messageText
                    messageText = ""
                    Task {
                        await sessionsStore.sendMessage(sessionKey: sessionKey, content: text)
                    }
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.title2)
                        .foregroundColor(
                            messageText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                            ? AppTheme.textSecondaryColor(for: colorScheme)
                            : AppTheme.primaryColor(for: colorScheme)
                        )
                }
                .disabled(messageText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSending)
                .padding(.bottom, 6)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
        }
        .background(MeshBackground())
        .navigationTitle(session?.name ?? "Chat")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .principal) {
                VStack(spacing: 2) {
                    Text(session?.name ?? "Chat")
                        .font(.headline)
                    if let session {
                        StatusBadge(
                            status: session.status,
                            color: AppTheme.sessionStatusColor(for: session.status)
                        )
                    }
                }
            }

            ToolbarItem(placement: .primaryAction) {
                Menu {
                    if session?.status == "busy" {
                        Button(role: .destructive) {
                            Task { await sessionsStore.cancelSession(key: sessionKey) }
                        } label: {
                            Label("Cancel", systemImage: "stop.circle")
                        }
                    }

                    Button(role: .destructive) {
                        Task {
                            await sessionsStore.deleteSession(key: sessionKey)
                        }
                    } label: {
                        Label("Delete", systemImage: "trash")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
            }
        }
        .fileImporter(
            isPresented: $showFilePicker,
            allowedContentTypes: [.data],
            allowsMultipleSelection: false
        ) { result in
            handleFileImport(result)
        }
        .task {
            await sessionsStore.fetchHistory(sessionKey: sessionKey)
        }
    }

    private func handleFileImport(_ result: Result<[URL], Error>) {
        guard case .success(let urls) = result, let url = urls.first else { return }

        guard url.startAccessingSecurityScopedResource() else { return }
        defer { url.stopAccessingSecurityScopedResource() }

        guard let data = try? Data(contentsOf: url) else { return }

        let filename = url.lastPathComponent
        let mimeType = UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "application/octet-stream"

        sessionsStore.addPendingAttachment(
            sessionKey: sessionKey,
            data: data,
            filename: filename,
            mimeType: mimeType
        )
    }
}
