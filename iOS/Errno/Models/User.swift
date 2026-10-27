// User.swift
// Errno — Models
//

import Foundation

struct User: Identifiable, Codable, Hashable, Sendable {
    let id: UUID
    var phone: String
    var role: UserRole
    var name: String
    var shopName: String? // Only for Shopkeeper
    var avatarUrl: String?
    var rating: Double?
    var totalJobsCompleted: Int?
    
    // MARK: - Initializer for Mock Data
    init(id: UUID = UUID(), phone: String, role: UserRole, name: String, shopName: String? = nil, avatarUrl: String? = nil, rating: Double? = nil, totalJobsCompleted: Int? = nil) {
        self.id = id
        self.phone = phone
        self.role = role
        self.name = name
        self.shopName = shopName
        self.avatarUrl = avatarUrl
        self.rating = rating
        self.totalJobsCompleted = totalJobsCompleted
    }
}
