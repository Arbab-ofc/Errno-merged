// RoleSelectionView.swift
// Errno — Views/Auth
//
// Matches Android "Welcome to ERRNO" screen.

import SwiftUI

struct RoleSelectionView: View {
    @Environment(AppRouter.self) private var router
    @State private var selectedRole: UserRole = .shopkeeper

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(spacing: Spacing.lg) {
                ErrnoLogo(size: .small).padding(.top, 16)

                // Welcome Header
                VStack(spacing: 6) {
                    HStack(spacing: 6) {
                        Text("Welcome to")
                            .font(.system(size: 26, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                        Text("ERRNO")
                            .font(.system(size: 26, weight: .bold))
                            .foregroundStyle(Color.errnoLime)
                    }

                    Text("On-demand workforce platform for work-based jobs.")
                        .font(.system(size: 14, weight: .regular))
                        .foregroundStyle(Color.errnoTextSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, Spacing.md)
                }

                // Banner Illustration Card
                ZStack {
                    RoundedRectangle(cornerRadius: 20)
                        .fill(Color(hex: "#F1F8E9"))
                        .frame(height: 140)

                    if selectedRole == .shopkeeper {
                        Image(systemName: "storefront")
                            .font(.system(size: 56))
                            .foregroundStyle(Color(hex: "#99E329"))
                    } else {
                        Image(systemName: "person.badge.shield.checkmark")
                            .font(.system(size: 56))
                            .foregroundStyle(Color(hex: "#99E329"))
                    }
                }
                .padding(.horizontal, Spacing.lg)

                // "Login as" Section
                VStack(alignment: .leading, spacing: Spacing.md) {
                    Text("Login as")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(Color.errnoTextPrimary)

                    HStack(spacing: 16) {
                        // Shop Owner Option Card
                        RoleCard(
                            role: .shopkeeper,
                            title: "Shop Owner",
                            subtitle: "Hire workers for your store",
                            iconName: "storefront",
                            isSelected: selectedRole == .shopkeeper
                        ) {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                selectedRole = .shopkeeper
                            }
                        }

                        // Worker Option Card
                        RoleCard(
                            role: .worker,
                            title: "Worker",
                            subtitle: "Find daily wage work easily",
                            iconName: "wrench.and.screwdriver",
                            isSelected: selectedRole == .worker
                        ) {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                selectedRole = .worker
                            }
                        }
                    }
                }
                .padding(.horizontal, Spacing.lg)

                Spacer(minLength: Spacing.md)

                // Actions Section
                VStack(spacing: Spacing.md) {
                    // Continue Button
                    Button {
                        router.requestConsent(role: selectedRole)
                    } label: {
                        Text("Continue")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundStyle(Color(hex: "#0B121F"))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(Color.errnoLime)
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                    }

                    if !AppDependencies.isDemo {
                        NavigationLink("Browse Available Jobs") { BackendJobsView() }
                            .font(.system(size: 13, weight: .medium))
                    }

                    // Create Account Link
                    Button {
                        router.requestConsent(role: selectedRole, registration: true)
                    } label: {
                        HStack(spacing: 4) {
                            Text("New to ERRNO?")
                                .font(.system(size: 13, weight: .regular))
                                .foregroundStyle(Color.errnoTextPrimary)
                            Text("Create an account")
                                .font(.system(size: 13, weight: .bold))
                                .foregroundStyle(Color.errnoLime)
                        }
                    }
                    .padding(.top, 4)

                    // Safe Guarantee
                    HStack(spacing: 6) {
                        Image(systemName: "shield.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(Color.errnoTextSecondary)
                        Text("Your number is safe with us")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(Color.errnoTextSecondary)
                    }
                    .padding(.top, 4)

                    LegalLinks().padding(.top, 6)
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.bottom, Spacing.xl)
            }
        }
        .frame(maxWidth: 600).frame(maxWidth: .infinity)
        .background(Color.white.ignoresSafeArea())
        .toolbar(.hidden, for: .navigationBar)
    }
}

// MARK: — Role Card Component

private struct RoleCard: View {
    let role: UserRole
    let title: String
    let subtitle: String
    let iconName: String
    let isSelected: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            ZStack(alignment: .topTrailing) {
                VStack(alignment: .center, spacing: 6) {
                    Image(systemName: iconName)
                        .font(.system(size: 28))
                        .foregroundStyle(isSelected ? Color.errnoLime : Color.errnoTextSecondary)
                        .frame(height: 34)

                    Text(title)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(isSelected ? Color.errnoLime : Color.errnoTextPrimary)

                    Text(subtitle)
                        .font(.system(size: 10, weight: .regular))
                        .foregroundStyle(Color.errnoTextSecondary)
                        .multilineTextAlignment(.center)
                        .lineLimit(2)
                        .minimumScaleFactor(0.85)
                }
                .frame(maxWidth: .infinity)
                .frame(minHeight: 120)
                .padding(.horizontal, 10)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(isSelected ? Color.errnoLime : Color.errnoStroke, lineWidth: isSelected ? 2 : 1)
                )

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 15))
                        .foregroundStyle(Color.errnoLime)
                        .padding(8)
                }
            }
        }
        .buttonStyle(.plain)
    }
}
