import SwiftUI

struct WorkerAcceptingJobView: View {
    let jobId: UUID
    let applicationID: String
    let applicationStatus: String
    let viewJobInfo: () -> Void
    @Environment(LocalMarketplaceStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var job: BackendJob?
    @State private var loading = true
    @State private var error: String?
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Image(systemName: "checkmark.circle.fill").font(.system(size: 56)).foregroundStyle(Color.errnoGreen)
                Text("Application submitted").font(.system(size: 24, weight: .bold))
                Text("The backend has recorded your application. The shopkeeper will review it.")
                    .font(.system(size: 14)).foregroundStyle(Color.errnoTextSecondary)
                Group {
                    Text("Application ID: \(applicationID)")
                    Text("Application status: \(applicationStatus.capitalized)")
                }.font(.system(size: 12, weight: .medium)).foregroundStyle(Color.errnoTextSecondary)
                if loading { ProgressView("Loading job details…") }
                else if let error { Text(error).foregroundStyle(Color.errnoError); Button("Retry") { Task { await loadJob() } } }
                else if let job {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(job.title).font(.system(size: 18, weight: .bold))
                        StatusBadge(text: job.status.capitalized)
                        if let location = job.location { Label(location, systemImage: "mappin.and.ellipse") }
                        Text("\(job.duration_type) · \(job.pay_amount.formatted(.currency(code: "INR")))")
                        if let date = job.scheduled_date { Text("Scheduled: \(date)") }
                    }.marketplaceCard()
                }
                PrimaryButton(title: "Go to My Jobs", style: .dark, action: viewJobInfo)
                Button("Back to job details") { dismiss() }.frame(maxWidth: .infinity)
            }.padding(24)
        }.foregroundStyle(Color.errnoTextPrimary).marketplacePage().navigationTitle("Application")
            .task { await loadJob() }
    }

    @MainActor private func loadJob() async {
        loading = true; error = nil
        defer { loading = false }
        do { job = try await AppDependencies.catalog().job(id: jobId.uuidString) }
        catch { self.error = error.localizedDescription }
    }
}
