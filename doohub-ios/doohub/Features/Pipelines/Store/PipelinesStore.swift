import SwiftUI
import Foundation

@MainActor
class PipelinesStore: ObservableObject {
    @Published var pipelines: [Pipeline] = []
    @Published var isLoading: Bool = false
    @Published var mergeStatuses: [String: MergeStatus] = [:]
    @Published var mergingKeys: Set<String> = []

    private let apiService: APIService
    private var sseClient: SSEClient?

    init(apiService: APIService) {
        self.apiService = apiService
    }

    func fetchPipelines() async {
        isLoading = true
        do {
            let fetched = try await apiService.getPipelines()
            pipelines = fetched
            // Auto-check merge status for completed pipelines
            for pipeline in fetched where pipeline.status == "done" {
                await checkMergeStatus(key: pipeline.pipelineKey)
            }
        } catch {
            // Silent
        }
        isLoading = false
    }

    func createPipeline(repoPath: String, issueNumber: Int?, taskDescription: String?, model: String?, templateId: Int?) async -> Pipeline? {
        do {
            let pipeline = try await apiService.createPipeline(
                repoPath: repoPath,
                issueNumber: issueNumber,
                taskDescription: taskDescription,
                model: model,
                templateId: templateId
            )
            pipelines.insert(pipeline, at: 0)
            return pipeline
        } catch {
            return nil
        }
    }

    func cancelPipeline(key: String) async {
        do {
            try await apiService.cancelPipeline(key: key)
        } catch {
            // Silent
        }
    }

    func deletePipeline(key: String) async {
        pipelines.removeAll { $0.pipelineKey == key }
        do {
            try await apiService.deletePipeline(key: key)
        } catch {
            await fetchPipelines()
        }
    }

    func checkMergeStatus(key: String) async {
        do {
            let status = try await apiService.getMergeStatus(key: key)
            mergeStatuses[key] = status
        } catch {
            // Silent
        }
    }

    func mergePipeline(key: String) async {
        mergingKeys.insert(key)
        do {
            try await apiService.mergePipeline(key: key)
            await checkMergeStatus(key: key)
        } catch {
            // Silent
        }
        mergingKeys.remove(key)
    }

    // MARK: - SSE

    func connectSSE() {
        Task {
            guard let url = await apiService.pipelineEventsURL() else { return }
            sseClient?.disconnect()
            sseClient = SSEClient(url: url)
            sseClient?.connect { [weak self] event in
                Task { @MainActor in
                    self?.handleSSEEvent(event)
                }
            }
        }
    }

    func disconnectSSE() {
        sseClient?.disconnect()
        sseClient = nil
    }

    private func handleSSEEvent(_ event: SSEEvent) {
        guard let data = event.data.data(using: .utf8) else { return }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)
            let formatters: [DateFormatter] = {
                let f1 = DateFormatter()
                f1.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
                f1.timeZone = TimeZone(identifier: "UTC")
                let f2 = DateFormatter()
                f2.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
                f2.timeZone = TimeZone(identifier: "UTC")
                return [f1, f2]
            }()
            for formatter in formatters {
                if let date = formatter.date(from: dateString) { return date }
            }
            let iso = ISO8601DateFormatter()
            iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = iso.date(from: dateString) { return date }
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Cannot decode date: \(dateString)")
        }

        // Backend sends event: pipeline for all pipeline updates
        switch event.event {
        case "pipeline":
            // Any pipeline event triggers a refetch for simplicity
            Task {
                await fetchPipelines()
            }
        default:
            break
        }
    }
}

struct PipelineStatusUpdate: Decodable {
    let pipelineKey: String
    let status: String
}
