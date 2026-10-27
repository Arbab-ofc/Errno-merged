// JobService.swift
// Errno — Services
//
// Protocol-backed mock job service. Swap to SupabaseJobService later.

import Foundation

protocol JobServiceProtocol: Sendable {
    func fetchShopkeeperJobs(shopOwnerId: UUID) async throws -> [Job]
    func createJob(_ job: Job) async throws -> Job
    func fetchApplications(for jobId: UUID) async throws -> [Application]
    func getWorker(id: UUID) async throws -> User?
    func hireWorker(applicationId: UUID, jobId: UUID) async throws
}

final class MockJobService: JobServiceProtocol, @unchecked Sendable {
    nonisolated init() {}
    
    private var jobs = MockData.jobs
    private var applications = MockData.applications
    private let workers = MockData.workers
    
    func fetchShopkeeperJobs(shopOwnerId: UUID) async throws -> [Job] {
        try await Task.sleep(for: .milliseconds(800))
        return jobs.filter { $0.shopOwnerId == shopOwnerId }
    }
    
    func createJob(_ job: Job) async throws -> Job {
        try await Task.sleep(for: .milliseconds(1000))
        let newJob = job
        // In real life, DB assigns ID and createdAt, but for mock we just use what's passed
        jobs.append(newJob)
        return newJob
    }
    
    func fetchApplications(for jobId: UUID) async throws -> [Application] {
        try await Task.sleep(for: .milliseconds(600))
        return applications.filter { $0.jobId == jobId }
    }
    
    func getWorker(id: UUID) async throws -> User? {
        // Synchronous mock lookup
        return workers.first { $0.id == id }
    }
    
    func hireWorker(applicationId: UUID, jobId: UUID) async throws {
        try await Task.sleep(for: .milliseconds(1000))
        
        // Mark application as accepted
        if let appIndex = applications.firstIndex(where: { $0.id == applicationId }) {
            applications[appIndex].status = .accepted
        }
        
        // Reject all other applications for this job
        for i in applications.indices where applications[i].jobId == jobId && applications[i].id != applicationId {
            applications[i].status = .rejected
        }
        
        // Mark job as inProgress
        if let jobIndex = jobs.firstIndex(where: { $0.id == jobId }) {
            jobs[jobIndex].status = .inProgress
        }
    }
}
