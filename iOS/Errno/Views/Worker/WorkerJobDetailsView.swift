import SwiftUI

struct WorkerJobDetailsView: View {
    let jobId: UUID
    var onAccepted: () -> Void
    @Environment(LocalMarketplaceStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var error: String?
    @State private var selected = true
    var body: some View {
        VStack(spacing: 0) {
            MarketplaceHeader(title: "Job Details", dark: true, back: { dismiss() })
            ScrollView {
                if let job = store.job(id: jobId) {
                    VStack(alignment: .leading, spacing: 16) {
                        Text(job.title).font(.system(size: 20, weight: .bold))
                        Label("\(job.locationLabel) • \(job.distance)", systemImage: "mappin.and.ellipse").font(.system(size: 13)).foregroundStyle(.gray)
                        Text(job.description).font(.system(size: 14)).foregroundStyle(Color.errnoTextSecondary)
                        Text("Work Location & Route").font(.system(size: 14, weight: .bold))
                        WorkerLocationMapView(locationName: job.locationLabel, distanceText: job.distance)
                        Text("Choose Duration & Pay").font(.system(size: 16, weight: .bold))
                        Text("Select the time you can work").font(.system(size: 12)).foregroundStyle(.gray)
                        Button { selected = true } label: {
                            HStack { Text(job.durationLabel); Spacer(); Text(job.payLabel).bold(); Image(systemName: selected ? "largecircle.fill.circle" : "circle").foregroundStyle(Color.errnoGreen) }
                                .font(.system(size: 14)).foregroundStyle(Color.errnoTextPrimary).padding(.vertical, 12)
                        }.accessibilityLabel("\(job.durationLabel), total pay \(job.payLabel), selected")
                        Text("Scheduled: \(job.scheduleLabel)").font(.system(size: 12)).foregroundStyle(.gray)
                        if job.status != .open { StatusBadge(text: job.displayStatus) }
                        if let error { Text(error).foregroundStyle(Color.errnoError) }
                    }.marketplaceCard(padding: 20, radius: 20).padding(20)
                } else {
                    MarketplaceEmptyState(title: "Job unavailable", message: "Go back and choose an available job.", dark: true).padding(20)
                }
            }
        }.marketplacePage(dark: true).toolbar(.hidden, for: .navigationBar)
            .safeAreaInset(edge: .bottom) {
                if let job = store.job(id: jobId), job.status == .open {
                    PrimaryButton(title: "Accept Job", style: .dark) {
                        do { try store.accept(jobId: jobId); onAccepted() }
                        catch { self.error = error.localizedDescription }
                    }.padding(16).background(Color.errnoNavy)
                }
            }
    }
}
