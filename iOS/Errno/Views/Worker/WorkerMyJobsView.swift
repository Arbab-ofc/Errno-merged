import SwiftUI

struct WorkerMyJobsView: View {
    @Environment(LocalMarketplaceStore.self) private var store
    @State private var filter = 0
    @State private var isLoading = false
    @State private var isLoadingMore = false
    @State private var errorMessage: String?
    @State private var applications: [BackendWorkerApplication] = []
    @State private var hasMoreApplications = false
    @State private var selectedApplication: BackendWorkerApplication?
    @State private var actionError: String?
    @State private var actionLoadingID: String?
    private let pageSize = 20

    private var upcoming: [Job] { store.workerJobs.filter { $0.status == .assigned } }
    private var ongoing: [Job] { store.workerJobs.filter { $0.status == .inProgress } }
    private var completed: [Job] { store.workerJobs.filter { $0.status == .completed } }
    private var jobs: [Job] { filter == 1 ? upcoming : filter == 2 ? ongoing : completed }

    var body: some View {
        VStack(spacing: 0) {
            MarketplaceHeader(title: "My Jobs", dark: true)
            MarketplaceFilters(labels: ["Applications (\(applications.count))", "Upcoming (\(upcoming.count))", "Ongoing (\(ongoing.count))", "Completed (\(completed.count))"], selection: $filter, dark: true)
            ScrollView {
                LazyVStack(spacing: 16) {
                    if isLoading { ProgressView().padding() }
                    if let errorMessage {
                        MarketplaceEmptyState(title: "Unable to load your work", message: errorMessage, dark: true)
                        Button("Retry") { Task { await load() } }.tint(.errnoLime)
                    } else if filter == 0 {
                        if applications.isEmpty && !isLoading {
                            MarketplaceEmptyState(title: "No applications yet", message: "Jobs you apply to will appear here with their current status.", dark: true)
                        }
                        ForEach(applications) { application in
                            Button { selectedApplication = application } label: { ApplicationHistoryCard(application: application) }
                                .buttonStyle(.plain)
                        }
                        if hasMoreApplications {
                            Button(isLoadingMore ? "Loading…" : "Load more") { Task { await loadMore() } }
                                .disabled(isLoadingMore).tint(.errnoLime)
                        }
                    } else if jobs.isEmpty && !isLoading {
                        MarketplaceEmptyState(title: "No jobs in this section", message: "Your assigned work will appear here as its status changes.", dark: true)
                    }
                    ForEach(jobs) { job in
                        WorkerMyJobCard(job: job, isStarting: actionLoadingID == job.id.uuidString,
                                        onStart: { Task { await start(job) } })
                    }
                }.padding(20)
            }
        }
        .marketplacePage(dark: true)
        .task { await load() }
        .refreshable { await load() }
        .sheet(item: $selectedApplication) { application in
            ApplicationHistoryDetail(application: application, isCancelling: actionLoadingID == application.id,
                                     onCancel: { Task { await cancel(application) } })
                .presentationDetents([.medium, .large])
        }
        .alert("Unable to update", isPresented: Binding(get: { actionError != nil }, set: { if !$0 { actionError = nil } })) {
            Button("OK", role: .cancel) { actionError = nil }
        } message: { Text(actionError ?? "Please retry.") }
    }

    private func load() async {
        isLoading = true; errorMessage = nil
        defer { isLoading = false }
        do {
            let repository = try AppDependencies.backendRepository()
            let jobs = try await repository.workerJobs()
            store.installBackendJobs(jobs, ownerID: store.shopkeeper.id)
            let page = try await repository.workerApplications(limit: pageSize, offset: 0)
            applications = page.items
            hasMoreApplications = page.has_more
        } catch { errorMessage = error.localizedDescription }
    }

    private func loadMore() async {
        guard !isLoadingMore else { return }
        isLoadingMore = true; defer { isLoadingMore = false }
        do {
            let page = try await AppDependencies.backendRepository().workerApplications(limit: pageSize, offset: applications.count)
            applications.append(contentsOf: page.items)
            hasMoreApplications = page.has_more
        } catch { errorMessage = error.localizedDescription }
    }

    private func cancel(_ application: BackendWorkerApplication) async {
        actionLoadingID = application.id; defer { actionLoadingID = nil }
        do {
            _ = try await AppDependencies.backendRepository().cancelApplication(jobID: application.job_id)
            selectedApplication = nil
            await load()
        } catch { actionError = error.localizedDescription }
    }

