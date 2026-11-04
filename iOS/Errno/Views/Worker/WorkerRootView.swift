import SwiftUI

enum WorkerRoute: Hashable {
    case details(UUID)
    case accepting(UUID)
    case verification
}

struct WorkerRootView: View {
    @Environment(AppRouter.self) private var router
    @State private var path: [WorkerRoute] = []
    @State private var notificationsPresented = false
    @State private var unreadNotifications = 0
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
            .overlay(alignment: .topTrailing) { Button { notificationsPresented = true } label: { Image(systemName:unreadNotifications > 0 ? "bell.badge.fill" : "bell").font(.title3).padding(12).background(.ultraThinMaterial, in: Circle()).overlay(alignment:.topTrailing) { if unreadNotifications>0 { Text(unreadNotifications>99 ? "99+" : "\(unreadNotifications)").font(.caption2).padding(4).background(.red,in:Capsule()).offset(x:4,y:-4) } } }.padding(.top, 8).padding(.trailing, 16).accessibilityLabel("Notifications, \(unreadNotifications) unread") }
            .sheet(isPresented:$notificationsPresented) { NotificationInboxView() }
            .onReceive(NotificationCenter.default.publisher(for:.errnoNotificationTapped)) { _ in notificationsPresented = true; UserDefaults.standard.removeObject(forKey:"errno.notifications.pending-route") }
            .task { unreadNotifications = (try? await ErrnoNotifications.unreadCount()) ?? 0; if UserDefaults.standard.string(forKey:"errno.notifications.pending-route") != nil { notificationsPresented = true; UserDefaults.standard.removeObject(forKey:"errno.notifications.pending-route") } }
            .preferredColorScheme(path.last == .verification ? .light : .dark)
            // White marketplace cards retain their existing content palette.
            .environment(\.colorScheme, .light)
    }
}
