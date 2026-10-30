import SwiftUI

struct ApplicantItem: Identifiable {
    let id: UUID
    var user: User
    var status: ApplicationStatus
    var jobTitle: String
    var exp: String
    var distance: String
}

struct ApplicationsRootView: View {
    @Environment(LocalMarketplaceStore.self) private var store
    @State private var selection = 0
    @State private var isLoading = false
    @State private var errorMessage: String?
    private var apps: [Application] { store.applications.filter { app in store.ownerJobs.contains { $0.id == app.jobId } } }
    private var filtered: [Application] { selection == 1 ? apps.filter { $0.status == .pending } : selection == 2 ? apps.filter { $0.status == .accepted || $0.status == .completed } : apps }
    var body: some View {
        VStack(spacing: 0) {
            MarketplaceHeader(title: "Worker Applications")
            MarketplaceFilters(labels: ["All (\(apps.count))", "Pending (\(apps.filter { $0.status == .pending }.count))", "Accepted (\(apps.filter { $0.status == .accepted || $0.status == .completed }.count))"], selection: $selection)
            ScrollView {
                if isLoading { ProgressView().padding(24) }
                else if let errorMessage {
                    MarketplaceEmptyState(title: "Unable to load applications", message: errorMessage)
                    Button("Retry") { Task { await load() } }.foregroundStyle(Color.errnoGreen)
                } else { ApplicationRows(applications: filtered).padding(20) }
            }
        }.marketplacePage().toolbar(.hidden, for: .navigationBar)
            .task { await load() }
    }
    private func load() async {
        isLoading = true; errorMessage = nil
        defer { isLoading = false }
        do { store.installBackendApplications(try await AppDependencies.backendRepository().ownerApplications()) }
        catch { errorMessage = error.localizedDescription }
    }
}

struct ApplicationRows: View {
    let applications: [Application]
    @Environment(LocalMarketplaceStore.self) private var store
    @State private var review: Application?
    @State private var error: String?
    var body: some View {
        LazyVStack(spacing: 16) {
            if applications.isEmpty {
                MarketplaceEmptyState(title: "No Applications Received Yet", message: "When workers apply for your posted jobs, their applications will appear here.")
            }
            ForEach(applications) { app in
                if let worker = store.user(id: app.workerId), let job = store.job(id: app.jobId) {
                    VStack(spacing: 0) {
                        NewApplicantCard(item: ApplicantItem(id: app.id, user: worker, status: app.status, jobTitle: job.title, exp: "Profile details unavailable", distance: ""), onAccept: { decide(app, "accepted") }, onDecline: { decide(app, "rejected") })
                        Button("View Reviews & Profile") { review = app }.font(.system(size: 12, weight: .bold)).padding(10)
                    }
                }
            }
            if let error { Text(error).foregroundStyle(Color.errnoError) }
        }
        .sheet(item: $review) { app in
            NavigationStack {
                VStack(alignment: .leading, spacing: 16) {
                    if let worker = store.user(id: app.workerId) {
                        Text(worker.name).font(.system(size: 20, weight: .bold))
                        Text("\(worker.totalJobsCompleted ?? 0) Shifts Completed")
                        Text("Past Shopkeeper Reviews & Ratings:").bold()
                        Text("No recorded reviews for this local applicant.").foregroundStyle(.gray)
                        if app.status == .pending {
                            PrimaryButton(title: "Accept Worker", style: .dark) { decide(app, "accepted"); review = nil }
                            PrimaryButton(title: "Decline", style: .secondary) { decide(app, "rejected"); review = nil }
                        }
                    }
                    Spacer()
                }.padding(20).navigationTitle("Worker Profile").navigationBarTitleDisplayMode(.inline)
                    .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Close") { review = nil } } }
            }.presentationDetents([.medium, .large])
        }
    }
    private func decide(_ app: Application, _ decision: String) {
        Task {
            do {
                _ = try await AppDependencies.backendRepository().decide(jobID: app.jobId.uuidString,
                                                                         applicationID: app.id.uuidString,
                                                                         decision: decision)
                store.updateApplicationStatus(id: app.id, status: decision == "accepted" ? .accepted : .rejected)
                if decision == "accepted", let jobs = try? await AppDependencies.backendRepository().myJobs() {
                    store.installBackendJobs(jobs)
                }
            } catch { self.error = error.localizedDescription }
        }
    }
}

struct NewApplicantCard: View {
    let item: ApplicantItem
    var onAccept: () -> Void = {}
    var onDecline: () -> Void = {}
    
    
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
                if (item.status == .accepted || item.status == .completed) {
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
                
                if let rating = item.user.rating {
                    HStack(spacing: 3) {
                        Image(systemName: "star.fill").font(.system(size: 11)).foregroundStyle(Color(hex: "F5A623"))
                        Text(String(format: "%.1f", rating)).font(.system(size: 13, weight: .bold)).foregroundStyle(Color.errnoTextPrimary)
                    }
                }
                
                Spacer()
            }
            
            if item.status == .rejected { StatusBadge(text: "Declined") }
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

