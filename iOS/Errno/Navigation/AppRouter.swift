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
    case login(role: UserRole)
    case register(role: UserRole)
    case verifyOTP(phone: String, role: UserRole)
}

// MARK: — AppRouter

@Observable
@MainActor
final class AppRouter {
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
        authPath.append(.login(role: role))
    }

    func navigateToRegister(role: UserRole) {
        authPath.append(.register(role: role))
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
            switch role {
            case .shopkeeper: appState = .shopkeeperHome
            case .worker:     appState = .workerHome
            }
        }
    }

    // MARK: Sign Out

    func signOut() {
        authPath.removeAll()
        withAnimation(ErrnoAnimation.smoothSlow) {
            appState = .auth
        }
    }
}
