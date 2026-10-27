// ShopkeeperProfileView.swift
// Errno — Views/Shopkeeper
//
// Profile tab matching the Android design.

import SwiftUI

struct ShopkeeperProfileView: View {
    @Environment(AppRouter.self) private var router
    
    var body: some View {
        ZStack {
            Color.errnoBackground.ignoresSafeArea()
            
            ScrollView {
                VStack(spacing: Spacing.xl) {
                    
                    // Header
                    HStack {
                        Text("Profile")
                            .font(.system(size: 24, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                        Spacer()
                    }
                    .padding(.horizontal, Spacing.lg)
                    .padding(.top, Spacing.md)
                    
                    // Profile Info Card
                    VStack(spacing: Spacing.md) {
                        // Store Icon
                        ZStack {
                            Circle()
                                .fill(Color.errnoLimeLight)
                                .frame(width: 80, height: 80)
                            Image(systemName: "storefront.fill")
                                .foregroundStyle(Color.errnoGreen)
                                .font(.system(size: 32))
                        }
                        
                        // Names
                        VStack(spacing: 4) {
                            Text("Rahul Sharma")
                                .font(.system(size: 20, weight: .bold))
                                .foregroundStyle(Color.errnoTextPrimary)
                            Text("Rahul General Store")
                                .errnoBodyMedium(color: .errnoTextSecondary)
                        }
                        
                        // Location
                        HStack(spacing: 4) {
                            Image(systemName: "mappin.and.ellipse")
                                .font(.system(size: 12))
                            Text("Okhla Market Area, Block B, New Delhi")
                                .font(.system(size: 14))
                        }
                        .foregroundStyle(Color.errnoTextSecondary)
                        
                        // Badge
                        HStack(spacing: 4) {
                            Image(systemName: "checkmark.seal.fill")
                            Text("Verified Business")
                        }
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Color.errnoGreen)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color.errnoGreen.opacity(0.1))
                        .clipShape(Capsule())
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, Spacing.lg)
                    .background(Color.errnoSurface)
                    .clipShape(RoundedRectangle(cornerRadius: Radius.xl))
                    .overlay(
                        RoundedRectangle(cornerRadius: Radius.xl)
                            .strokeBorder(Color.errnoStroke, lineWidth: 1)
                    )
                    .padding(.horizontal, Spacing.lg)
                    
                    // Stats Row
                    HStack(spacing: Spacing.md) {
                        ProfileStatCard(value: "12", label: "Total Posted")
                        ProfileStatCard(value: "28", label: "Workers Hired")
                        ProfileStatCard(value: "4.9 ★", label: "Rating")
                    }
                    .padding(.horizontal, Spacing.lg)
                    
                    // Menu List
                    VStack(spacing: 0) {
                        ProfileMenuItem(icon: "pencil", title: "Edit Business Details")
                        Divider().background(Color.errnoStroke)
                        ProfileMenuItem(icon: "storefront", title: "Store Location & Timings")
                        Divider().background(Color.errnoStroke)
                        ProfileMenuItem(icon: "wallet.pass", title: "Payment Methods & Wallet")
                        Divider().background(Color.errnoStroke)
                        ProfileMenuItem(icon: "questionmark.circle", title: "Help & Support Center")
                        Divider().background(Color.errnoStroke)
                        ProfileMenuItem(icon: "shield", title: "Terms of Service & Privacy", showDivider: false)
                    }
                    .background(Color.errnoSurface)
                    .clipShape(RoundedRectangle(cornerRadius: Radius.lg))
                    .overlay(
                        RoundedRectangle(cornerRadius: Radius.lg)
                            .strokeBorder(Color.errnoStroke, lineWidth: 1)
                    )
                    .padding(.horizontal, Spacing.lg)
                    
                    // Logout Button
                    Button(action: {
                        router.signOut()
                    }) {
                        HStack {
                            Image(systemName: "arrow.right.square")
                            Text("Logout Account")
                        }
                        .font(.system(size: 16, weight: .bold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .foregroundStyle(Color.errnoError)
                        .background(Color.errnoError.opacity(0.1))
                        .clipShape(RoundedRectangle(cornerRadius: Radius.md))
                    }
                    .padding(.horizontal, Spacing.lg)
                    .padding(.bottom, 40)
                    
                }
            }
        }
        .navigationBarHidden(true)
    }
}

// MARK: - Profile Stat Card

private struct ProfileStatCard: View {
    let value: String
    let label: String
    
    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.system(size: 20, weight: .bold))
                .foregroundStyle(Color.errnoTextPrimary)
            Text(label)
                .font(.system(size: 12))
                .foregroundStyle(Color.errnoTextSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, Spacing.md)
        .background(Color.errnoSurface)
        .clipShape(RoundedRectangle(cornerRadius: Radius.lg))
        .overlay(
            RoundedRectangle(cornerRadius: Radius.lg)
                .strokeBorder(Color.errnoStroke, lineWidth: 1)
        )
    }
}

// MARK: - Profile Menu Item

private struct ProfileMenuItem: View {
    let icon: String
    let title: String
    var showDivider: Bool = true
    
    var body: some View {
        Button(action: {}) {
            HStack(spacing: Spacing.md) {
                Image(systemName: icon)
                    .foregroundStyle(Color.errnoGreen)
                    .font(.system(size: 18))
                    .frame(width: 24)
                
                Text(title)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(Color.errnoTextPrimary)
                
                Spacer()
                
                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Color.errnoTextSecondary)
            }
            .padding(Spacing.md)
        }
    }
}
