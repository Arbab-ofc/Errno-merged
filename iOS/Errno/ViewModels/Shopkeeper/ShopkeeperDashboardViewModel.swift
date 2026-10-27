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
    init(store: LocalMarketplaceStore) { self.store = store }
    func fetchJobs() { errorMessage = nil } // Local reads are synchronous in Phase 1.
}
