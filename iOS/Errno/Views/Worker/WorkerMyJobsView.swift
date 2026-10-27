import SwiftUI

struct WorkerMyJobsView: View {
    @Environment(LocalMarketplaceStore.self) private var store
    @State private var filter = 0 // Match Android's Upcoming tab as the initial selection.
    private var upcoming: [Job] { [] } // Android acceptance does not produce Upcoming jobs.
    private var ongoing: [Job] { store.workerJobs.filter { $0.status == .inProgress } }
    private var completed: [Job] { store.workerJobs.filter { $0.status == .completed } }
    private var jobs: [Job] { filter == 0 ? upcoming : filter == 1 ? ongoing : completed }
    var body: some View {
        VStack(spacing: 0) {
            MarketplaceHeader(title: "My Jobs", dark: true)
            MarketplaceFilters(labels: ["Upcoming (\(upcoming.count))", "Ongoing (\(ongoing.count))", "Completed (\(completed.count))"], selection: $filter, dark: true)
            ScrollView {
                LazyVStack(spacing: 16) {
                    if jobs.isEmpty { MarketplaceEmptyState(title: "No jobs in this section", message: "Accepted shifts will appear in Ongoing.", dark: true) }
                    ForEach(jobs) { WorkerMyJobCard(job: $0) }
                }.padding(20)
            }
        }.marketplacePage(dark: true)
    }
}

private struct WorkerMyJobCard: View {
    let job: Job
    @Environment(LocalMarketplaceStore.self) private var store
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var expanded = true
    @State private var rating = false
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            NavigationLink(value: WorkerRoute.details(job.id)) {
                VStack(alignment: .leading, spacing: 6) {
                    HStack { Text(job.title).font(.system(size: 17, weight: .bold)); Spacer(); StatusBadge(text: job.status == .completed ? "Completed" : "Ongoing") }
                    Text("\(job.locationLabel) • \(job.distance)").font(.system(size: 13)).foregroundStyle(.gray)
                    HStack { Text("🕒 \(job.durationLabel) • \(job.scheduleLabel)"); Spacer(); Text(job.payLabel).bold() }.font(.system(size: 13))
                }.foregroundStyle(Color.errnoTextPrimary)
            }.buttonStyle(.plain)
            Divider()
            if job.status == .completed {
                HStack {
                    if job.shopkeeperRating > 0 { Text("Rated: \(job.shopkeeperRating) ★").font(.system(size: 12, weight: .bold)) }
                    Spacer()
                    Button("Rate Shopkeeper") { rating = true }.font(.system(size: 12, weight: .bold))
                }
            } else {
                Button { withAnimation(reduceMotion ? nil : .easeInOut(duration: 0.3)) { expanded.toggle() } } label: {
                    Label(expanded ? "Hide Map" : "Shop Map", systemImage: "arrow.triangle.turn.up.right.diamond").font(.system(size: 12, weight: .bold))
                }
                if expanded { WorkerLocationMapView(locationName: job.locationLabel, distanceText: job.distance).transition(.opacity.combined(with: .move(edge: .top))) }
            }
        }.marketplaceCard()
            .sheet(isPresented: $rating) { RatingDialog(title: "Rate Shopkeeper Experience", target: "Shopkeeper") { stars, comment in store.rate(jobId: job.id, role: .worker, stars: stars, comment: comment) } }
    }
}
