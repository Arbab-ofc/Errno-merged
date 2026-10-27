// ApplicationsRootView.swift
// Errno — Views/Shopkeeper
//
// Root view for the Applications tab matching Figma design.

import SwiftUI

struct ApplicantItem: Identifiable {
    let id = UUID()
    var user: User
    var status: ApplicationStatus
    var jobTitle: String
    var exp: String
    var distance: String
}

struct ApplicationsRootView: View {
    @State private var selectedFilter: String = "All"
    let filters = ["All", "Pending", "Accepted"]
    
    @State private var apps: [ApplicantItem] = [
        ApplicantItem(
            user: User(phone: "+919876543211", role: .worker, name: "Amit Kumar", rating: 4.8),
            status: .pending,
            jobTitle: "Shop Helper",
            exp: "2 yrs exp",
            distance: "1.2 km away"
        ),
        ApplicantItem(
            user: User(phone: "+919876543212", role: .worker, name: "Ramesh Singh", rating: 4.9),
            status: .pending,
            jobTitle: "Shop Helper",
            exp: "3 yrs exp",
            distance: "0.8 km away"
        ),
        ApplicantItem(
            user: User(phone: "+919876543213", role: .worker, name: "Vikram Patel", rating: 5.0),
            status: .accepted,
            jobTitle: "Counter Staff",
            exp: "4 yrs exp",
            distance: "1.5 km away"
        ),
        ApplicantItem(
            user: User(phone: "+919876543214", role: .worker, name: "Pooja Sharma", rating: 4.7),
            status: .accepted,
            jobTitle: "Store Assistant",
            exp: "2 yrs exp",
            distance: "1.0 km away"
        )
    ]
    
    var filteredApps: [ApplicantItem] {
        switch selectedFilter {
        case "All": return apps
        case "Pending": return apps.filter { $0.status == .pending }
        case "Accepted": return apps.filter { $0.status == .accepted }
        default: return apps
        }
    }
    
    private func count(for filter: String) -> Int {
        switch filter {
        case "All": return apps.count
        case "Pending": return apps.filter { $0.status == .pending }.count
        case "Accepted": return apps.filter { $0.status == .accepted }.count
        default: return 0
        }
    }
    
    var body: some View {
        ZStack {
            Color(hex: "F8F9FA").ignoresSafeArea()
            
            VStack(spacing: 0) {
                // Top App Header
                HStack(spacing: Spacing.md) {
                    Text("Applications")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundStyle(Color.errnoTextPrimary)
                    
                    Spacer()
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.top, Spacing.md)
                .padding(.bottom, Spacing.md)
                .background(Color.white)
                
                // Filter Tabs
                HStack(spacing: 0) {
                    ForEach(filters, id: \.self) { filter in
                        VStack(spacing: 10) {
                            Text("\(filter) (\(count(for: filter)))")
                                .font(.system(size: 15, weight: selectedFilter == filter ? .bold : .medium))
                                .foregroundStyle(selectedFilter == filter ? Color.errnoGreen : Color(hex: "757575"))
                            
                            Rectangle()
                                .fill(selectedFilter == filter ? Color.errnoGreen : Color.clear)
                                .frame(height: 3)
                        }
                        .frame(maxWidth: .infinity)
                        .contentShape(Rectangle())
                        .onTapGesture {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                selectedFilter = filter
                            }
                        }
                    }
                }
                .padding(.horizontal, Spacing.md)
                .padding(.top, Spacing.xs)
                .background(Color.white)
                
                Divider()
                    .background(Color(hex: "E0E0E0"))
                
                // Applications List
                ScrollView {
                    LazyVStack(spacing: 14) {
                        ForEach(filteredApps) { item in
                            NewApplicantCard(
                                item: item,
                                onAccept: {
                                    if let idx = apps.firstIndex(where: { $0.id == item.id }) {
                                        withAnimation(.easeInOut(duration: 0.25)) {
                                            apps[idx].status = .accepted
                                        }
                                    }
                                },
                                onDecline: {
                                    if let idx = apps.firstIndex(where: { $0.id == item.id }) {
                                        withAnimation(.easeInOut(duration: 0.25)) {
                                            apps[idx].status = .rejected
                                        }
                                    }
                                }
                            )
                        }
                    }
                    .padding(.horizontal, Spacing.lg)
                    .padding(.vertical, Spacing.md)
                }
            }
        }
        .navigationBarHidden(true)
    }
}

// MARK: - New Applicant Card Component

