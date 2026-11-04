// JobService.swift
// Errno — Services
//

import Foundation

@MainActor
protocol JobServiceProtocol {
    func fetchShopkeeperJobs(shopOwnerId: UUID) async throws -> [Job]
    var requiresAuthoritativeQuote: Bool { get }
    func requestQuote(for job: Job) async throws -> PricingQuoteResponse?
    func createJob(_ job: Job, quote: PricingQuoteResponse?) async throws -> Job
    func fetchApplications(for jobId: UUID) async throws -> [Application]
    func getWorker(id: UUID) async throws -> User?
    func hireWorker(applicationId: UUID, jobId: UUID) async throws
}

final class MockJobService: JobServiceProtocol {
    // Explicit injection prevents the isolated stores used by the original prototype.
    private let store: LocalMarketplaceStore
    init(store: LocalMarketplaceStore) { self.store = store }
    var requiresAuthoritativeQuote: Bool { false }
    
    func fetchShopkeeperJobs(shopOwnerId: UUID) async throws -> [Job] {
        try await Task.sleep(for: .milliseconds(800))
        return store.jobs.filter { $0.shopOwnerId == shopOwnerId }
    }
    
    func requestQuote(for job: Job) async throws -> PricingQuoteResponse? { nil }
    func createJob(_ job: Job, quote: PricingQuoteResponse?) async throws -> Job {
        try await Task.sleep(for: .milliseconds(1000))
        return try store.post(job)
    }
    
    func fetchApplications(for jobId: UUID) async throws -> [Application] {
        try await Task.sleep(for: .milliseconds(600))
        return store.applications.filter { $0.jobId == jobId }
    }
    
    func getWorker(id: UUID) async throws -> User? {
        // Synchronous mock lookup
        return store.user(id: id)
    }
    
    func hireWorker(applicationId: UUID, jobId: UUID) async throws {
        try await Task.sleep(for: .milliseconds(1000))
        
        try store.hire(applicationId: applicationId, jobId: jobId)
    }
}

/// Production workflow adapter. Remote state is authoritative; the observable store is only a UI cache.
@MainActor
final class BackendJobService: JobServiceProtocol {
    private let store: LocalMarketplaceStore
    private let repository: BackendRepository?
    init(store: LocalMarketplaceStore) {
        self.store = store
        repository = try? AppDependencies.backendRepository()
    }
    var requiresAuthoritativeQuote: Bool { true }
    func fetchShopkeeperJobs(shopOwnerId: UUID) async throws -> [Job] {
        guard let repository else { throw APIError.configuration }
        let rows = try await repository.myJobs()
        store.installBackendJobs(rows, ownerID: shopOwnerId)
        return store.ownerJobs
    }
    func requestQuote(for job: Job) async throws -> PricingQuoteResponse? {
        guard let repository else { throw APIError.configuration }
        guard let hours = job.estimatedDurationHours, hours >= 1, hours <= 12 else { throw APIError.invalidInput }
        let serviceTime = job.scheduledStartTime ?? Date()
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let area = job.isDelivery ? job.pickupLocation : job.location
        return try await repository.pricingQuote(PricingQuoteRequest(duration_hours: Int(hours), service_start_at: iso.string(from: serviceTime), area_id: area))
    }
    func createJob(_ job: Job, quote: PricingQuoteResponse?) async throws -> Job {
        guard let repository else { throw APIError.configuration }
        guard let hours = job.estimatedDurationHours, hours >= 1, hours <= 12,
              let quote, !quote.quote_id.isEmpty else { throw APIError.invalidInput }
        if let expiration = ISO8601DateFormatter().date(from: quote.expires_at), expiration <= Date() { throw APIError.validation }
        let body = CreateJobRequest(title: job.title, category: job.category.rawValue, description: job.description,
                                    pay_amount: NSDecimalNumber(decimal: quote.final_service_charge).doubleValue, duration_type: "\(Int(hours)) hours",
                                    scheduled_date: job.scheduleLabel, location: job.location, latitude: job.latitude, longitude: job.longitude,
                                    pickup_location: job.pickupLocation, drop_location: job.dropLocation, is_delivery: job.isDelivery,
                                    quote_id: quote.quote_id, service_start_at: quote.service_start_at)
        let row = try await repository.createJob(body)
        guard let id = UUID(uuidString: row.id) else { throw APIError.decoding }
        let persisted = Job(id: id, shopOwnerId: job.shopOwnerId, category: JobCategory(rawValue: row.category ?? "") ?? .other,
                            title: row.title, description: row.description ?? "", payType: .fixed, payAmount: row.pay_amount,
                            estimatedDurationHours: job.estimatedDurationHours, latitude: job.latitude, longitude: job.longitude)
        store.installBackendJobs([row], ownerID: job.shopOwnerId)
        return persisted
    }
    func fetchApplications(for jobId: UUID) async throws -> [Application] {
        guard let repository else { throw APIError.configuration }
        let rows = try await repository.applications(jobID: jobId.uuidString)
        return rows.compactMap { row in
            guard let id = UUID(uuidString: row.id), let worker = UUID(uuidString: row.worker_id), let job = UUID(uuidString: row.job_id),
                  let status = ApplicationStatus(rawValue: row.status) else { return nil }
            return Application(id: id, jobId: job, workerId: worker, status: status)
        }
    }
    func getWorker(id: UUID) async throws -> User? { store.user(id: id) }
    func hireWorker(applicationId: UUID, jobId: UUID) async throws {
        guard let repository else { throw APIError.configuration }
        _ = try await repository.decide(jobID: jobId.uuidString, applicationID: applicationId.uuidString, decision: "accepted")
    }
}
