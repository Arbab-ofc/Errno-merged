// ShopkeeperRootView.swift
// Errno — Views/Shopkeeper
//
// Placeholder for Phase 3.

import SwiftUI

struct ShopkeeperRootView: View {
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            ShopkeeperDashboardView()
                .tabItem {
                    Label("Home", systemImage: "house.fill")
                }
                .tag(0)
            
            NavigationStack {
                ShopkeeperJobsView()
            }
            .tabItem {
                Label("Jobs", systemImage: "briefcase.fill")
            }
            .tag(1)
            
            NavigationStack {
                ApplicationsRootView()
            }
            .tabItem {
                Label("Applications", systemImage: "person.2.fill")
            }
            .tag(2)
            
            NavigationStack {
                ShopkeeperProfileView()
            }
            .tabItem {
                Label("Profile", systemImage: "person.fill")
            }
            .tag(3)
        }
        .tint(Color.errnoLime)
        .onAppear {
            // Apply custom unselected tint if needed
            let appearance = UITabBarAppearance()
            appearance.configureWithOpaqueBackground()
            UITabBar.appearance().standardAppearance = appearance
            if #available(iOS 15.0, *) {
                UITabBar.appearance().scrollEdgeAppearance = appearance
            }
        }
    }
}
