import Foundation
import Security
import FirebaseAuth

/// Opaque server session credentials are kept in the device-only Keychain vault.
nonisolated protocol CredentialVault: Sendable {
    func read() throws -> Data?
    func write(_ data: Data) throws
    func clear() throws
}

nonisolated private struct StoredBackendSession: Codable, Sendable { let accessToken: String }
nonisolated enum BackendTokenStore {
    private static let vault = KeychainCredentialVault()
    static func readToken() -> String? {
        guard let data = try? vault.read(),
              let stored = try? JSONDecoder().decode(StoredBackendSession.self, from: data) else { return nil }
        return stored.accessToken
    }
    static func save(_ token: String) throws {
        try vault.write(JSONEncoder().encode(StoredBackendSession(accessToken: token)))
    }
    static func clear() throws { try vault.clear() }
}
nonisolated struct KeychainCredentialVault: CredentialVault {
    private let service = "Errno.backend.session"
    private let account = "current-session"
    private var query: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service, kSecAttrAccount as String: account]
    }
    func read() throws -> Data? {
        var query = query
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var value: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &value)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = value as? Data else { throw APIError.unauthorized }
        return data
    }
    func write(_ data: Data) throws {
        let attributes: [String: Any] = [kSecValueData as String: data]
        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var item = query
            item[kSecValueData as String] = data
            item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            guard SecItemAdd(item as CFDictionary, nil) == errSecSuccess else { throw APIError.unauthorized }
        } else if status != errSecSuccess { throw APIError.unauthorized }
    }
    func clear() throws {
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw APIError.unauthorized }
    }
}

actor BackendSessionManager {
    private let vault: any CredentialVault
    init(vault: any CredentialVault = KeychainCredentialVault()) { self.vault = vault }
    func restore() async throws -> FirebaseUserProfile? {
        if let token = BackendTokenStore.readToken() {
            do {
                let client = APIClient(configuration: try .bundled())
                return try await client.send(BackendEndpoints.currentUser(token: token))
            } catch {
                try? vault.clear()
            }
        }
        return try await FirebaseGoogleAuth.restore()
    }
    func logout() async throws {
        await ErrnoNotifications.unregisterCurrent()
        if let token = BackendTokenStore.readToken(), let config = try? BackendConfiguration.bundled() {
            let client = APIClient(configuration: config)
            let _: [String: Bool]? = try? await client.send(BackendEndpoints.whatsappLogout(token: token))
        }
        try vault.clear()
        try await FirebaseGoogleAuth.logout()
    }
}

nonisolated struct BackendAuthService: AuthServiceProtocol {
    private func client() throws -> APIClient { APIClient(configuration: try .bundled()) }
    private func normalizedPhone(_ phone: String) throws -> String {
        let digits = phone.filter(\.isNumber)
        guard digits.count == 10, digits.allSatisfy(\.isASCII) else { throw APIError.invalidInput }
        return "+91" + digits
    }
    func sendOTP(to phone: String, role: UserRole) async throws -> WhatsAppOTPChallenge {
        guard Self.validPhone(phone) else { throw APIError.invalidInput }
        return try await client().send(BackendEndpoints.whatsappSendOTP(WhatsAppOTPRequest(phone: try normalizedPhone(phone), role: role == .worker ? "WORKER" : "SHOPKEEPER")))
    }
    func resendOTP(to phone: String, role: UserRole, requestID: String) async throws -> WhatsAppOTPChallenge {
        let request = WhatsAppOTPRequest(phone: try normalizedPhone(phone), role: role == .worker ? "WORKER" : "SHOPKEEPER", requestId: requestID)
        return try await client().send(BackendEndpoints.whatsappResendOTP(request))
    }
    func verifyOTP(_ otp: String, phone: String, role: UserRole, requestID: String, fullName: String?) async throws -> FirebaseUserProfile {
        guard Self.validPhone(phone), otp.count == 6, otp.allSatisfy({ $0.isASCII && $0.isNumber }) else { throw APIError.invalidInput }
        let trimmedName = fullName?.trimmingCharacters(in: .whitespacesAndNewlines)
        let payload = WhatsAppOTPVerification(phone: try normalizedPhone(phone), requestId: requestID, otp: otp,
                                              role: role == .worker ? "WORKER" : "SHOPKEEPER",
                                              fullName: trimmedName?.isEmpty == false ? trimmedName : nil)
        let response: WhatsAppLoginResponse = try await client().send(BackendEndpoints.whatsappVerifyOTP(payload))
        try BackendTokenStore.save(response.accessToken)
        return response.user
    }
    func register(name: String, phone: String, role: UserRole) async throws {
        // /register marks an arbitrary phone verified without OTP proof.
        throw APIError.insecureAuthentication
    }
    static func validPhone(_ phone: String) -> Bool {
        phone.count == 10 && phone.allSatisfy { $0.isASCII && $0.isNumber }
    }
}

nonisolated enum AppDependencies {
    static var isDemo: Bool {
        #if DEBUG
        return ProcessInfo.processInfo.arguments.contains("--errno-demo")
        #else
        return false
        #endif
    }
    static func authService() -> any AuthServiceProtocol {
        if isDemo { return MockAuthService() }
        return BackendAuthService()
    }
    static func catalog() throws -> any JobCatalogRepository {
        BackendRepository(client: APIClient(configuration: try .bundled()))
    }
    static func backendRepository() throws -> BackendRepository {
        BackendRepository(client: APIClient(configuration: try .bundled()))
    }
}
