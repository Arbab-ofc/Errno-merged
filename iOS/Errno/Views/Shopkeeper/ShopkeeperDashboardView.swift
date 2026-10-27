// ShopkeeperDashboardView.swift
// Errno — Views/Shopkeeper
//
// Shows a list of active jobs posted by the shopkeeper. Matches the Android 'Home' tab.

import SwiftUI

struct ShopkeeperDashboardView: View {
    @State private var viewModel: ShopkeeperDashboardViewModel
    @Environment(AppRouter.self) private var router
    init(store: LocalMarketplaceStore) { _viewModel = State(initialValue: ShopkeeperDashboardViewModel(store: store)) }
    @State private var notifications = false
    
    var body: some View {
        @Bindable var router = router
        NavigationStack {
            ZStack {
                Color.errnoBackground.ignoresSafeArea()
                
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        
                        // Custom Header
                        HStack {
                            ErrnoLogo(variant: .iconOnly, size: .small, animate: false)
                            Spacer()
                            Button(action: { notifications = true }) {
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
                                .font(.system(size: 22, weight: .bold))
                                .foregroundStyle(Color.errnoTextPrimary)
                            Text("Manage your jobs easily")
                                .errnoBodyLarge(color: .errnoTextSecondary)
                        }
                        
                        Label("ERRNO Guarantee: Temporary Worker within 15 minutes", systemImage: "timer")
                            .font(.system(size: 13, weight: .bold)).foregroundStyle(Color.errnoGreen)
                            .padding(14).frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color.errnoGreenLight, in: RoundedRectangle(cornerRadius: 12))
                        // Summary Cards
                        HStack(spacing: Spacing.md) {
                            SummaryCard(title: "Active Jobs", value: "\(viewModel.jobs.filter { $0.status == .open || $0.status == .inProgress }.count)")
                            SummaryCard(title: "Total Applications", value: "\(viewModel.store.applications.count)")
                        }
                        
                        // Post Job CTA
                        Button(action: { router.postingPresented = true }) {
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
                                    router.shopkeeperTab = 1
                                }
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(Color.errnoGreen)
                            }
                            
                            if viewModel.isLoading && viewModel.jobs.isEmpty {
                                ProgressView()
                                    .frame(maxWidth: .infinity, alignment: .center)
                                    .padding()
                            } else if viewModel.jobs.isEmpty {
                                MarketplaceEmptyState(title: "No Jobs Posted Yet", message: "Post your first job to start hiring workers nearby.")
                            } else {
                                LazyVStack(spacing: Spacing.md) {
                                    ForEach(viewModel.jobs) { job in
                                        NavigationLink(destination: ShopkeeperJobDetailView(jobId: job.id)) {
                                            JobDashboardCard(job: job)
                                        }
                                        .buttonStyle(.plain)
                                    }
                                }
                            }
                        }
                        
                        Spacer(minLength: 16)
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, Spacing.md)
                }
            }
            .navigationBarHidden(true)
            .fullScreenCover(isPresented: $router.postingPresented) {
                NavigationStack {
                    PostJobView(store: viewModel.store)
                }
            }
            .onAppear {
                viewModel.fetchJobs()
            }
        }
        .alert("Notifications", isPresented: $notifications) { Button("OK", role: .cancel) {} }
        message: { Text("No notifications. Live notifications are not enabled in this local demo.") }
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
                .font(.system(size: 24, weight: .bold))
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
                Text(job.displayStatus)
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
                Text(job.locationLabel)
                    .font(.system(size: 14))
            }
            .foregroundStyle(Color.errnoTextSecondary)
            
            // Pay
            Text("\(job.payLabel) • \(job.durationLabel)")
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(Color.errnoTextPrimary)
                .padding(.vertical, 4)
            
            // Footer
            HStack {
                HStack(spacing: 4) {
                    Image(systemName: "person.2.fill")
                        .foregroundStyle(Color.blue)
                    Text(job.displayStatus)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(Color.errnoTextPrimary)
                }
                Spacer()
                Text(job.createdAt, style: .relative)
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
