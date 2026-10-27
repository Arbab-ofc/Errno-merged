// ApplicationsView.swift
// Errno — Views/Shopkeeper
//
// Shows a list of workers who applied for a specific job, allowing the shopkeeper to hire.

import SwiftUI

struct ApplicationsView: View {
    let job: Job
    
    @State private var applications: [Application] = []
    @State private var workers: [UUID: User] = [:]
    @State private var isLoading: Bool = true
    @State private var isHiring: Bool = false
    @Environment(\.dismiss) private var dismiss
    
    private let jobService: JobServiceProtocol = MockJobService()
    
    var body: some View {
        ZStack {
            Color.errnoBackground.ignoresSafeArea()
            
            if isLoading {
                ProgressView()
            } else if applications.isEmpty {
                VStack(spacing: Spacing.md) {
                    Image(systemName: "person.3.sequence")
                        .font(.system(size: 64))
                        .foregroundStyle(Color.errnoTextSecondary)
                    Text("No applicants yet")
                        .errnoHeadlineMedium()
                    Text("Workers nearby will see your job soon.")
                        .errnoBodyMedium(color: .errnoTextSecondary)
                }
            } else {
                ScrollView {
                    LazyVStack(spacing: Spacing.md) {
                        ForEach(applications) { app in
                            if let worker = workers[app.workerId] {
                                ApplicantCard(
                                    application: app,
                                    worker: worker,
                                    isHiring: isHiring,
                                    onHire: { hire(applicationId: app.id) }
                                )
                            }
                        }
                    }
                    .padding(Spacing.lg)
                }
            }
        }
        .navigationTitle("Applicants")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            loadData()
        }
    }
    
    private func loadData() {
        Task {
            do {
                let fetchedApps = try await jobService.fetchApplications(for: job.id)
                var fetchedWorkers: [UUID: User] = [:]
                for app in fetchedApps {
                    if let worker = try await jobService.getWorker(id: app.workerId) {
                        fetchedWorkers[worker.id] = worker
                    }
                }
                
                await MainActor.run {
                    self.applications = fetchedApps
                    self.workers = fetchedWorkers
                    self.isLoading = false
                }
            } catch {
                await MainActor.run {
                    self.isLoading = false
                }
            }
        }
    }
    
    private func hire(applicationId: UUID) {
        isHiring = true
        Task {
            do {
                try await jobService.hireWorker(applicationId: applicationId, jobId: job.id)
                await MainActor.run {
                    self.isHiring = false
                    // Reload to reflect status changes
                    self.loadData()
                }
            } catch {
                await MainActor.run {
                    self.isHiring = false
                }
            }
        }
    }
}

// MARK: - Applicant Card

private struct ApplicantCard: View {
    let application: Application
    let worker: User
    let isHiring: Bool
    let onHire: () -> Void
    
    @Environment(\.openURL) private var openURL
    @State private var showingCallSheet: Bool = false
    
    var body: some View {
        VStack(spacing: 12) {
            // Top row
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
                
                VStack(alignment: .leading, spacing: 4) {
                    Text(worker.name)
                        .font(.system(size: 17, weight: .bold))
                        .foregroundStyle(Color.errnoTextPrimary)
                    
                    HStack(spacing: 4) {
                        Image(systemName: "star.fill")
                            .font(.system(size: 11))
                            .foregroundStyle(Color(hex: "F5A623"))
                        
                        Text(String(format: "%.1f", worker.rating ?? 5.0))
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                        
                        Text("•")
                            .font(.system(size: 12))
                            .foregroundStyle(Color(hex: "B0B0B0"))
                        
                        Text("\(worker.totalJobsCompleted ?? 12) jobs completed")
                            .font(.system(size: 13))
                            .foregroundStyle(Color(hex: "757575"))
                    }
                }
                
                Spacer()
                
                if application.status == .accepted {
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
                } else if application.status == .rejected {
                    Text("Declined")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(Color(hex: "757575"))
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(Color(hex: "F2F4F7"))
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
            
            // Action button
            if application.status == .pending {
                Button(action: onHire) {
                    HStack {
                        if isHiring {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Text("Accept Worker")
                                .font(.system(size: 15, weight: .bold))
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .foregroundStyle(.white)
                    .background(Color.errnoGreen)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .disabled(isHiring)
                .padding(.top, 4)
            } else if application.status == .accepted {
                Button(action: {
                    if let url = URL(string: "tel://\(worker.phone)"), UIApplication.shared.canOpenURL(url) {
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
                .alert("Contact \(worker.name)", isPresented: $showingCallSheet) {
                    Button("Call \(worker.phone.isEmpty ? "+91 98765 43210" : worker.phone)") {
                        if let url = URL(string: "tel://\(worker.phone.isEmpty ? "9876543210" : worker.phone)") {
                            openURL(url)
                        }
                    }
                    Button("Cancel", role: .cancel) {}
                } message: {
                    Text("Call \(worker.name) to coordinate work schedule.")
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
