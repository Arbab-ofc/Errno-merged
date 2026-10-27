// ShopkeeperDashboardView.swift
// Errno — Views/Shopkeeper
//
// Shows a list of active jobs posted by the shopkeeper. Matches the Android 'Home' tab.

import SwiftUI

struct ShopkeeperDashboardView: View {
    @State private var viewModel = ShopkeeperDashboardViewModel()
    @State private var showPostJob = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                Color.errnoBackground.ignoresSafeArea()
                
                ScrollView {
                    VStack(alignment: .leading, spacing: Spacing.xl) {
                        
                        // Custom Header
                        HStack {
                            ErrnoLogo(variant: .iconOnly, size: .small, animate: false)
                            Spacer()
                            Button(action: {}) {
                                Image(systemName: "bell")
                                    .font(.system(size: 20))
                                    .foregroundStyle(Color.errnoTextPrimary)
                                    .padding(8)
                                    .background(Color.errnoSurface)
                                    .clipShape(Circle())
                                    .overlay(Circle().strokeBorder(Color.errnoStroke, lineWidth: 1))
                            }
                        }
                        
                        // Greeting
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Hello, \(viewModel.currentUser.name.components(separatedBy: " ").first ?? "User") 👋")
                                .font(.system(size: 28, weight: .bold))
                                .foregroundStyle(Color.errnoTextPrimary)
                            Text("Manage your jobs easily")
                                .errnoBodyLarge(color: .errnoTextSecondary)
                        }
                        
                        // Summary Cards
                        HStack(spacing: Spacing.md) {
                            SummaryCard(title: "Active Jobs", value: "\(viewModel.jobs.filter { $0.status == .open || $0.status == .inProgress }.count)")
                            SummaryCard(title: "Total Applications", value: "34") // Mock static for now
                        }
                        
                        // Post Job CTA
                        Button(action: { showPostJob = true }) {
                            HStack(spacing: Spacing.md) {
                                Image(systemName: "plus")
                                    .font(.system(size: 24, weight: .regular))
                                    .foregroundStyle(.white)
                                
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("Post a New Job")
                                        .font(.system(size: 18, weight: .bold))
                                        .foregroundStyle(.white)
                                    Text("Find the right worker for your job")
                                        .font(.system(size: 14))
                                        .foregroundStyle(.white.opacity(0.8))
                                }
                                Spacer()
                            }
                            .padding(Spacing.lg)
                            .background(Color.errnoNavy)
                            .clipShape(RoundedRectangle(cornerRadius: Radius.lg))
                        }
                        
                        // Recent Jobs Section
                        VStack(alignment: .leading, spacing: Spacing.md) {
                            HStack {
                                Text("Recent Jobs")
                                    .font(.system(size: 20, weight: .bold))
                                    .foregroundStyle(Color.errnoTextPrimary)
                                Spacer()
                                Button("View All") {
                                    // Navigate to Jobs tab? In TabView, we'd change selection
                                }
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(Color.errnoGreen)
                            }
                            
                            if viewModel.isLoading && viewModel.jobs.isEmpty {
                                ProgressView()
                                    .frame(maxWidth: .infinity, alignment: .center)
                                    .padding()
                            } else if viewModel.jobs.isEmpty {
                                Text("No recent jobs")
                                    .errnoBodyMedium(color: .errnoTextSecondary)
                            } else {
                                LazyVStack(spacing: Spacing.md) {
                                    ForEach(viewModel.jobs) { job in
                                        NavigationLink(destination: ApplicationsView(job: job)) {
                                            JobDashboardCard(job: job)
                                        }
                                        .buttonStyle(.plain)
                                    }
                                }
                            }
                        }
                        
                        Spacer(minLength: 80) // Padding for tab bar
                    }
                    .padding(.horizontal, Spacing.lg)
                    .padding(.top, Spacing.md)
                }
            }
            .navigationBarHidden(true)
            .fullScreenCover(isPresented: $showPostJob) {
                NavigationStack {
                    PostJobView()
                }
            }
            .onAppear {
                viewModel.fetchJobs()
            }
        }
    }
}

// MARK: - Summary Card Component

private struct SummaryCard: View {
    let title: String
    let value: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Text(title)
                .errnoBodyMedium(color: .errnoTextSecondary)
            Text(value)
                .font(.system(size: 32, weight: .bold))
                .foregroundStyle(Color.errnoTextPrimary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(Spacing.md)
        .background(Color.errnoSurface)
        .clipShape(RoundedRectangle(cornerRadius: Radius.lg))
        .overlay(
            RoundedRectangle(cornerRadius: Radius.lg)
                .strokeBorder(Color.errnoStroke, lineWidth: 1)
        )
    }
}

// MARK: - Job Dashboard Card

private struct JobDashboardCard: View {
    let job: Job
    
    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack(alignment: .top) {
                Text(job.title)
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(Color.errnoTextPrimary)
                
                Spacer()
                
                // Status Badge
                Text(job.status == .open || job.status == .inProgress ? "Active" : job.status.rawValue.capitalized)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(job.status == .open || job.status == .inProgress ? Color.errnoGreen : Color.errnoTextSecondary)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background((job.status == .open || job.status == .inProgress ? Color.errnoGreen : Color.errnoTextSecondary).opacity(0.1))
                    .clipShape(RoundedRectangle(cornerRadius: 6))
            }
            
            // Location
            HStack(spacing: 4) {
                Image(systemName: "mappin.and.ellipse")
                    .font(.system(size: 12))
                Text("Okhla Store -> Sector 18 Noida") // Mocked for design match
                    .font(.system(size: 14))
            }
            .foregroundStyle(Color.errnoTextSecondary)
            
            // Pay
            Text(job.payType == .hourly ? "₹\(Int(job.payAmount)) - ₹\(Int(job.payAmount) + 100) / hr" : "₹\(Int(job.payAmount))")
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(Color.errnoTextPrimary)
                .padding(.vertical, 4)
            
            // Footer
            HStack {
                HStack(spacing: 4) {
                    Image(systemName: "person.2.fill")
                        .foregroundStyle(Color.blue)
                    Text("4 Applied") // Mocked
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(Color.errnoTextPrimary)
                }
                Spacer()
                Text("Posted 30m ago") // Mocked
                    .font(.system(size: 12))
                    .foregroundStyle(Color.errnoTextSecondary)
            }
        }
        .padding(Spacing.lg)
        .background(Color.errnoSurface)
        .clipShape(RoundedRectangle(cornerRadius: Radius.lg))
        .overlay(
            RoundedRectangle(cornerRadius: Radius.lg)
                .strokeBorder(Color.errnoStroke, lineWidth: 1)
        )
    }
}
