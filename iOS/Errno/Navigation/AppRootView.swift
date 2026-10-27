// AppRootView.swift
// Errno — Navigation
//
// Root container view. Switches between app states using animated ZStack transitions.
// Auth flow lives inside a NavigationStack bound to AppRouter.authPath.

import SwiftUI

struct AppRootView: View {
    @Environment(AppRouter.self) private var router
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        @Bindable var router = router

        ZStack {
            switch router.appState {

            case .splash:
                SplashView()
                    .transition(.opacity)
                    .zIndex(ZLayer.overlay)

            case .auth:
                NavigationStack(path: $router.authPath) {
                    RoleSelectionView()
                        .navigationDestination(for: AuthRoute.self) { route in
                            switch route {
                            case .consent(let role, let registration):
                                TermsConsentView(role: role, registration: registration)
                            case .login(let role):
                                LoginView(role: role)
                            case .register(let role):
                                RegisterView(initialRole: role)
                            case .verifyOTP(let phone, let role):
                                VerifyOTPView(phone: phone, role: role)
                            }
                        }
                }
                .transition(.opacity)
                .zIndex(ZLayer.base)

            case .shopkeeperHome:
                ShopkeeperRootView()
                    .transition(.opacity)
                    .zIndex(ZLayer.base)

            case .workerHome:
                WorkerRootView()
                    .transition(.opacity)
                    .zIndex(ZLayer.base)
            }
        }
        .animation(reduceMotion ? nil : ErrnoAnimation.smoothSlow, value: router.appState)
    }
}