struct NewApplicantCard: View {
    let item: ApplicantItem
    var onAccept: () -> Void = {}
    var onDecline: () -> Void = {}
    
    @Environment(\.openURL) private var openURL
    @State private var showingCallSheet: Bool = false
    
    var body: some View {
        VStack(spacing: 12) {
            // Top info row
            HStack(alignment: .top, spacing: 14) {
                // Avatar
                ZStack {
                    Circle()
                        .fill(Color(hex: "EEF7E8"))
                        .frame(width: 48, height: 48)
                    
                    Image(systemName: "person.fill")
                        .foregroundStyle(Color.errnoGreen)
                        .font(.system(size: 20))
                }
                
                // Name & Subtitle
                VStack(alignment: .leading, spacing: 4) {
                    Text(item.user.name)
                        .font(.system(size: 17, weight: .bold))
                        .foregroundStyle(Color.errnoTextPrimary)
                    
                    Text("Applied for: \(item.jobTitle)")
                        .font(.system(size: 13, weight: .regular))
                        .foregroundStyle(Color(hex: "757575"))
                }
                
                Spacer()
                
                // Status Badge for Accepted
                if item.status == .accepted {
                    HStack(spacing: 4) {
                        Image(systemName: "checkmark")
                            .font(.system(size: 11, weight: .bold))
                        Text("Accepted")
                            .font(.system(size: 12, weight: .semibold))
                    }
                    .foregroundStyle(Color.errnoGreen)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Color(hex: "E4F4D6"))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
            
            // Metadata row: Exp • Distance • Rating
            HStack(spacing: 6) {
                Text(item.exp)
                    .font(.system(size: 13, weight: .regular))
                    .foregroundStyle(Color(hex: "757575"))
                
                Text("•")
                    .font(.system(size: 12))
                    .foregroundStyle(Color(hex: "B0B0B0"))
                
                Text(item.distance)
                    .font(.system(size: 13, weight: .regular))
                    .foregroundStyle(Color(hex: "757575"))
                
                Text("•")
                    .font(.system(size: 12))
                    .foregroundStyle(Color(hex: "B0B0B0"))
                
                HStack(spacing: 3) {
                    Image(systemName: "star.fill")
                        .font(.system(size: 11))
                        .foregroundStyle(Color(hex: "F5A623"))
                    
                    Text(String(format: "%.1f", item.user.rating ?? 5.0))
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(Color.errnoTextPrimary)
                }
                
                Spacer()
            }
            
            // Action Buttons
            if item.status == .pending {
                HStack(spacing: 12) {
                    Button(action: onDecline) {
                        Text("Decline")
                            .font(.system(size: 15, weight: .semibold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .foregroundStyle(Color(hex: "555555"))
                            .background(Color.white)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                            .overlay(
                                RoundedRectangle(cornerRadius: 12)
                                    .strokeBorder(Color(hex: "D0D5DD"), lineWidth: 1)
                            )
                    }
                    
                    Button(action: onAccept) {
                        Text("Accept Worker")
                            .font(.system(size: 15, weight: .bold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .foregroundStyle(.white)
                            .background(Color.errnoGreen)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                }
                .padding(.top, 4)
            } else if item.status == .accepted {
                // Call Worker full width button
                Button(action: {
                    if let url = URL(string: "tel://\(item.user.phone)"), UIApplication.shared.canOpenURL(url) {
                        openURL(url)
                    } else {
                        showingCallSheet = true
                    }
                }) {
                    HStack(spacing: 8) {
                        Image(systemName: "phone.fill")
                            .font(.system(size: 14))
                        Text("Call Worker")
                            .font(.system(size: 15, weight: .bold))
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .foregroundStyle(.white)
                    .background(Color.errnoNavy)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .padding(.top, 4)
                .alert("Contact \(item.user.name)", isPresented: $showingCallSheet) {
                    Button("Call \(item.user.phone.isEmpty ? "+91 98765 43210" : item.user.phone)") {
                        if let url = URL(string: "tel://\(item.user.phone.isEmpty ? "9876543210" : item.user.phone)") {
                            openURL(url)
                        }
                    }
                    Button("Cancel", role: .cancel) {}
                } message: {
                    Text("Call \(item.user.name) to coordinate work schedule and store address.")
                }
            }
        }
        .padding(16)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .strokeBorder(Color(hex: "EAECF0"), lineWidth: 1)
        )
        .shadow(color: Color.black.opacity(0.02), radius: 6, x: 0, y: 2)
    }
}

