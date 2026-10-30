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
    case verifyOTP(phone: String, role: UserRole)
}

// MARK: — AppRouter

@Observable
@MainActor
final class AppRouter {
    let marketplace = LocalMarketplaceStore()
    private let session = BackendSessionManager()
    var sessionError: String?

    func restoreSession() async {
        do {
            guard let profile = try await session.restore() else { return }
            switch profile.role {
            case "worker": appState = .workerHome
            case "shop_owner", "shopkeeper": appState = .shopkeeperHome
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

    func navigateToOTP(phone: String, role: UserRole) {
        authPath.append(.verifyOTP(phone: phone, role: role))
    }

    func pop() {
        if !authPath.isEmpty {
            authPath.removeLast()
        }
    }

    // MARK: Post-Auth Destination

    func navigateToHome(role: UserRole) {
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
}
