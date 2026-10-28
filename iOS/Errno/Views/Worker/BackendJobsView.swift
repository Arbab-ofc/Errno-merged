import SwiftUI

/// Public catalog uses the server's IDs and strings verbatim. Missing data is not replaced by demo locations or GPS.
struct BackendJobsView: View {
    @State private var model = BackendJobsViewModel()
    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 16) {
                Text("Available Jobs & Deliveries").font(.system(size: 18, weight: .bold)).foregroundStyle(.white)
                if model.isLoading { ProgressView("Loading jobs…").tint(.white).foregroundStyle(.white) }
                else if let error = model.errorMessage {
                    MarketplaceEmptyState(title: "Unable to load jobs", message: error, dark: true)
                    Button("Retry") { Task { await model.load() } }.tint(.errnoLime)
                } else if model.jobs.isEmpty {
                    MarketplaceEmptyState(title: "No Available Jobs Nearby", message: "New work opportunities will appear here when posted.", dark: true)
                }
                ForEach(model.jobs) { job in
                    NavigationLink { BackendJobDetailsView(jobID: job.id) } label: {
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Text(job.title).font(.system(size: 17, weight: .bold))
                                Spacer()
                                StatusBadge(text: job.is_delivery ? "Delivery" : "New")
                            }
                            if let location = job.location { Label(location, systemImage: "mappin.and.ellipse").font(.system(size: 13)).foregroundStyle(.gray) }
                            HStack {
                                Label(job.duration_type, systemImage: "clock").font(.system(size: 13))
                                Spacer()
                                Text(job.pay_amount, format: .currency(code: "INR")).font(.system(size: 15, weight: .bold))
                            }
                        }.marketplaceCard().foregroundStyle(Color.errnoTextPrimary)
                    }.buttonStyle(.plain)
                }
            }.padding(20).frame(maxWidth: 840).frame(maxWidth: .infinity)
        }.marketplacePage(dark: true)
            .navigationTitle("Available Jobs").navigationBarTitleDisplayMode(.inline)
            .toolbar(.visible, for: .navigationBar)
            .task { await model.load() }
            .refreshable { await model.load() }
    }
}

struct BackendJobDetailsView: View {
    let jobID: String
    @Environment(\.dismiss) private var dismiss
    @State private var job: BackendJob?
    @State private var isLoading = false
    @State private var error: String?
    var body: some View {
        VStack(spacing: 0) {
            MarketplaceHeader(title: "Job Details", dark: true, back: { dismiss() })
            ScrollView {
                if isLoading { ProgressView("Loading job…").tint(.white).foregroundStyle(.white).padding() }
                else if let error {
                    MarketplaceEmptyState(title: "Unable to load job", message: error, dark: true).padding(20)
                    Button("Retry") { Task { await load() } }.tint(.errnoLime)
                } else if let job {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(job.title).font(.system(size: 20, weight: .bold))
                        if let location = job.location { Label(location, systemImage: "mappin.and.ellipse").font(.system(size: 13)).foregroundStyle(.gray) }
                        if let description = job.description { Text(description).font(.system(size: 14)).foregroundStyle(Color.errnoTextSecondary) }
                        Text("Work Location & Route").font(.system(size: 14, weight: .bold))
                        if let pickup = job.pickup_location { Text("Pickup: \(pickup)") }
                        if let drop = job.drop_location { Text("Drop: \(drop)") }
                        Text("Choose Duration & Pay").font(.system(size: 16, weight: .bold))
                        if let date = job.scheduled_date { Text("Scheduled: \(date)").font(.system(size: 12)).foregroundStyle(.gray) }
                        StatusBadge(text: job.status)
                        Text("Applications are unavailable until secure sign-in is supported.").font(.system(size: 12)).foregroundStyle(Color.errnoTextSecondary)
                    }.marketplaceCard(padding: 12, radius: 20).padding(.horizontal, 12).padding(.vertical, 8)
                }
            }
        }.marketplacePage(dark: true).toolbar(.hidden, for: .navigationBar)
            .safeAreaInset(edge: .bottom, spacing: 0) {
                if let job {
                    VStack(spacing: 8) {
                        HStack {
                            Text(job.duration_type)
                            Spacer()
                            Text(job.pay_amount, format: .currency(code: "INR")).bold()
                        }.font(.system(size: 14)).foregroundStyle(Color.errnoTextPrimary)
                            .padding(12).background(Color.errnoBackground, in: RoundedRectangle(cornerRadius: 10))
                        PrimaryButton(title: "Accept Job", style: .dark) {}.disabled(true)
                    }.padding(16).background(Color.errnoNavy)
                }
            }
            .task { await load() }
    }
    private func load() async {
        guard !isLoading else { return }
        isLoading = true; error = nil; job = nil
        defer { isLoading = false }
        do {
            let result = try await AppDependencies.catalog().job(id: jobID)
            try Task.checkCancellation()
            job = result
        } catch is CancellationError { }
        catch { self.error = error.localizedDescription }
    }
}
