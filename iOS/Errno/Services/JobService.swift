// JobService.swift
// Errno — Services
//

import Foundation

@MainActor
protocol JobServiceProtocol {
    func fetchShopkeeperJobs(shopOwnerId: UUID) async throws -> [Job]
    func createJob(_ job: Job) async throws -> Job
    func fetchApplications(for jobId: UUID) async throws -> [Application]
    func getWorker(id: UUID) async throws -> User?
    func hireWorker(applicationId: UUID, jobId: UUID) async throws
}

final class MockJobService: JobServiceProtocol {
    // Explicit injection prevents the isolated stores used by the original prototype.
    private let store: LocalMarketplaceStore
    init(store: LocalMarketplaceStore) { self.store = store }
    
    func fetchShopkeeperJobs(shopOwnerId: UUID) async throws -> [Job] {
        try await Task.sleep(for: .milliseconds(800))
        return store.jobs.filter { $0.shopOwnerId == shopOwnerId }
    }
    
    func createJob(_ job: Job) async throws -> Job {
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
