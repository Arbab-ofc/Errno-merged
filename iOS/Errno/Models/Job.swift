// Job.swift
// Errno — Models
//

import Foundation
import CoreLocation

enum JobCategory: String, Codable, CaseIterable, Hashable, Sendable {
    case delivery = "Delivery Partner"
    case shopHelper = "Shop Helper"
    case loading = "Loading/Unloading"
    case cleaning = "Cleaning"
    case other = "Other"
    case counterStaff = "Counter Staff"
    case storeAssistant = "Store Assistant"
    case packingStaff = "Packing Staff"
    case deliveryBoy = "Delivery Boy"
    case cashier = "Cashier"

    static var marketplaceCategories: [JobCategory] {
        [.delivery, .shopHelper, .counterStaff, .storeAssistant, .packingStaff, .deliveryBoy, .cashier]
    }
    var isDelivery: Bool { self == .delivery || self == .deliveryBoy }
    
    var icon: String {
        switch self {
        case .delivery: return "box.truck.fill"
        case .shopHelper: return "cart.fill"
        case .loading: return "shippingbox.fill"
        case .cleaning: return "sparkles"
        case .other: return "briefcase.fill"
        case .counterStaff, .cashier: return "creditcard.fill"
        case .storeAssistant, .packingStaff: return "shippingbox.fill"
        case .deliveryBoy: return "bicycle"
        }
    }
}

enum JobStatus: String, Codable, Hashable, Sendable {
    case open
    case assigned
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
    var location = "Okhla Market Area"
    var pickupLocation = "Okhla Market Store #12"
    var dropLocation = "Sector 18 Noida"
    var packageType = "Parcel / Product Box"
    var distance = "1.2 km away" // Schematic frontend distance, not measured GPS.
    var assignedWorkerId: UUID?
    var workerRating = 0
    var shopkeeperRating = 0
    var workerReview = ""
    var shopkeeperReview = ""

    var isDelivery: Bool { category.isDelivery }
    var locationLabel: String { isDelivery ? "\(pickupLocation) → \(dropLocation)" : location }
    var durationLabel: String { "\(Int(estimatedDurationHours ?? 2)) Hours" }
    var payLabel: String { "₹\(Int(payAmount))" }
    var scheduleLabel: String {
        guard let date = scheduledStartTime else { return "Today" }
        return date.formatted(date: .abbreviated, time: .shortened)
    }
    var displayStatus: String {
        switch status {
        case .open: return "Active"
        case .assigned: return "Worker Assigned"
        case .inProgress: return "In Progress"
        case .completed: return "Work Completed"
        case .cancelled: return "Cancelled"
        }
    }
    
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
