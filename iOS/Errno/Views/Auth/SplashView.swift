// SplashView.swift
// Errno — Views/Auth
//
// Initial splash/onboarding screen matching Android design.

import SwiftUI

struct SplashView: View {
    @Environment(AppRouter.self) private var router

    var body: some View {
        ZStack {
            // Dark navy background matching design
            Color.errnoNavy
                .ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer()

                // Center Brand & Tagline
                VStack(spacing: Spacing.xl) {
                    // Logo Box
                    ZStack {
                        RoundedRectangle(cornerRadius: 16)
                            .fill(Color(hex: "#060A11"))
                            .frame(width: 96, height: 96)

                        ErrnoIconMark(size: 52, color: .errnoLime)
                    }

                    VStack(spacing: 4) {
                        Text("Errno")
                            .font(.system(size: 26, weight: .bold, design: .rounded))
                            .foregroundStyle(.white)

                        Text("SMART SOLUTIONS")
                            .font(.system(size: 8, weight: .bold, design: .default))
                            .foregroundStyle(Color.errnoLime)
                            .tracking(2.5)
                    }

                    Text("Find reliable help.\nWork when you need it.")
                        .font(.system(size: 16, weight: .medium))
                        .foregroundStyle(Color.white.opacity(0.85))
                        .multilineTextAlignment(.center)
                        .lineSpacing(4)
                        .padding(.top, Spacing.sm)
                }

                Spacer()

                // Bottom Action: "Get Started"
                Button {
                    router.transitionToAuth()
                } label: {
                    Text("Get Started")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(Color(hex: "#0B121F"))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(Color.errnoLime)
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.bottom, Spacing.xxl)
            }
        }
    }
}