    private func start(_ job: Job) async {
        actionLoadingID = job.id.uuidString; defer { actionLoadingID = nil }
        do {
            let updated = try await AppDependencies.backendRepository().startJob(jobID: job.id.uuidString)
            store.updateLifecycle(updated, ownerID: store.shopkeeper.id)
        } catch { actionError = error.localizedDescription }
    }
}

private struct ApplicationHistoryCard: View {
    let application: BackendWorkerApplication
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack { Text(application.job.title).font(.system(size: 17, weight: .bold)); Spacer(); StatusBadge(text: application.status.capitalized) }
            Text(application.job.shop?.shop_name ?? "Shop details unavailable").font(.system(size: 14, weight: .semibold))
            Text([application.job.shop?.address, application.job.location].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " • "))
                .font(.system(size: 12)).foregroundStyle(.gray)
            HStack { Text("Applied \(application.created_at ?? "Date unavailable")"); Spacer(); Text(application.job.pay_amount, format: .currency(code: "INR")).bold() }
                .font(.system(size: 12)).foregroundStyle(.gray)
        }.marketplaceCard().foregroundStyle(Color.errnoTextPrimary)
    }
}

private struct ApplicationHistoryDetail: View {
    let application: BackendWorkerApplication
    let isCancelling: Bool
    let onCancel: () -> Void
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(application.job.title).font(.system(size: 21, weight: .bold))
            StatusBadge(text: "Application: \(application.status.capitalized)")
            Label(application.job.shop?.shop_name ?? "Shop details unavailable", systemImage: "storefront")
            if let address = application.job.shop?.address, !address.isEmpty { Label(address, systemImage: "mappin.and.ellipse") }
            if let location = application.job.location, !location.isEmpty { Text("Work location: \(location)") }
            Text("Job status: \(application.job.status.replacingOccurrences(of: "_", with: " ").capitalized)")
            Text("Applied: \(application.created_at ?? "Date unavailable")")
            Text(application.job.pay_amount, format: .currency(code: "INR")).fontWeight(.bold)
            Spacer()
            if application.status == "pending" {
                PrimaryButton(title: isCancelling ? "Cancelling…" : "Cancel application", style: .secondary, action: onCancel).disabled(isCancelling)
            }
            Button("Close") { dismiss() }.frame(maxWidth: .infinity)
        }.padding(24).foregroundStyle(Color.errnoTextPrimary)
    }
}

private struct WorkerMyJobCard: View {
    let job: Job
    let isStarting: Bool
    let onStart: () -> Void
    @Environment(LocalMarketplaceStore.self) private var store
    @State private var expanded = true
    @State private var rating = false
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            NavigationLink(value: WorkerRoute.details(job.id)) {
              VStack(alignment: .leading, spacing: 6) {
                HStack { Text(job.title).font(.system(size: 17, weight: .bold)); Spacer(); StatusBadge(text: job.displayStatus) }
                Text("\(job.locationLabel) • \(job.distance)").font(.system(size: 13)).foregroundStyle(.gray)
                HStack { Text("🕒 \(job.durationLabel) • \(job.scheduleLabel)"); Spacer(); Text(job.payLabel).bold() }.font(.system(size: 13))
              }.foregroundStyle(Color.errnoTextPrimary)
            }.buttonStyle(.plain)
            if job.status == .assigned {
                PrimaryButton(title: isStarting ? "Starting…" : "Start Job", style: .dark, action: onStart).disabled(isStarting)
            }
            Divider()
            if job.status == .completed {
                HStack { Spacer(); Button("Rate Shopkeeper") { rating = true }.font(.system(size: 12, weight: .bold)) }
            } else {
                Button { expanded.toggle() } label: { Label(expanded ? "Hide Map" : "Shop Map", systemImage: "arrow.triangle.turn.up.right.diamond").font(.system(size: 12, weight: .bold)) }
                if expanded { WorkerLocationMapView(locationName: job.locationLabel, distanceText: job.distance) }
            }
        }.marketplaceCard()
            .sheet(isPresented: $rating) { RatingDialog(title: "Rate Shopkeeper Experience", target: "Shopkeeper") { stars, comment in store.rate(jobId: job.id, role: .worker, stars: stars, comment: comment) } }
    }
}
