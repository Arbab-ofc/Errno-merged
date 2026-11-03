import SwiftUI

struct WorkerHomeView: View {
    @Environment(LocalMarketplaceStore.self) private var store
    var onApplicationSubmitted: ((UUID, BackendApplication) -> Void)? = nil
    var body: some View {
        if !AppDependencies.isDemo {
            BackendJobsView(showsAvailabilityControl: true, onApplicationSubmitted: onApplicationSubmitted)
        } else { demoBody }
    }
    private var demoBody: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 16) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Hello, \(store.worker.name) 👋").font(.system(size: 22, weight: .bold))
                        Text("Find work & delivery shifts near you").font(.system(size: 13)).foregroundStyle(.white.opacity(0.7))
                    }
                    Spacer()
                }.foregroundStyle(.white)
                Label(store.currentLocation, systemImage: "mappin.and.ellipse")
                    .font(.system(size: 14, weight: .medium)).foregroundStyle(.white)
                    .padding(16).frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(hex: "182436"), in: RoundedRectangle(cornerRadius: 12))
                Text("Available Jobs & Deliveries").font(.system(size: 18, weight: .bold)).foregroundStyle(.white).padding(.top, 8)
                if store.availableJobs.isEmpty {
                    MarketplaceEmptyState(title: "No Available Jobs Nearby", message: "New daily wage work and delivery shift opportunities posted by shopkeepers near you will appear here automatically.", dark: true)
                }
                ForEach(store.availableJobs) { job in
                    NavigationLink(value: WorkerRoute.details(job.id)) { WorkerAvailableJobCard(job: job) }.buttonStyle(.plain)
                }
            }.padding(.horizontal, 20).padding(.vertical, 12).frame(maxWidth: 840).frame(maxWidth: .infinity)
        }.marketplacePage(dark: true)
    }
}

struct WorkerAvailableJobCard: View {
    let job: Job
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack { Text(job.title).font(.system(size: 17, weight: .bold)); Spacer(); StatusBadge(text: job.isDelivery ? "Delivery" : "New") }
            Label("\(job.locationLabel) • \(job.distance)", systemImage: "mappin.and.ellipse")
                .font(.system(size: 13)).foregroundStyle(.gray)
            if job.isDelivery {
                VStack(alignment: .leading, spacing: 4) {
                    Text("📦 Pickup: \(job.pickupLocation)")
                    Text("📍 Drop: \(job.dropLocation)")
                }.font(.system(size: 11)).foregroundStyle(Color(hex: "444444")).padding(8)
                    .frame(maxWidth: .infinity, alignment: .leading).background(Color.errnoBackground, in: RoundedRectangle(cornerRadius: 8))
            }
            HStack { Label(job.durationLabel, systemImage: "clock").font(.system(size: 13)); Spacer(); Text(job.payLabel).font(.system(size: 15, weight: .bold)) }
        }.marketplaceCard().foregroundStyle(Color.errnoTextPrimary)
    }
}
