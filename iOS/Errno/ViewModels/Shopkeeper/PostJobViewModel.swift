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
    var payAmountString: String = ""
    var estimatedDurationHours: Double = 2.0
    var pricingOptions: [(hours: Int, maximum: Decimal)] = []
    var pricingQuote: PricingQuoteResponse?
    var isLoadingQuote = false
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
        estimatedDurationHours >= 1 && estimatedDurationHours <= 12 && estimatedDurationHours.rounded() == estimatedDurationHours
    }

    func loadPricingOptions() async {
        do {
            let repository = try AppDependencies.backendRepository()
            pricingOptions = try await repository.pricingDurations().filter { $0.enabled && $0.approval_status == "approved" }
                .compactMap { row in row.maximum_price.map { (hours: row.duration_hours, maximum: $0) } }
            if let first = pricingOptions.first, !pricingOptions.contains(where: { Double($0.hours) == estimatedDurationHours }) {
                estimatedDurationHours = Double(first.hours)
            }
        } catch { errorMessage = error.localizedDescription }
    }

    var hasValidQuote: Bool {
        guard let pricingQuote, let expires = Self.parseISODate(pricingQuote.expires_at) else { return !jobService.requiresAuthoritativeQuote }
        return expires > Date()
    }
    var requiresPricingQuote: Bool { jobService.requiresAuthoritativeQuote }

    func refreshPricingQuote() async {
        guard isStep3Valid else { errorMessage = "Choose a configured duration."; return }
        isLoadingQuote = true; errorMessage = nil
        defer { isLoadingQuote = false }
        do {
            pricingQuote = try await jobService.requestQuote(for: makeDraftJob())
            if jobService.requiresAuthoritativeQuote && pricingQuote == nil {
                errorMessage = "The backend did not return a valid pricing quote."
            }
        } catch {
            pricingQuote = nil
            errorMessage = error.localizedDescription
        }
    }
    
    func submitJob(onSuccess: @escaping () -> Void) {
        guard !isSubmitting else { return }
        if postedJob != nil { onSuccess(); return }
        guard isStep3Valid else {
            errorMessage = "Choose a configured duration."
            return
        }
        if jobService.requiresAuthoritativeQuote && !hasValidQuote {
            errorMessage = "This quote has expired or is unavailable. Refresh the quote before confirming."
            pricingQuote = nil
            return
        }
        
        isSubmitting = true
        errorMessage = nil
        
        let submittedJob = makeDraftJob()
        Task {
            do {
                let created = try await jobService.createJob(submittedJob, quote: pricingQuote)
                await MainActor.run {
                    self.isSubmitting = false
                    self.isSuccess = true
                    self.postedJob = created
                    self.payAmountString = String(format: "%.2f", created.payAmount)
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

    private func makeDraftJob() -> Job {
        var newJob = Job(
            id: draftId,
            shopOwnerId: currentUser.id,
            category: category,
            title: category.rawValue,
            description: description.isEmpty ? "Deliver parcel/products safely." : description,
            payType: .fixed,
            payAmount: 0,
            estimatedDurationHours: estimatedDurationHours,
            latitude: latitude,
            longitude: longitude,
            scheduledStartTime: Calendar.current.date(bySettingHour: selectedTime, minute: 0, second: 0, of: scheduledStartTime)
        )
        newJob.location = location.isEmpty ? "Okhla Market Area" : location
        newJob.pickupLocation = pickupLocation.isEmpty ? "Pickup Store" : pickupLocation
        newJob.dropLocation = dropLocation.isEmpty ? "Drop Address" : dropLocation
        newJob.packageType = packageType
        return newJob
    }

    private static func parseISODate(_ value: String) -> Date? {
        let fractional = ISO8601DateFormatter(); fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return fractional.date(from: value) ?? ISO8601DateFormatter().date(from: value)
    }
}
