import Foundation

struct Earning: Identifiable, Equatable {
    var id: UUID { jobId }
    let jobId: UUID
    let workerId: UUID
    let title: String
    let hours: Int
    let amount: Double
    let date: Date
}

enum MarketplaceError: LocalizedError {
    case unavailable, invalidPay, missingJob, invalidApplication, unauthorized
    var errorDescription: String? {
        switch self {
        case .unavailable: return "This job is no longer available."
        case .invalidPay: return "Enter a positive duration and total pay."
        case .missingJob: return "This job could not be found."
        case .invalidApplication: return "This application is no longer pending."
        case .unauthorized: return "Sign in with the appropriate role to continue."
        }
    }
}
