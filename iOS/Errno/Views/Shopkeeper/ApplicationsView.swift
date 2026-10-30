import SwiftUI

/// The existing per-job applicant route uses the same records as the Applications tab.
struct ApplicationsView: View {
    let job: Job
    @Environment(LocalMarketplaceStore.self) private var store
    @State private var errorMessage: String?
    @State private var isLoading = false
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(job.title).font(.system(size: 18, weight: .bold))
                if isLoading { ProgressView() }
                if let errorMessage { MarketplaceEmptyState(title: "Unable to load applications", message: errorMessage) }
                ApplicationRows(applications: store.applications.filter { $0.jobId == job.id })
            }.padding(20)
        }.marketplacePage().navigationTitle("Applicants").navigationBarTitleDisplayMode(.inline)
            .toolbar(.visible, for: .navigationBar)
            .task {
                isLoading = true; errorMessage = nil
                defer { isLoading = false }
                do { store.installBackendApplications(try await AppDependencies.backendRepository().ownerApplications()) }
                catch { errorMessage = error.localizedDescription }
            }
    }
}
