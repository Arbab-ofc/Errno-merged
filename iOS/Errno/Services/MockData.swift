import Foundation

/// Opt-in applicant fixtures, never automatically loaded into a screen or a separate store.
@MainActor
enum MockData {
    static func applicants() -> [User] {
        [User(phone: "9876543211", role: .worker, name: "Amit Kumar", rating: 4.8, totalJobsCompleted: 14),
         User(phone: "9876543212", role: .worker, name: "Ramesh Singh", rating: 4.8, totalJobsCompleted: 14)]
    }
}
