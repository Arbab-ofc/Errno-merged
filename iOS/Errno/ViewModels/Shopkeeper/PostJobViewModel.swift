// PostJobViewModel.swift
// Errno — ViewModels/Shopkeeper
//
// Manages state for the multi-step post job wizard.

import SwiftUI
import Observation
import CoreLocation

@Observable
@MainActor
final class PostJobViewModel {
    // Step 1: Category & Details
    var category: JobCategory = .delivery
    var title: String = ""
    var description: String = ""
    
    // Step 2: Location
    var latitude: Double = 12.9352 // Default to Koramangala
    var longitude: Double = 77.6245
    
    // Step 3: Pay Structure
    var payType: PayType = .fixed
    var payAmountString: String = ""
    var estimatedDurationHours: Double = 1.0
    var isScheduled: Bool = false
    var scheduledStartTime: Date = Date().addingTimeInterval(3600)
    
    // API State
    var isSubmitting: Bool = false
    var errorMessage: String? = nil
    var isSuccess: Bool = false
    
    private let jobService: JobServiceProtocol
    private let currentUser: User
    
    init(jobService: JobServiceProtocol = MockJobService(), currentUser: User? = nil) {
        self.jobService = jobService
        self.currentUser = currentUser ?? MockData.currentUser
    }
    
    var isStep1Valid: Bool {
        !title.isEmpty && !description.isEmpty
    }
    
    var isStep3Valid: Bool {
        if let amount = Double(payAmountString), amount > 0 {
            return true
        }
        return false
    }
    
    func submitJob(onSuccess: @escaping () -> Void) {
        guard let amount = Double(payAmountString) else { return }
        
        isSubmitting = true
        errorMessage = nil
        
        let newJob = Job(
            shopOwnerId: currentUser.id,
            category: category,
            title: title,
            description: description,
            payType: payType,
            payAmount: amount,
            estimatedDurationHours: payType == .hourly ? estimatedDurationHours : nil,
            latitude: latitude,
            longitude: longitude,
            scheduledStartTime: isScheduled ? scheduledStartTime : nil
        )
        
        Task {
            do {
                _ = try await jobService.createJob(newJob)
                await MainActor.run {
                    self.isSubmitting = false
                    self.isSuccess = true
                    onSuccess()
                }
            } catch {
                await MainActor.run {
                    self.isSubmitting = false
                    self.errorMessage = "Failed to post job: \(error.localizedDescription)"
                }
            }
        }
    }
}
