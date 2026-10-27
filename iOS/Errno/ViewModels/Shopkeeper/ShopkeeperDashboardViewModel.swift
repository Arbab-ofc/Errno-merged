// ShopkeeperDashboardViewModel.swift
// Errno — ViewModels/Shopkeeper
//
// Manages state for the Shopkeeper Dashboard.

import SwiftUI
import Observation

@Observable
@MainActor
final class ShopkeeperDashboardViewModel {
    var jobs: [Job] = []
    var isLoading: Bool = false
    var errorMessage: String? = nil
    
    private let jobService: JobServiceProtocol
    let currentUser: User
    
    init(jobService: JobServiceProtocol = MockJobService(), currentUser: User? = nil) {
        self.jobService = jobService
        self.currentUser = currentUser ?? MockData.currentUser
    }
    
    func fetchJobs() {
        isLoading = true
        errorMessage = nil
        
        Task {
            do {
                let fetchedJobs = try await jobService.fetchShopkeeperJobs(shopOwnerId: currentUser.id)
                await MainActor.run {
                    self.jobs = fetchedJobs
                    self.isLoading = false
                }
            } catch {
                await MainActor.run {
                    self.errorMessage = "Failed to load jobs: \(error.localizedDescription)"
                    self.isLoading = false
                }
            }
        }
    }
}
