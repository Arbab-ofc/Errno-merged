// MockData.swift
// Errno — Services
//
// Static seed data for mock services.

import Foundation
import CoreLocation

@MainActor
enum MockData {
    // Current user (mocked as shopkeeper for Phase 3)
    static let currentUser = User(
        id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!,
        phone: "9876543210",
        role: .shopkeeper,
        name: "Ramesh Kumar",
        shopName: "Ramesh Provisions",
        rating: 4.8
    )

    static let workers: [User] = [
        User(id: UUID(uuidString: "11111111-0000-0000-0000-000000000001")!, phone: "9000000001", role: .worker, name: "Suresh", rating: 4.9, totalJobsCompleted: 45),
        User(id: UUID(uuidString: "11111111-0000-0000-0000-000000000002")!, phone: "9000000002", role: .worker, name: "Amit", rating: 4.5, totalJobsCompleted: 12),
        User(id: UUID(uuidString: "11111111-0000-0000-0000-000000000003")!, phone: "9000000003", role: .worker, name: "Raju", rating: 4.7, totalJobsCompleted: 89)
    ]

    static var jobs: [Job] = [
        Job(
            id: UUID(uuidString: "22222222-0000-0000-0000-000000000001")!,
            shopOwnerId: currentUser.id,
            category: .delivery,
            title: "Local Delivery",
            description: "Need someone to deliver 5 packages to nearby addresses in Koramangala.",
            payType: .fixed,
            payAmount: 300,
            estimatedDurationHours: 2.5,
            latitude: 12.9352,
            longitude: 77.6245,
            status: .open,
            scheduledStartTime: Date().addingTimeInterval(3600) // 1 hour from now
        ),
        Job(
            id: UUID(uuidString: "22222222-0000-0000-0000-000000000002")!,
            shopOwnerId: currentUser.id,
            category: .shopHelper,
            title: "Store Assistant",
            description: "Help organize inventory and attend to customers for the evening shift.",
            payType: .hourly,
            payAmount: 100, // per hour
            estimatedDurationHours: 4,
            latitude: 12.9352,
            longitude: 77.6245,
            status: .inProgress,
            scheduledStartTime: Date().addingTimeInterval(-3600) // started 1 hour ago
        )
    ]

    static var applications: [Application] = [
        Application(
            id: UUID(),
            jobId: UUID(uuidString: "22222222-0000-0000-0000-000000000001")!,
            workerId: workers[0].id,
            status: .pending
        ),
        Application(
            id: UUID(),
            jobId: UUID(uuidString: "22222222-0000-0000-0000-000000000001")!,
            workerId: workers[1].id,
            status: .pending
        ),
        Application(
            id: UUID(),
            jobId: UUID(uuidString: "22222222-0000-0000-0000-000000000002")!,
            workerId: workers[2].id,
            status: .accepted
        )
    ]
}
