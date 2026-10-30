import SwiftUI

struct ShopkeeperJobsView: View {
    @State private var viewModel: ShopkeeperDashboardViewModel
    @State private var selectedFilter = 1
    init(store: LocalMarketplaceStore) { _viewModel = State(initialValue: ShopkeeperDashboardViewModel(store: store)) }
    private var active: [Job] { viewModel.jobs.filter { $0.status == .open || $0.status == .assigned || $0.status == .inProgress } }
    private var completed: [Job] { viewModel.jobs.filter { $0.status == .completed } }
    private var filtered: [Job] { selectedFilter == 0 ? viewModel.jobs : selectedFilter == 1 ? active : completed }
    var body: some View {
        VStack(spacing: 0) {
            MarketplaceHeader(title: "My Jobs & Assigned Workers")
            MarketplaceFilters(labels: ["All (\(viewModel.jobs.count))", "Active (\(active.count))", "Completed (\(completed.count))"], selection: $selectedFilter)
            ScrollView {
                LazyVStack(spacing: 16) {
                    if viewModel.isLoading { ProgressView().padding() }
                    if let error = viewModel.errorMessage {
                        MarketplaceEmptyState(title: "Unable to load jobs", message: error)
                        Button("Retry") { Task { await viewModel.fetchJobs() } }.foregroundStyle(Color.errnoGreen)
                    }
                    if filtered.isEmpty { MarketplaceEmptyState(title: "No jobs found", message: "Your posted jobs will appear here.") }
                    ForEach(filtered) { job in
                        NavigationLink(destination: ShopkeeperJobDetailView(jobId: job.id)) {
                            JobTabCard(job: job, worker: job.assignedWorkerId.flatMap { viewModel.store.user(id: $0) })
                        }.buttonStyle(.plain)
                    }
                }.padding(20)
            }
        }.marketplacePage().toolbar(.hidden, for: .navigationBar)
            .task { await viewModel.fetchJobs() }
    }
}

private struct JobTabCard: View {
    let job: Job
    let worker: User?
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top) { Text(job.title).font(.system(size: 16, weight: .bold)); Spacer(); StatusBadge(text: job.displayStatus) }
            Label("\(job.locationLabel) • Scheduled: \(job.scheduleLabel)", systemImage: "mappin.and.ellipse")
                .font(.system(size: 13)).foregroundStyle(.gray)
            if let worker {
                Label("Worker Accepted: \(worker.name) • Profile →", systemImage: "person.fill")
                    .font(.system(size: 13, weight: .bold)).padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading).background(Color.errnoGreenLight, in: RoundedRectangle(cornerRadius: 12))
            }
            HStack { Text("Settlement Pay: \(job.payLabel)").bold(); Spacer(); Text(job.createdAt, style: .relative).foregroundStyle(.gray) }.font(.system(size: 12))
            if job.workerRating > 0 { Text("You rated worker: \(job.workerRating) ★").font(.system(size: 12, weight: .bold)) }
            if worker != nil { Divider(); Label("View Profile", systemImage: "person").font(.system(size: 12, weight: .bold)).foregroundStyle(Color.errnoGreen).frame(maxWidth: .infinity) }
        }.marketplaceCard().foregroundStyle(Color.errnoTextPrimary)
    }
}

struct ShopkeeperJobDetailView: View {
    let jobId: UUID
    @Environment(LocalMarketplaceStore.self) private var store
    @State private var rating = false
    @State private var completion = false
    @State private var error: String?
    var body: some View {
        ScrollView {
            if let job = store.job(id: jobId) {
                VStack(alignment: .leading, spacing: 16) {
                    Text(job.title).font(.system(size: 20, weight: .bold))
                    StatusBadge(text: job.displayStatus)
                    Text(job.description).font(.system(size: 14)).foregroundStyle(Color.errnoTextSecondary)
                    Text("\(job.durationLabel) • \(job.payLabel) total • \(job.scheduleLabel)").font(.system(size: 13, weight: .bold))
                    WorkerLocationMapView(locationName: job.locationLabel, distanceText: "Shop Location", isDarkTheme: false)
                    if let id = job.assignedWorkerId, let worker = store.user(id: id) {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Assigned Worker Profile").font(.system(size: 18, weight: .bold))
                            Text(worker.name).font(.system(size: 18, weight: .bold))
                            Text("Rating: \(worker.rating ?? 0, specifier: "%.1f") ★ • \(worker.totalJobsCompleted ?? 0) Shifts")
                                .font(.system(size: 12))
                            Text(id == store.worker.id && store.isVerified ? "Demo Aadhaar Verified • \(store.maskedAadhaar)" : "Identity verification is not confirmed")
                                .font(.system(size: 11)).foregroundStyle(Color.errnoTextSecondary)
                            ContactActions(phone: worker.phone)
                        }.marketplaceCard()
                    }
                    NavigationLink("View Job Applications") { ApplicationsView(job: job) }
                    if job.status == .open || job.status == .assigned {
                        PrimaryButton(title: "Cancel Job", style: .secondary) { completion = true }
                    }
                    if job.status == .inProgress {
                        PrimaryButton(title: "Confirm Work Completed", style: .dark) { completion = true }
                    }
                    if job.status == .completed {
                        PrimaryButton(title: "Rate Hired Worker", style: .secondary) { rating = true }
                    }
                    if let error { Text(error).foregroundStyle(Color.errnoError) }
                }.padding(20).frame(maxWidth: 800).frame(maxWidth: .infinity)
            } else { MarketplaceEmptyState(title: "Job unavailable", message: "Return to My Jobs and select an existing job.").padding(20) }
        }.marketplacePage().navigationTitle("Job Details").navigationBarTitleDisplayMode(.inline)
            .toolbar(.visible, for: .navigationBar)
            .confirmationDialog(jobActionTitle, isPresented: $completion, titleVisibility: .visible) {
                Button(jobActionIsCompletion ? "Confirm completion" : "Cancel job", role: jobActionIsCompletion ? nil : .destructive) {
                    Task { await performLifecycleAction(jobActionIsCompletion ? "complete" : "cancel") }
                }
                Button("Keep job", role: .cancel) {}
            }
            .sheet(isPresented: $rating) { RatingDialog(title: "Rate Hired Worker", target: "Worker") { stars, comment in store.rate(jobId: jobId, role: .shopkeeper, stars: stars, comment: comment) } }
    }

    private var jobActionTitle: String {
        store.job(id: jobId)?.status == .inProgress ? "Confirm this work is complete?" : "Cancel this job?"
    }
    private var jobActionIsCompletion: Bool { store.job(id: jobId)?.status == .inProgress }

    @MainActor private func performLifecycleAction(_ action: String) async {
        do {
            let repository = try AppDependencies.backendRepository()
            let updated = action == "complete"
                ? try await repository.completeJob(jobID: jobId.uuidString)
                : try await repository.cancelJob(jobID: jobId.uuidString)
            store.updateLifecycle(updated)
        } catch let requestError { error = requestError.localizedDescription }
    }
}
