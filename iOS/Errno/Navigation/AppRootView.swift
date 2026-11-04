// AppRootView.swift
// Errno — Navigation
//
// Root container view. Switches between app states using animated ZStack transitions.
// Auth flow lives inside a NavigationStack bound to AppRouter.authPath.

import SwiftUI

struct AppRootView: View {
    @Environment(AppRouter.self) private var router
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        @Bindable var router = router

        ZStack {
            switch router.appState {

            case .splash:
                SplashView()
                    .preferredColorScheme(.dark)
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
                            case .verifyOTP(let phone, let role, let requestID, let expiresIn, let resendAfter):
                                VerifyOTPView(phone: phone, role: role, requestID: requestID, expiresIn: expiresIn, resendAfter: resendAfter)
                            }
                        }
                }
                .preferredColorScheme(.light)
                .transition(.opacity)
                .zIndex(ZLayer.base)

            case .shopkeeperHome:
                ShopkeeperRootView()
                    .preferredColorScheme(.light)
                    .transition(.opacity)
                    .zIndex(ZLayer.base)

            case .workerHome:
                WorkerRootView()
                    .transition(.opacity)
                    .zIndex(ZLayer.base)
            }
        }
        .task { await router.restoreSession() }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active { router.startPresenceTracking() }
            else { router.stopPresenceTracking() }
        }
        .animation(reduceMotion ? nil : ErrnoAnimation.smoothSlow, value: router.appState)
    }
}
