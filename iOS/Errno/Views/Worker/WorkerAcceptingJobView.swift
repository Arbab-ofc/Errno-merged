import SwiftUI

struct WorkerAcceptingJobView: View {
    let jobId: UUID
    let viewJobInfo: () -> Void
    @Environment(LocalMarketplaceStore.self) private var store
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var confirmed = false
    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                Spacer(minLength: 60)
                Image(systemName: "checkmark").font(.system(size: 48, weight: .bold)).foregroundStyle(.white)
                    .frame(width: confirmed ? 80 : 140, height: confirmed ? 80 : 140)
                    .background(confirmed ? Color.errnoGreen : Color(hex: "131F2E"), in: Circle())
                    .overlay(Circle().stroke(Color.errnoGreen, lineWidth: 3))
                Text(confirmed ? "Job Accepted!" : "Accepting Job...").font(.system(size: 24, weight: .bold))
                Text(confirmed ? "Get ready to start your work." : "Please wait while the shop owner gets notified.")
                    .font(.system(size: 14)).foregroundStyle(.white.opacity(0.7))
                MockNotice(text: "Local acceptance simulation • No notification is sent.").padding(.horizontal, 20)
                if confirmed, let job = store.job(id: jobId) {
                    VStack(alignment: .leading, spacing: 16) {
                        Text(job.title).font(.system(size: 18, weight: .bold))
                        Text(job.locationLabel).font(.system(size: 13)).foregroundStyle(.gray)
                        summary("Duration", job.durationLabel)
                        summary("Pay", job.payLabel)
                        summary("Schedule", job.scheduleLabel)
                        Divider()
                        Text("Note: Reach on time and complete your work.").font(.system(size: 12)).foregroundStyle(.gray)
                    }.padding(20).frame(maxWidth: .infinity).background(Color(hex: "131D2A"), in: RoundedRectangle(cornerRadius: 20))
                    PrimaryButton(title: "View Job Info", style: .dark, action: viewJobInfo)
                } else if confirmed {
                    Text("This job is no longer available.")
                    Button("Return to My Jobs", action: viewJobInfo)
                } else { ProgressView().tint(.errnoGreen) }
            }.padding(24)
        }.foregroundStyle(.white).marketplacePage(dark: true).toolbar(.hidden, for: .navigationBar)
            .task {
                do { try await Task.sleep(for: .seconds(2)) } catch { return }
                withAnimation(reduceMotion ? nil : .easeInOut(duration: 0.3)) { confirmed = true }
            }
    }
    private func summary(_ label: String, _ value: String) -> some View {
        HStack { Text(label).foregroundStyle(.gray); Spacer(); Text(value).bold() }.font(.system(size: 13))
    }
}
