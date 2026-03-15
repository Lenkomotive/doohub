import SwiftUI
import Foundation

@MainActor
class TemplatesStore: ObservableObject {
    @Published var templates: [PipelineTemplate] = []
    @Published var templateDetails: [Int: PipelineTemplate] = [:]
    @Published var isLoading: Bool = false

    private let apiService: APIService

    init(apiService: APIService) {
        self.apiService = apiService
    }

    func fetchTemplates() async {
        isLoading = true
        do {
            templates = try await apiService.getTemplates()
        } catch {
            // Silent
        }
        isLoading = false
    }

    func fetchTemplateDetail(id: Int) async {
        do {
            let detail = try await apiService.getTemplate(id: id)
            templateDetails[id] = detail
        } catch {
            // Silent
        }
    }
}
