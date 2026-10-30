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
    let created_at: String?
    let started_at: String?
    let completed_at: String?
    let cancelled_at: String?
    var shop_name: String? = nil
}
nonisolated struct BackendApplication: Codable, Sendable {
    let id: String
    let job_id: String
    let worker_id: String
    let status: String
    let created_at: String?
}
nonisolated struct BackendApplicationShop: Decodable, Sendable {
    let id: String
    let shop_name: String
    let address: String?
    let category: String?
}
nonisolated struct BackendApplicationJob: Decodable, Sendable {
    let id: String
    let title: String
    let location: String?
    let status: String
    let pay_amount: Double
    let scheduled_date: String?
    let shop: BackendApplicationShop?
}
nonisolated struct BackendWorkerApplication: Decodable, Sendable, Identifiable {
    let id: String
    let job_id: String
    let worker_id: String
    let status: String
    let created_at: String?
    let job: BackendApplicationJob
}
nonisolated struct BackendWorkerApplicationsPage: Decodable, Sendable {
    let items: [BackendWorkerApplication]
    let total: Int
    let limit: Int
    let offset: Int
    let has_more: Bool
}
nonisolated struct BackendOwnerApplication: Decodable, Sendable {
    let id: String
    let job_id: String
    let job_title: String
    let worker_id: String
    let worker_name: String?
    let status: String
}
nonisolated struct ApplicationDecision: Encodable, Sendable { let decision: String }
nonisolated struct ProfileNameUpdate: Encodable, Sendable { let name: String }

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
    static func updateCurrentUser(name: String, token: String) throws -> APIEndpoint {
        var endpoint = try APIEndpoint.json("PATCH", ["api", "v1", "users", "me"], body: ProfileNameUpdate(name: name))
        endpoint.bearerToken = token; return endpoint
    }
    static func jobs(status: String? = nil) -> APIEndpoint {
        APIEndpoint(method: "GET", path: ["jobs"], query: status.map { [URLQueryItem(name: "status_filter", value: $0)] } ?? [])
    }
    static func job(id: String) -> APIEndpoint { APIEndpoint(method: "GET", path: ["jobs", id]) }
    static func authenticatedJobs(status: String? = nil, token: String) -> APIEndpoint {
        var endpoint = jobs(status: status); endpoint.bearerToken = token; return endpoint
    }
    static func apply(jobID: String, token: String) -> APIEndpoint {
        APIEndpoint(method: "POST", path: ["jobs", jobID, "apply"], bearerToken: token)
    }
    static func myJobs(token: String) -> APIEndpoint { APIEndpoint(method: "GET", path: ["jobs", "mine"], bearerToken: token) }
    static func myWorkerJobs(token: String) -> APIEndpoint { APIEndpoint(method: "GET", path: ["jobs", "worker", "mine"], bearerToken: token) }
    static func myApplications(token: String) -> APIEndpoint { APIEndpoint(method: "GET", path: ["jobs", "applications", "me"], bearerToken: token) }
    static func myApplications(token: String, limit: Int, offset: Int) -> APIEndpoint {
        APIEndpoint(method: "GET", path: ["jobs", "applications", "me"], query: [URLQueryItem(name: "limit", value: String(limit)), URLQueryItem(name: "offset", value: String(offset))], bearerToken: token)
    }
    static func cancelMyApplication(jobID: String, token: String) -> APIEndpoint {
        APIEndpoint(method: "DELETE", path: ["jobs", jobID, "applications", "me"], bearerToken: token)
    }
    static func startJob(jobID: String, token: String) -> APIEndpoint { APIEndpoint(method: "POST", path: ["jobs", jobID, "start"], bearerToken: token) }
    static func completeJob(jobID: String, token: String) -> APIEndpoint { APIEndpoint(method: "POST", path: ["jobs", jobID, "complete"], bearerToken: token) }
    static func cancelJob(jobID: String, token: String) -> APIEndpoint {
        APIEndpoint(method: "PATCH", path: ["jobs", jobID, "status"], query: [URLQueryItem(name: "new_status", value: "cancelled")], bearerToken: token)
    }
    static func ownerApplications(token: String) -> APIEndpoint { APIEndpoint(method: "GET", path: ["jobs", "applications", "owner"], bearerToken: token) }
    static func jobApplications(id: String, token: String) -> APIEndpoint { APIEndpoint(method: "GET", path: ["jobs", id, "applications"], bearerToken: token) }
    static func decideApplication(jobID: String, applicationID: String, decision: String, token: String) throws -> APIEndpoint {
        var endpoint = try APIEndpoint.json("PATCH", ["jobs", jobID, "applications", applicationID], body: ApplicationDecision(decision: decision))
        endpoint.bearerToken = token; return endpoint
    }
    static func createJob(_ body: CreateJobRequest, token: String) throws -> APIEndpoint {
        var endpoint = try APIEndpoint.json("POST", ["jobs"], body: body); endpoint.bearerToken = token; return endpoint
    }
    static func currentShop(token: String) -> APIEndpoint { APIEndpoint(method: "GET", path: ["shops", "me"], bearerToken: token) }
    static func saveShop(_ body: UpdateShopRequest, token: String) throws -> APIEndpoint {
        var endpoint = try APIEndpoint.json("PUT", ["shops", "me"], body: body); endpoint.bearerToken = token; return endpoint
    }
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
    func apply(jobID: String) async throws -> BackendApplication
}
nonisolated struct BackendRepository: JobCatalogRepository {
    let client: APIClient
    func jobs(status: String? = nil) async throws -> [BackendJob] { try await client.send(BackendEndpoints.jobs(status: status)) }
    func job(id: String) async throws -> BackendJob { try await client.send(BackendEndpoints.job(id: id)) }

    private func token() async throws -> String { try await FirebaseGoogleAuth.currentIDToken() }
    func apply(jobID: String) async throws -> BackendApplication { try await client.send(BackendEndpoints.apply(jobID: jobID, token: try await token())) }
    func myJobs() async throws -> [BackendJob] { try await client.send(BackendEndpoints.myJobs(token: try await token())) }
    func workerJobs() async throws -> [BackendJob] { try await client.send(BackendEndpoints.myWorkerJobs(token: try await token())) }
    func myApplications() async throws -> [BackendApplication] { try await client.send(BackendEndpoints.myApplications(token: try await token())) }
    func workerApplications(limit: Int = 20, offset: Int = 0) async throws -> BackendWorkerApplicationsPage {
        try await client.send(BackendEndpoints.myApplications(token: try await token(), limit: limit, offset: offset))
    }
    func cancelApplication(jobID: String) async throws -> BackendApplication {
        try await client.send(BackendEndpoints.cancelMyApplication(jobID: jobID, token: try await token()))
    }
    func startJob(jobID: String) async throws -> BackendJob { try await client.send(BackendEndpoints.startJob(jobID: jobID, token: try await token())) }
    func completeJob(jobID: String) async throws -> BackendJob { try await client.send(BackendEndpoints.completeJob(jobID: jobID, token: try await token())) }
    func cancelJob(jobID: String) async throws -> BackendJob { try await client.send(BackendEndpoints.cancelJob(jobID: jobID, token: try await token())) }
    func ownerApplications() async throws -> [BackendOwnerApplication] { try await client.send(BackendEndpoints.ownerApplications(token: try await token())) }
    func applications(jobID: String) async throws -> [BackendApplication] { try await client.send(BackendEndpoints.jobApplications(id: jobID, token: try await token())) }
    func decide(jobID: String, applicationID: String, decision: String) async throws -> BackendApplication {
        try await client.send(BackendEndpoints.decideApplication(jobID: jobID, applicationID: applicationID, decision: decision, token: try await token()))
    }
    func createJob(_ body: CreateJobRequest) async throws -> BackendJob { try await client.send(BackendEndpoints.createJob(body, token: try await token())) }
    func updateStatus(jobID: String, status: String) async throws -> BackendJob {
        var endpoint = BackendEndpoints.status(jobID: jobID, status: status); endpoint.bearerToken = try await token()
        return try await client.send(endpoint)
    }
    func profile() async throws -> FirebaseUserProfile { try await client.send(BackendEndpoints.currentUser(token: try await token())) }
    func updateProfile(name: String) async throws -> FirebaseUserProfile {
        try await client.send(BackendEndpoints.updateCurrentUser(name: name, token: try await token()))
    }
    func shop() async throws -> BackendShop? { try await client.send(BackendEndpoints.currentShop(token: try await token())) }
    func updateShop(_ body: UpdateShopRequest) async throws -> BackendShop { try await client.send(BackendEndpoints.saveShop(body, token: try await token())) }
}
