import SwiftUI
import Observation

/// Projection over the shared sandbox; tab changes never create another job store.
@Observable
@MainActor
final class ShopkeeperDashboardViewModel {
    let store: LocalMarketplaceStore
    var jobs: [Job] { store.ownerJobs }
    var currentUser: User { store.shopkeeper }
    var isLoading = false
    var errorMessage: String?
    private let repository: BackendRepository?
    init(store: LocalMarketplaceStore) { self.store = store; repository = try? AppDependencies.backendRepository() }
    func fetchJobs() async {
        isLoading = true; errorMessage = nil
        defer { isLoading = false }
        do {
            guard let repository else { throw APIError.configuration }
            let rows = try await repository.myJobs()
            store.installBackendJobs(rows)
            if let shop = try await repository.shop() {
                store.updateRemoteShop(name: shop.shop_name, address: shop.address ?? "", category: shop.category)
            }
        } catch { errorMessage = error.localizedDescription }
    }
}
