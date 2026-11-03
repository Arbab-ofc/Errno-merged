import SwiftUI

enum WorkerRoute: Hashable {
    case details(UUID)
    case accepting(UUID)
    case verification
}

struct WorkerRootView: View {
    @Environment(AppRouter.self) private var router
    @State private var path: [WorkerRoute] = []
    var body: some View {
        @Bindable var router = router
        NavigationStack(path: $path) {
            TabView(selection: $router.workerTab) {
                WorkerHomeView().tag(0)
                WorkerMyJobsView().tag(1)
                WorkerEarningsView().tag(2)
                WorkerProfileView().tag(3)
            }
            .toolbar(.hidden, for: .tabBar)
            .toolbar(.hidden, for: .navigationBar)
            .safeAreaInset(edge: .bottom, spacing: 0) {
                MarketplaceBottomBar(titles: ["Home", "My Jobs", "Earnings", "Profile"],
                                     icons: ["house.fill", "briefcase.fill", "wallet.pass.fill", "person.fill"],
                                     selection: $router.workerTab, dark: true)
            }
            .navigationDestination(for: WorkerRoute.self) { route in
                switch route {
                case .details(let id): WorkerJobDetailsView(jobId: id) {}
                case .accepting(let id): WorkerAcceptingJobView(jobId: id) { router.workerTab = 1; path.removeAll() }
                case .verification: DigiLockerVerificationView()
                }
            }
        }.tint(.errnoGreen)
            .preferredColorScheme(path.last == .verification ? .light : .dark)
            // White marketplace cards retain their existing content palette.
            .environment(\.colorScheme, .light)
    }
}
