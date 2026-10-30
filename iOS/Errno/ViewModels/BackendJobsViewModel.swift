import Foundation
import Observation

@Observable
@MainActor
final class BackendJobsViewModel {
    private(set) var jobs: [BackendJob] = []
    private(set) var isLoading = false
    private(set) var errorMessage: String?
    @ObservationIgnored private let repository: (any JobCatalogRepository)?
    @ObservationIgnored private var generation = 0

    init(repository: (any JobCatalogRepository)? = nil) { self.repository = repository }

    func load() async {
        generation += 1
        let requestGeneration = generation
        isLoading = true
        errorMessage = nil
        defer { if generation == requestGeneration { isLoading = false } }
        do {
            let repository = try repository ?? AppDependencies.catalog()
            let result = try await repository.jobs(status: "open")
            try Task.checkCancellation()
            guard generation == requestGeneration else { return }
            jobs = result
        } catch is CancellationError { }
        catch {
            guard generation == requestGeneration else { return }
            jobs = [] // Never show stale jobs as currently available after a failed refresh.
            errorMessage = error.localizedDescription
        }
    }
}
