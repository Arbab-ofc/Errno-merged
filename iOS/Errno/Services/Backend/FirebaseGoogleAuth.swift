import FirebaseAuth
import FirebaseCore
import GoogleSignIn
import UIKit

@MainActor
enum FirebaseGoogleAuth {
    static func currentIDToken(forceRefresh: Bool = false) async throws -> String {
        guard let user = Auth.auth().currentUser else { throw APIError.unauthorized }
        return try await firebaseIDToken(for: user, forceRefresh: forceRefresh)
    }

    static func signIn(role: UserRole) async throws -> FirebaseUserProfile {
        guard let clientID = FirebaseApp.app()?.options.clientID, !clientID.isEmpty else {
            throw APIError.googleSignInConfiguration
        }
        GIDSignIn.sharedInstance.configuration = GIDConfiguration(clientID: clientID)
        guard let presenter = UIApplication.shared.connectedScenes
            .compactMap({ $0 as? UIWindowScene })
            .flatMap(\.windows)
            .first(where: \.isKeyWindow)?.rootViewController else {
            throw APIError.configuration
        }

        let googleResult = try await GIDSignIn.sharedInstance.signIn(withPresenting: presenter)
        guard let googleIDToken = googleResult.user.idToken?.tokenString else {
            throw APIError.unauthorized
        }
        let credential = GoogleAuthProvider.credential(
            withIDToken: googleIDToken,
            accessToken: googleResult.user.accessToken.tokenString
        )
        let result = try await Auth.auth().signIn(with: credential)
        let token = try await firebaseIDToken(for: result.user, forceRefresh: true)
        let client = APIClient(configuration: try BackendConfiguration.bundled())
        let response: FirebaseLoginResponse = try await client.send(BackendEndpoints.firebaseLogin(token: token))
        var profile = response.user
        if profile.role == nil {
            let selectedRole = role == .worker ? "worker" : "shop_owner"
            let body = try APIEndpoint.json("PATCH", ["api", "v1", "users", "me"], body: RoleSelectionPayload(role: selectedRole))
            var authenticated = body
            authenticated.bearerToken = token
            profile = try await client.send(authenticated, as: FirebaseUserProfile.self)
        }
        return profile
    }

    static func restore() async throws -> FirebaseUserProfile? {
        guard let user = Auth.auth().currentUser else { return nil }
        let token = try await firebaseIDToken(for: user, forceRefresh: true)
        let client = APIClient(configuration: try BackendConfiguration.bundled())
        let response: FirebaseLoginResponse = try await client.send(BackendEndpoints.firebaseLogin(token: token))
        return response.user
    }

    static func logout() async throws {
        if let user = Auth.auth().currentUser, let token = try? await user.getIDToken() {
            if let configuration = try? BackendConfiguration.bundled() {
                let client = APIClient(configuration: configuration)
                let _: LogoutResponse? = try? await client.send(BackendEndpoints.logout(token: token))
            }
        }
        try Auth.auth().signOut()
    }

    static func handle(url: URL) -> Bool {
        GIDSignIn.sharedInstance.handle(url)
    }

    private static func firebaseIDToken(for user: FirebaseAuth.User, forceRefresh: Bool) async throws -> String {
        try await withCheckedThrowingContinuation { continuation in
            user.getIDTokenForcingRefresh(forceRefresh) { token, error in
                if let error {
                    continuation.resume(throwing: error)
                } else if let token {
                    continuation.resume(returning: token)
                } else {
                    continuation.resume(throwing: APIError.unauthorized)
                }
            }
        }
    }
}

private struct RoleSelectionPayload: Encodable, Sendable {
    let role: String
}

nonisolated private struct LogoutResponse: Decodable, Sendable {
    let success: Bool
}
