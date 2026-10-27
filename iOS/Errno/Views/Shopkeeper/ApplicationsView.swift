import SwiftUI

/// The existing per-job applicant route uses the same records as the Applications tab.
struct ApplicationsView: View {
    let job: Job
    @Environment(LocalMarketplaceStore.self) private var store
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(job.title).font(.system(size: 18, weight: .bold))
                ApplicationRows(applications: store.applications.filter { $0.jobId == job.id })
                if store.job(id: job.id)?.status == .open {
                    Button("Add Local Demo Applicants") { store.addDemoApplicants(jobId: job.id) }
                    MockNotice(text: "Optional local fixtures, not real worker applications.")
                }
            }.padding(20)
        }.marketplacePage().navigationTitle("Applicants").navigationBarTitleDisplayMode(.inline)
            .toolbar(.visible, for: .navigationBar)
    }
}
