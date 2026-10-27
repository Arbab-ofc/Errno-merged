// Job.swift
// Errno — Models
//
// Core Job model, maps to Supabase "jobs" table.

import Foundation
import CoreLocation

enum JobCategory: String, Codable, CaseIterable, Hashable, Sendable {
    case delivery = "Delivery"
    case shopHelper = "Shop Helper"
    case loading = "Loading/Unloading"
    case cleaning = "Cleaning"
    case other = "Other"
    
    var icon: String {
        switch self {
        case .delivery: return "box.truck.fill"
        case .shopHelper: return "cart.fill"
        case .loading: return "shippingbox.fill"
        case .cleaning: return "sparkles"
        case .other: return "briefcase.fill"
        }
    }
}

enum JobStatus: String, Codable, Hashable, Sendable {
    case open
    case inProgress
    case completed
    case cancelled
}

enum PayType: String, Codable, Hashable, Sendable {
    case fixed
    case hourly
}

struct Job: Identifiable, Codable, Hashable, Sendable {
    let id: UUID
    let shopOwnerId: UUID
    var category: JobCategory
    var title: String
    var description: String
    var payType: PayType
    var payAmount: Double
    var estimatedDurationHours: Double?
    var latitude: Double
    var longitude: Double
    var status: JobStatus
    var createdAt: Date
    var scheduledStartTime: Date?
    
    // Derived properties
    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
    
    // MARK: - Initializer for Mock Data
    init(id: UUID = UUID(), shopOwnerId: UUID, category: JobCategory, title: String, description: String, payType: PayType, payAmount: Double, estimatedDurationHours: Double? = nil, latitude: Double, longitude: Double, status: JobStatus = .open, createdAt: Date = Date(), scheduledStartTime: Date? = nil) {
        self.id = id
        self.shopOwnerId = shopOwnerId
        self.category = category
        self.title = title
        self.description = description
        self.payType = payType
        self.payAmount = payAmount
        self.estimatedDurationHours = estimatedDurationHours
        self.latitude = latitude
        self.longitude = longitude
        self.status = status
        self.createdAt = createdAt
        self.scheduledStartTime = scheduledStartTime
    }
}
