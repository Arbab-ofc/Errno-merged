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
    var latitude: Double?
    var longitude: Double?
    var location = ""
    var pickupLocation = ""
    var dropLocation = ""
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
    // The existing iOS form always collected a future date/time, so preserve that default.
    var isScheduled: Bool = true
    var scheduledStartTime: Date = Date()
    
    // API State
    var isSubmitting: Bool = false
    var errorMessage: String? = nil
    var isSuccess: Bool = false
    private var quoteRequestID = UUID()
    private var pricingQuoteExpectedStart: Date?
    
    private let jobService: JobServiceProtocol
    private let currentUser: User

    private var bookingCalendar: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "Asia/Kolkata") ?? .current
        return calendar
    }
    
    init(jobService: JobServiceProtocol, currentUser: User) {
        self.jobService = jobService
        self.currentUser = currentUser
    }
    
    var isStep1Valid: Bool {
        let trimmedDescription = description.trimmingCharacters(in: .whitespacesAndNewlines)
        let start = bookingCalendar.date(bySettingHour: selectedTime, minute: 0, second: 0, of: scheduledStartTime)
        let dayStart = bookingCalendar.startOfDay(for: Date())
        let latest = bookingCalendar.date(byAdding: .day, value: 6, to: dayStart) ?? Date()
        return !category.rawValue.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !trimmedDescription.isEmpty && trimmedDescription.count <= 250
            && (!isScheduled || ((9...20).contains(selectedTime)
                && scheduledStartTime >= dayStart && scheduledStartTime <= latest
                && (start ?? .distantPast) > Date()))
    }
    
    var isStep3Valid: Bool {
        estimatedDurationHours >= 1 && estimatedDurationHours <= 12 && estimatedDurationHours.rounded() == estimatedDurationHours
            && pricingOptions.contains(where: { Double($0.hours) == estimatedDurationHours })
    }

    var isLocationValid: Bool {
        if category.isDelivery {
            return !pickupLocation.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                && !dropLocation.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }
        return !location.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
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
        guard let pricingQuote else { return !jobService.requiresAuthoritativeQuote }
        guard let expires = Self.parseISODate(pricingQuote.expires_at),
              let quoteStart = Self.parseISODate(pricingQuote.service_start_at),
              let expectedStart = pricingQuoteExpectedStart else { return false }
        return expires > Date() && abs(quoteStart.timeIntervalSince(expectedStart)) < 1
            && pricingQuote.final_service_charge > 0
            && pricingQuote.final_service_charge >= pricingQuote.base_price
            && pricingQuote.final_service_charge <= pricingQuote.maximum_price
    }
    var requiresPricingQuote: Bool { jobService.requiresAuthoritativeQuote }

    func refreshPricingQuote() async {
        guard isStep3Valid else { errorMessage = "Choose a configured duration."; return }
        let requestID = UUID()
        quoteRequestID = requestID
        let draft = makeDraftJob()
        let expectedStart = draft.scheduledStartTime ?? Date()
        isLoadingQuote = true; errorMessage = nil
        defer { if quoteRequestID == requestID { isLoadingQuote = false } }
        do {
            let quote = try await jobService.requestQuote(for: draft)
            guard quoteRequestID == requestID else { return }
            pricingQuote = quote
            pricingQuoteExpectedStart = expectedStart
            if jobService.requiresAuthoritativeQuote && pricingQuote == nil {
                errorMessage = "The backend did not return a valid pricing quote."
            }
        } catch {
            guard quoteRequestID == requestID else { return }
            pricingQuote = nil
            pricingQuoteExpectedStart = nil
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
        guard isStep1Valid else {
            errorMessage = "Enter a job description and choose a future date and valid start time."
            return
        }
        guard isLocationValid else {
            errorMessage = category.isDelivery ? "Enter both pickup and drop-off locations." : "Enter the work address."
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
            scheduledStartTime: isScheduled
                ? bookingCalendar.date(bySettingHour: selectedTime, minute: 0, second: 0, of: scheduledStartTime)
                : Date()
        )
        newJob.bookingType = isScheduled ? "PRE_BOOKING" : "CURRENT"
        newJob.location = location
        newJob.pickupLocation = pickupLocation
        newJob.dropLocation = dropLocation
        newJob.packageType = packageType
        return newJob
    }

    private static func parseISODate(_ value: String) -> Date? {
        let fractional = ISO8601DateFormatter(); fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return fractional.date(from: value) ?? ISO8601DateFormatter().date(from: value)
    }
}
