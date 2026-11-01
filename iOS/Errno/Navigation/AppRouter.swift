// AppRouter.swift
// Errno — Navigation
//
// Single source of truth for app-level navigation state.
// Uses the @Observable macro (iOS 17+) — no ObservableObject boilerplate.

import SwiftUI

// MARK: — App-Level State

enum AppState: Equatable {
    case splash
    case auth
    case shopkeeperHome
    case workerHome
}

// MARK: — Auth Navigation Routes

/// Type-safe route enum for the auth NavigationStack.
/// All associated values are Hashable — Swift synthesises Hashable automatically.
enum AuthRoute: Hashable {
    case consent(role: UserRole, registration: Bool)
    case login(role: UserRole)
    case register(role: UserRole)
    case verifyOTP(phone: String, role: UserRole, requestID: String, expiresIn: Int, resendAfter: Int)
}

// MARK: — AppRouter

@Observable
@MainActor
final class AppRouter {
    let marketplace = LocalMarketplaceStore()
    private let session = BackendSessionManager()
    var sessionError: String?
    private var presenceTask: Task<Void, Never>?

    func restoreSession() async {
        do {
            guard let profile = try await session.restore() else { return }
            marketplace.signIn(profile: profile)
            startPresenceTracking()
            switch profile.role {
            case "worker":
                if let repository = try? AppDependencies.backendRepository(), let jobs = try? await repository.workerJobs() {
                    marketplace.installBackendJobs(jobs)
                }
                appState = .workerHome
            case "shop_owner", "shopkeeper":
                if let repository = try? AppDependencies.backendRepository() {
                    if let shop = try? await repository.shop() {
                        marketplace.updateRemoteShop(name: shop.shop_name, address: shop.address ?? "", category: shop.category)
                    }
                    if let jobs = try? await repository.myJobs() { marketplace.installBackendJobs(jobs, ownerID: UUID(uuidString: profile.id)) }
                }
                appState = .shopkeeperHome
            default: appState = .auth
            }
        } catch {
            sessionError = error.localizedDescription
            if appState == .splash { appState = .auth }
        }
    }
    var registrationName = ""
    var shopkeeperTab = 0
    var workerTab = 0
    var postingPresented = false
    var appState: AppState   = .splash
    var authPath: [AuthRoute] = []

    // MARK: State Transitions

    func transitionToAuth() {
        withAnimation(ErrnoAnimation.smoothSlow) {
            appState = .auth
        }
    }

    // MARK: Auth Navigation

    func navigateToLogin(role: UserRole) {
        registrationName = ""
        authPath.append(.login(role: role))
    }

    func navigateToRegister(role: UserRole) {
        authPath.append(.register(role: role))
    }

    func requestConsent(role: UserRole, registration: Bool = false) {
        authPath.append(.consent(role: role, registration: registration))
    }

    func finishConsent(role: UserRole, registration: Bool) {
        if !authPath.isEmpty { authPath.removeLast() }
        if registration { navigateToRegister(role: role) } else { navigateToLogin(role: role) }
    }

    func navigateToOTP(phone: String, role: UserRole, challenge: WhatsAppOTPChallenge) {
        authPath.append(.verifyOTP(phone: phone, role: role, requestID: challenge.requestId,
                                  expiresIn: challenge.expiresInSeconds, resendAfter: challenge.resendAfterSeconds))
    }

    func pop() {
        if !authPath.isEmpty {
            authPath.removeLast()
        }
    }

    // MARK: Post-Auth Destination

    func navigateToHome(role: UserRole) {
        startPresenceTracking()
        withAnimation(ErrnoAnimation.smoothSlow) {
            authPath.removeAll()
            shopkeeperTab = 0
            workerTab = 0
            switch role {
            case .shopkeeper: appState = .shopkeeperHome
            case .worker:     appState = .workerHome
            }
        }
    }

    // MARK: Sign Out

    func signOut() {
        stopPresenceTracking()
        marketplace.signOut()
        Task {
            do { try await session.logout() }
            catch { sessionError = error.localizedDescription }
        }
        postingPresented = false
        registrationName = ""
        shopkeeperTab = 0
        workerTab = 0
        authPath.removeAll()
        withAnimation(ErrnoAnimation.smoothSlow) {
            appState = .auth
        }
    }

    func startPresenceTracking() {
        guard presenceTask == nil else { return }
        presenceTask = Task { [weak self] in
            guard let self else { return }
            guard let repository = try? AppDependencies.backendRepository() else { self.presenceTask = nil; return }
            while !Task.isCancelled {
                let response = try? await repository.presenceHeartbeat(sessionID: FirebaseGoogleAuth.presenceSessionIdentifier, foreground: true)
                let seconds = max(15, response?.heartbeat_interval_seconds ?? 60)
                do { try await Task.sleep(for: .seconds(seconds)) } catch { break }
            }
            _ = try? await repository.presenceOffline(sessionID: FirebaseGoogleAuth.presenceSessionIdentifier)
            self.presenceTask = nil
        }
    }

    func stopPresenceTracking() {
        presenceTask?.cancel()
        presenceTask = nil
        Task {
            guard let repository = try? AppDependencies.backendRepository() else { return }
            _ = try? await repository.presenceOffline(sessionID: FirebaseGoogleAuth.presenceSessionIdentifier)
        }
    }
}
