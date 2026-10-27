// Application.swift
// Errno — Models
//
// Represents a Worker applying for a Job.

import Foundation

enum ApplicationStatus: String, Codable, Hashable, Sendable {
    case pending
    case accepted
    case rejected
    case completed
}

struct Application: Identifiable, Codable, Hashable, Sendable {
    let id: UUID
    let jobId: UUID
    let workerId: UUID
    var status: ApplicationStatus
    var appliedAt: Date
    
    // MARK: - Initializer for Mock Data
    init(id: UUID = UUID(), jobId: UUID, workerId: UUID, status: ApplicationStatus = .pending, appliedAt: Date = Date()) {
        self.id = id
        self.jobId = jobId
        self.workerId = workerId
        self.status = status
        self.appliedAt = appliedAt
    }
}
