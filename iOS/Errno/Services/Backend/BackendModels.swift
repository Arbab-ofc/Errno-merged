import Foundation

nonisolated struct SendOTPRequest: Codable, Sendable {
    let phone_number: String
    let role: String?
}
nonisolated struct SendOTPResponse: Decodable, Sendable {
    let success: Bool
    let message: String
    // Deliberately discard otp_demo. It is never displayed or used as proof of identity.
}
nonisolated struct VerifyOTPRequest: Codable, Sendable {
    let phone_number: String
    let otp_code: String
}
nonisolated struct RegisterRequest: Codable, Sendable {
    let full_name: String
    let phone_number: String
    let role: String
}
nonisolated struct BackendUser: Codable, Sendable, Equatable {
    let id: String
    let full_name: String?
    let phone_number: String
    let role: String
    let is_phone_verified: Bool
}
nonisolated struct AuthResponse: Decodable, Sendable {
    let success: Bool
    let token: String?
    let message: String?
    let user: BackendUser?
}
nonisolated struct FirebaseUserProfile: Decodable, Sendable {
    let id: String
    let firebase_uid: String
    let name: String?
    let email: String?
    let phone_number: String?
    let role: String?
    let onboarding_completed: Bool
}
nonisolated struct FirebaseLoginResponse: Decodable, Sendable {
    let success: Bool
    let user: FirebaseUserProfile
}
nonisolated struct BackendShop: Codable, Sendable {
    let id: String
    let owner_id: String
    let shop_name: String
    let address: String?
    let category: String?
}
nonisolated struct UpdateShopRequest: Codable, Sendable {
    let shop_name: String
    let address: String?
    let category: String?
}
nonisolated struct CreateJobRequest: Codable, Sendable {
    let title: String
    let category: String?
    let description: String?
    let pay_amount: Double
    let duration_type: String
    let scheduled_date: String?
    let location: String?
    let pickup_location: String?
    let drop_location: String?
    let is_delivery: Bool
}
nonisolated struct BackendJob: Codable, Sendable, Identifiable {
    let id: String
    let shop_id: String?
    let title: String
    let category: String?
    let description: String?
    let pay_amount: Double
    let duration_type: String
    let scheduled_date: String?
    let location: String?
    let pickup_location: String?
    let drop_location: String?
    let is_delivery: Bool
    let status: String
    let assigned_worker_id: String?
}
nonisolated struct BackendApplication: Codable, Sendable {
    let id: String
    let job_id: String
    let worker_id: String
    let status: String
}

/// Mirrors existing routes. Definitions do not imply that a route is secure or operational.
nonisolated enum BackendEndpoints {
    static func firebaseLogin(token: String) -> APIEndpoint {
        APIEndpoint(method: "POST", path: ["api", "v1", "auth", "firebase"], bearerToken: token)
    }
    static func logout(token: String) -> APIEndpoint {
        APIEndpoint(method: "POST", path: ["api", "v1", "auth", "logout"], bearerToken: token)
    }
    static func currentUser(token: String) -> APIEndpoint {
        APIEndpoint(method: "GET", path: ["api", "v1", "users", "me"], bearerToken: token)
    }
    static func jobs(status: String? = nil) -> APIEndpoint {
        APIEndpoint(method: "GET", path: ["jobs"], query: status.map { [URLQueryItem(name: "status_filter", value: $0)] } ?? [])
    }
    static func job(id: String) -> APIEndpoint { APIEndpoint(method: "GET", path: ["jobs", id]) }
    static func sendOTP(_ body: SendOTPRequest) throws -> APIEndpoint { try .json("POST", ["auth", "send-otp"], body: body) }
    static func verifyOTP(_ body: VerifyOTPRequest) throws -> APIEndpoint { try .json("POST", ["auth", "verify-otp"], body: body) }
    static func register(_ body: RegisterRequest) throws -> APIEndpoint { try .json("POST", ["auth", "register"], body: body) }
    static func profile(phone: String) -> APIEndpoint { APIEndpoint(method: "GET", path: ["auth", "me", phone]) }
    static func shop(phone: String) -> APIEndpoint { APIEndpoint(method: "GET", path: ["shops", "me", phone]) }
    static func updateShop(phone: String, body: UpdateShopRequest) throws -> APIEndpoint { try .json("PATCH", ["shops", "me", phone], body: body) }
    static func createJob(ownerPhone: String, body: CreateJobRequest) throws -> APIEndpoint {
        var endpoint = try APIEndpoint.json("POST", ["jobs"], body: body)
        endpoint.query = [URLQueryItem(name: "owner_phone", value: ownerPhone)]
        return endpoint
    }
    static func apply(jobID: String, workerPhone: String) -> APIEndpoint {
        APIEndpoint(method: "POST", path: ["jobs", jobID, "apply"], query: [URLQueryItem(name: "worker_phone", value: workerPhone)])
    }
    static func status(jobID: String, status: String, workerID: String? = nil) -> APIEndpoint {
        var query = [URLQueryItem(name: "new_status", value: status)]
        if let workerID { query.append(URLQueryItem(name: "worker_id", value: workerID)) }
        return APIEndpoint(method: "PATCH", path: ["jobs", jobID, "status"], query: query)
    }
}

nonisolated protocol JobCatalogRepository: Sendable {
    func jobs(status: String?) async throws -> [BackendJob]
    func job(id: String) async throws -> BackendJob
}
nonisolated struct BackendRepository: JobCatalogRepository {
    let client: APIClient
    func jobs(status: String? = nil) async throws -> [BackendJob] { try await client.send(BackendEndpoints.jobs(status: status)) }
    func job(id: String) async throws -> BackendJob { try await client.send(BackendEndpoints.job(id: id)) }

    // The backend does not enforce identity/ownership. Never substitute phone numbers for authorization.
    func createJob(_ body: CreateJobRequest) async throws -> BackendJob { throw APIError.insecureAuthentication }
    func apply(jobID: String) async throws -> BackendApplication { throw APIError.insecureAuthentication }
    func updateStatus(jobID: String, status: String) async throws -> BackendJob { throw APIError.insecureAuthentication }
    func profile() async throws -> BackendUser { throw APIError.insecureAuthentication }
    func shop() async throws -> BackendShop { throw APIError.insecureAuthentication }
    func updateShop(_ body: UpdateShopRequest) async throws -> BackendShop { throw APIError.insecureAuthentication }
}
