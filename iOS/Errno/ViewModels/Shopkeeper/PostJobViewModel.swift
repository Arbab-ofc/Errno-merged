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
    var title: String = "Delivery Partner"
    var description: String = "Deliver parcel/products safely from shop to target location."
    
    // Step 2: Location
    var latitude: Double = 28.5355
    var longitude: Double = 77.2641
    var location = "Okhla Market Area"
    var pickupLocation = "Okhla Market Store #12"
    var dropLocation = "Sector 18 Noida"
    var packageType = "Parcel / Product Box"
    var selectedTime = 13
    let draftId = UUID()
    var postedJob: Job?
    
    // Step 3: Pay Structure
    var payType: PayType = .fixed
    var payAmountString: String = "249"
    var estimatedDurationHours: Double = 2.0
    var isScheduled: Bool = false
    var scheduledStartTime: Date = Date()
    
    // API State
    var isSubmitting: Bool = false
    var errorMessage: String? = nil
    var isSuccess: Bool = false
    
    private let jobService: JobServiceProtocol
    private let currentUser: User
    
    init(jobService: JobServiceProtocol, currentUser: User) {
        self.jobService = jobService
        self.currentUser = currentUser
    }
    
    var isStep1Valid: Bool {
        true // Android permits progression and supplies fallback text on submission.
    }
    
    var isStep3Valid: Bool {
        if let amount = Double(payAmountString), amount > 0 {
            return true
        }
        return false
    }
    
    func submitJob(onSuccess: @escaping () -> Void) {
        guard !isSubmitting else { return }
        if postedJob != nil { onSuccess(); return }
        guard let amount = Double(payAmountString), amount.isFinite, amount > 0, amount < Double(Int.max),
              estimatedDurationHours.isFinite, estimatedDurationHours > 0, estimatedDurationHours < Double(Int.max) else {
            errorMessage = "Enter a positive duration and total pay."
            return
        }
        
        isSubmitting = true
        errorMessage = nil
        
        var newJob = Job(
            id: draftId,
            shopOwnerId: currentUser.id,
            category: category,
            title: category.rawValue,
            description: description.isEmpty ? "Deliver parcel/products safely." : description,
            payType: .fixed,
            payAmount: amount,
            estimatedDurationHours: estimatedDurationHours,
            latitude: latitude,
            longitude: longitude,
            scheduledStartTime: Calendar.current.date(bySettingHour: selectedTime, minute: 0, second: 0, of: scheduledStartTime)
        )
        newJob.location = location.isEmpty ? "Okhla Market Area" : location
        newJob.pickupLocation = pickupLocation.isEmpty ? "Pickup Store" : pickupLocation
        newJob.dropLocation = dropLocation.isEmpty ? "Drop Address" : dropLocation
        newJob.packageType = packageType
        let submittedJob = newJob
        
        Task {
            do {
                let created = try await jobService.createJob(submittedJob)
                await MainActor.run {
                    self.isSubmitting = false
                    self.isSuccess = true
                    self.postedJob = created
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
