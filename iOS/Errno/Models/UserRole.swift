// UserRole.swift
// Errno — Models
//
// Shared role enum used across auth, navigation, and dashboard flows.

import Foundation

enum UserRole: String, Codable, CaseIterable, Hashable, Sendable {
    case shopkeeper
    case worker

    // MARK: — Display

    var displayName: String {
        switch self {
        case .shopkeeper: "Shop Owner"
        case .worker:     "Worker"
        }
    }

    var shortName: String {
        switch self {
        case .shopkeeper: "Shopkeeper"
        case .worker:     "Worker"
        }
    }

    var description: String {
        switch self {
        case .shopkeeper: "Post jobs, hire workers, and manage your shop."
        case .worker:     "Find nearby gigs, accept shifts, and get paid."
        }
    }

    var tagline: String {
        switch self {
        case .shopkeeper: "Hire. Manage. Grow."
        case .worker:     "Find. Work. Earn."
        }
    }

    /// SF Symbol name for this role
    var icon: String {
        switch self {
        case .shopkeeper: "storefront.fill"
        case .worker:     "person.badge.clock.fill"
        }
    }
}
