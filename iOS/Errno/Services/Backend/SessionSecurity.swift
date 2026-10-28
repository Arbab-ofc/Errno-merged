import Foundation
import Security

/// No server-issued credential in the current backend is a verifiable session.
/// The vault is ready for a future authenticated contract; current auth never writes to it.
nonisolated protocol CredentialVault: Sendable {
    func read() throws -> Data?
    func write(_ data: Data) throws
    func clear() throws
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
    /// No expiry, refresh, revocation, or authenticated /me route exists. Do not restore identity from a phone lookup.
    func restore() throws { try vault.clear() }
    func logout() throws { try vault.clear() }
    func accept(_ response: AuthResponse) throws { throw APIError.insecureAuthentication }
}

nonisolated struct BackendAuthService: AuthServiceProtocol {
    func sendOTP(to phone: String) async throws {
        guard Self.validPhone(phone) else { throw APIError.invalidInput }
        // Fixed server OTP + OTP disclosure + bypass in verify-otp: do not send or accept it.
        throw APIError.insecureAuthentication
    }
    func verifyOTP(_ otp: String, phone: String) async throws -> Bool {
        guard Self.validPhone(phone), otp.count == 6, otp.allSatisfy({ $0.isASCII && $0.isNumber }) else { throw APIError.invalidInput }
        throw APIError.insecureAuthentication
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
}
