import SwiftUI

struct ShopkeeperRootView: View {
    @Environment(AppRouter.self) private var router
    @Environment(LocalMarketplaceStore.self) private var store
    @State private var notificationsPresented = false
    @State private var unreadNotifications = 0
    var body: some View {
        @Bindable var router = router
        TabView(selection: $router.shopkeeperTab) {
            ShopkeeperDashboardView(store: store).tag(0)
            NavigationStack { ShopkeeperJobsView(store: store) }.tag(1)
            NavigationStack { ApplicationsRootView() }.tag(2)
            NavigationStack { ShopkeeperProfileView() }.tag(3)
        }
        .toolbar(.hidden, for: .tabBar)
        .safeAreaInset(edge: .bottom, spacing: 0) {
            MarketplaceBottomBar(titles: ["Home", "Jobs", "Applications", "Profile"],
                                 icons: ["house.fill", "briefcase.fill", "person.2.fill", "person.fill"], selection: $router.shopkeeperTab)
        }
        .overlay(alignment: .topTrailing) {
            Button { notificationsPresented = true } label: {
                Image(systemName: unreadNotifications > 0 ? "bell.badge.fill" : "bell")
                    .font(.title3).padding(12).background(.ultraThinMaterial, in: Circle())
                    .overlay(alignment: .topTrailing) {
                        if unreadNotifications > 0 {
                            Text(unreadNotifications > 99 ? "99+" : "\(unreadNotifications)")
                                .font(.caption2).padding(4).background(.red, in: Capsule()).offset(x:4,y:-4)
                        }
                    }
            }
            .padding(.top,8).padding(.trailing,16).accessibilityLabel("Notifications, \(unreadNotifications) unread")
        }
        .sheet(isPresented:$notificationsPresented) { NotificationInboxView() }
        .onReceive(NotificationCenter.default.publisher(for:.errnoNotificationTapped)) { _ in notificationsPresented = true; UserDefaults.standard.removeObject(forKey:"errno.notifications.pending-route") }
        .task { unreadNotifications = (try? await ErrnoNotifications.unreadCount()) ?? 0; if UserDefaults.standard.string(forKey:"errno.notifications.pending-route") != nil { notificationsPresented = true; UserDefaults.standard.removeObject(forKey:"errno.notifications.pending-route") } }
    }
}
