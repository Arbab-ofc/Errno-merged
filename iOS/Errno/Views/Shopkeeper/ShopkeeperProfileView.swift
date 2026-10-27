// ShopkeeperProfileView.swift
// Errno — Views/Shopkeeper
//
// Profile tab matching the Android design.

import SwiftUI

struct ShopkeeperProfileView: View {
    @Environment(AppRouter.self) private var router
    @Environment(LocalMarketplaceStore.self) private var store
    @State private var panel: ProfilePanel?
    @State private var logout = false
    
    var body: some View {
        ZStack {
            Color.errnoBackground.ignoresSafeArea()
            
            ScrollView {
                VStack(spacing: 16) {
                    
                    // Header
                    HStack {
                        Text("Profile & Business Settings")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                        Spacer()
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, Spacing.md)
                    
                    // Profile Info Card
                    VStack(spacing: Spacing.md) {
                        // Store Icon
                        ZStack {
                            Circle()
                                .fill(Color.errnoLimeLight)
                                .frame(width: 72, height: 72)
                            Image(systemName: "storefront.fill")
                                .foregroundStyle(Color.errnoGreen)
                                .font(.system(size: 32))
                        }
                        
                        // Names
                        VStack(spacing: 4) {
                            Text(store.shopkeeper.name)
                                .font(.system(size: 20, weight: .bold))
                                .foregroundStyle(Color.errnoTextPrimary)
                            Text(store.shopkeeper.shopName ?? "My Store")
                                .errnoBodyMedium(color: .errnoTextSecondary)
                        }
                        
                        // Location
                        HStack(spacing: 4) {
                            Image(systemName: "mappin.and.ellipse")
                                .font(.system(size: 12))
                            Text(store.shopAddress)
                                .font(.system(size: 14))
                        }
                        .foregroundStyle(Color.errnoTextSecondary)
                        
                        // Badge
                        HStack(spacing: 4) {
                            Image(systemName: "checkmark.seal.fill")
                            Text("Local Demo Business")
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
                    .padding(.horizontal, 20)
                    
                    // Stats Row
                    HStack(spacing: Spacing.md) {
                        ProfileStatCard(value: "\(store.ownerJobs.count)", label: "Total Posted")
                        ProfileStatCard(value: "\(store.activeCount)", label: "Active Jobs")
                        ProfileStatCard(value: "0", label: "Rating")
                    }
                    .padding(.horizontal, 20)
                    
                    // Menu List
                    VStack(spacing: 0) {
                        ProfileMenuItem(icon: "pencil", title: "Edit Business Details") { panel = .edit }
                        Divider().background(Color.errnoStroke)
                        ProfileMenuItem(icon: "storefront", title: "Store Location & Timings") { panel = .location }
                        Divider().background(Color.errnoStroke)
                        ProfileMenuItem(icon: "questionmark.circle", title: "Help & Support Center") { panel = .support }
                        Divider().background(Color.errnoStroke)
                        ProfileMenuItem(icon: "shield", title: "Terms of Service & Privacy", showDivider: false) { panel = .legal }
                    }
                    .background(Color.errnoSurface)
                    .clipShape(RoundedRectangle(cornerRadius: Radius.lg))
                    .overlay(
                        RoundedRectangle(cornerRadius: Radius.lg)
                            .strokeBorder(Color.errnoStroke, lineWidth: 1)
                    )
                    .padding(.horizontal, 20)
                    
                    // Logout Button
                    Button(action: {
                        logout = true
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
                    .padding(.horizontal, 20)
                    .padding(.bottom, 40)
                    
                }
            }
        }
        .navigationBarHidden(true)
        .sheet(item: $panel) { ProfilePanelView(panel: $0, role: .shopkeeper) }
        .confirmationDialog("Logout Account", isPresented: $logout, titleVisibility: .visible) {
            Button("Yes, Logout", role: .destructive) { router.signOut() }
            Button("Cancel", role: .cancel) {}
        } message: { Text("Are you sure you want to log out of your ERRNO account?") }
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
    var action: () -> Void
    
    var body: some View {
        Button(action: action) {
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
