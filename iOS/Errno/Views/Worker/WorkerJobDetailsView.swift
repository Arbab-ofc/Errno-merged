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
                    VStack(alignment: .leading, spacing: 8) {
                        Text(job.title).font(.system(size: 20, weight: .bold))
                        Label("\(job.locationLabel) • \(job.distance)", systemImage: "mappin.and.ellipse").font(.system(size: 13)).foregroundStyle(.gray)
                        Text(job.description).font(.system(size: 14)).foregroundStyle(Color.errnoTextSecondary)
                        Text("Work Location & Route").font(.system(size: 14, weight: .bold))
                        WorkerLocationMapView(locationName: job.locationLabel, distanceText: job.distance, mapHeight: 110)
                        Text("Choose Duration & Pay").font(.system(size: 16, weight: .bold))
                        Text("Select the time you can work").font(.system(size: 12)).foregroundStyle(.gray)
                        Text("Scheduled: \(job.scheduleLabel)").font(.system(size: 12)).foregroundStyle(.gray)
                        if job.status != .open { StatusBadge(text: job.displayStatus) }
                        if let error { Text(error).foregroundStyle(Color.errnoError) }
                    }.marketplaceCard(padding: 12, radius: 20).padding(.horizontal, 12).padding(.vertical, 8)
                } else {
                    MarketplaceEmptyState(title: "Job unavailable", message: "Go back and choose an available job.", dark: true).padding(20)
                }
            }
        }.marketplacePage(dark: true).toolbar(.hidden, for: .navigationBar)
            .safeAreaInset(edge: .bottom, spacing: 0) {
                if let job = store.job(id: jobId), job.status == .open {
                    VStack(spacing: 8) {
                        HStack {
                            Text(job.durationLabel)
                            Spacer()
                            Text(job.payLabel).bold()
                            Image(systemName: selected ? "largecircle.fill.circle" : "circle").foregroundStyle(Color.errnoGreen)
                        }
                        .font(.system(size: 14)).foregroundStyle(Color.errnoTextPrimary)
                        .padding(.horizontal, 12).padding(.vertical, 10)
                        .background(Color.errnoBackground, in: RoundedRectangle(cornerRadius: 10))
                        .accessibilityElement(children: .combine)
                        .accessibilityLabel("\(job.durationLabel), total pay \(job.payLabel), selected")
                        PrimaryButton(title: "Accept Job", style: .dark) {
                            do { try store.accept(jobId: jobId); onAccepted() }
                            catch { self.error = error.localizedDescription }
                        }
                    }.padding(.horizontal, 16).padding(.top, 8).padding(.bottom, 12).background(Color.errnoNavy)
                }
            }
    }
}
