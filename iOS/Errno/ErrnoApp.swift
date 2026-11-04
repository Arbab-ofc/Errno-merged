//
//  ErrnoApp.swift
//  Errno
//
//  Created by Aryam on 13/09/26.
//

import SwiftUI
import FirebaseCore
import GoogleSignIn

@main
struct ErrnoApp: App {
    @UIApplicationDelegateAdaptor(ErrnoAppDelegate.self) private var appDelegate
    @State private var router = AppRouter()
    @Environment(\.scenePhase) private var scenePhase
    @State private var heartbeatTask: Task<Void, Never>?

    init() {
        if FirebaseApp.app() == nil { FirebaseApp.configure() }
    }

    var body: some Scene {
        WindowGroup {
            AppRootView()
                .environment(router)
                .environment(router.marketplace)
                .tint(.errnoGreen)
                .onAppear { if scenePhase == .active { startPresence() } }
                .onChange(of: scenePhase) { _, phase in
                    if phase == .active { startPresence() } else { stopPresence() }
                }
                .onOpenURL { url in _ = FirebaseGoogleAuth.handle(url: url) }
        }
    }

    @MainActor private func startPresence() {
        guard heartbeatTask == nil else { return }
        heartbeatTask = Task {
            while !Task.isCancelled {
                guard FirebaseGoogleAuth.currentUserIsAuthenticated else { break }
                let heartbeat: PresenceResponse?
                if let repository = try? AppDependencies.backendRepository() {
                    heartbeat = try? await repository.presenceHeartbeat(sessionID: FirebaseGoogleAuth.presenceSessionIdentifier)
                } else {
                    heartbeat = nil
                }
                try? await Task.sleep(for: .seconds(heartbeat?.heartbeat_interval_seconds ?? 60))
            }
            heartbeatTask = nil
        }
    }

    @MainActor private func stopPresence() {
        heartbeatTask?.cancel(); heartbeatTask = nil
        guard FirebaseGoogleAuth.currentUserIsAuthenticated,
              let repository = try? AppDependencies.backendRepository() else { return }
        Task { _ = try? await repository.presenceOffline(sessionID: FirebaseGoogleAuth.presenceSessionIdentifier) }
    }
}
