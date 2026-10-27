import SwiftUI

struct ShopkeeperRootView: View {
    @Environment(AppRouter.self) private var router
    @Environment(LocalMarketplaceStore.self) private var store
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
    }
}
