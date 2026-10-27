// ShopkeeperJobsView.swift
// Errno — Views/Shopkeeper
//
// Matches the Android 'Jobs' tab.

import SwiftUI

struct ShopkeeperJobsView: View {
    @State private var viewModel = ShopkeeperDashboardViewModel()
    @State private var selectedFilter: String = "Active"
    let filters = ["All", "Active", "Completed"]
    
    var body: some View {
        ZStack {
            Color.errnoBackground.ignoresSafeArea()
            
            VStack(spacing: 0) {
                // Header (No back button since it's a root tab)
                HStack {
                    Text("My Jobs")
                        .font(.system(size: 24, weight: .bold))
                        .foregroundStyle(Color.errnoTextPrimary)
                    Spacer()
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.top, Spacing.md)
                .padding(.bottom, Spacing.sm)
                
                // Segmented Control
                HStack(spacing: 0) {
                    ForEach(filters, id: \.self) { filter in
                        VStack(spacing: 8) {
                            Text("\(filter) (\(count(for: filter)))")
                                .font(.system(size: 16, weight: selectedFilter == filter ? .bold : .medium))
                                .foregroundStyle(selectedFilter == filter ? Color.errnoGreen : Color.errnoTextSecondary)
                            
                            Rectangle()
                                .fill(selectedFilter == filter ? Color.errnoLime : Color.clear)
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
                .padding(.horizontal, Spacing.lg)
                
                Divider().background(Color.errnoStroke)
                
                // List
                ScrollView {
                    LazyVStack(spacing: Spacing.md) {
                        ForEach(filteredJobs) { job in
                            JobTabCard(job: job)
                        }
                    }
                    .padding(Spacing.lg)
                }
            }
        }
        .navigationBarHidden(true)
        .onAppear {
            viewModel.fetchJobs()
        }
    }
    
    private func count(for filter: String) -> Int {
        switch filter {
        case "All": return viewModel.jobs.count
        case "Active": return viewModel.jobs.filter { $0.status == .open || $0.status == .inProgress }.count
        case "Completed": return viewModel.jobs.filter { $0.status == .completed }.count
        default: return 0
        }
    }
    
    private var filteredJobs: [Job] {
        switch selectedFilter {
        case "All": return viewModel.jobs
        case "Active": return viewModel.jobs.filter { $0.status == .open || $0.status == .inProgress }
        case "Completed": return viewModel.jobs.filter { $0.status == .completed }
        default: return viewModel.jobs
        }
    }
}

// MARK: - Job Tab Card Component

private struct JobTabCard: View {
    let job: Job
    
    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
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
            
            // Location and Schedule
            HStack(spacing: 4) {
                Image(systemName: "mappin.and.ellipse")
                    .font(.system(size: 12))
                Text("Okhla Store -> Sector 18 Noida • Scheduled: Today")
                    .font(.system(size: 14))
            }
            .foregroundStyle(Color.errnoTextSecondary)
            
            // Pay
            HStack {
                Text("Settlement Pay: ₹\(Int(job.payAmount))")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(Color.errnoTextPrimary)
                
                Spacer()
                
                Text("Posted 30m ago")
                    .font(.system(size: 12))
                    .foregroundStyle(Color.errnoTextSecondary)
            }
            
            Divider().background(Color.errnoStroke)
            
            // Actions
            HStack(spacing: Spacing.md) {
                Button(action: {}) {
                    HStack {
                        Image(systemName: "star.fill")
                        Text("Rate Worker")
                    }
                    .font(.system(size: 14, weight: .bold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .foregroundStyle(Color.errnoGreen)
                    .background(Color.errnoSurface)
                    .clipShape(RoundedRectangle(cornerRadius: Radius.md))
                    .overlay(
                        RoundedRectangle(cornerRadius: Radius.md)
                            .strokeBorder(Color.errnoGreen, lineWidth: 1)
                    )
                }
                
                Button(action: {}) {
                    HStack {
                        Image(systemName: "creditcard.fill")
                        Text("Pay ₹\(Int(job.payAmount))")
                    }
                    .font(.system(size: 14, weight: .bold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .foregroundStyle(.white)
                    .background(Color.errnoLime.gradient) // Reusing lime gradient indirectly
                    .background(Color.errnoLime) // Fallback
                    .clipShape(RoundedRectangle(cornerRadius: Radius.md))
                }
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
