import SwiftUI

struct WorkerProfileView: View {
    @Environment(LocalMarketplaceStore.self) private var store
    @Environment(AppRouter.self) private var router
    @State private var panel: ProfilePanel?
    @State private var logout = false
    @State private var verificationLabel = "Identity verification status unavailable"
    @State private var workerName = ""
    @State private var preferredSkills: [String] = []
    @State private var wallet: WorkerWalletResponse?
    var body: some View {
        VStack(spacing: 0) {
            MarketplaceHeader(title: "Worker Profile Settings", dark: true)
            ScrollView {
                VStack(spacing: 16) {
                    VStack(spacing: 12) {
                        Image(systemName: "person.fill").font(.system(size: 36)).foregroundStyle(Color.errnoGreen)
                            .frame(width: 72, height: 72).background(Color.errnoGreenLight, in: Circle())
                        Text(workerName.isEmpty ? store.worker.name : workerName).font(.system(size: 20, weight: .bold))
                        Text(preferredSkills.isEmpty ? "Worker account" : preferredSkills.joined(separator: " · "))
                            .font(.system(size: 13)).foregroundStyle(Color.errnoTextSecondary)
                        StatusBadge(text: verificationLabel)
                    }.frame(maxWidth: .infinity).marketplaceCard(padding: 20, radius: 20)
                    HStack(spacing: 12) {
                        stat("Jobs Completed", "\(store.workerJobs.filter { $0.status == .completed }.count)")
                        stat("Total Earned", wallet.map { money($0.totalEarningsPaise) } ?? "Loading…")
                        stat("Rating", store.worker.rating.map { String(format: "%.1f ★", $0) } ?? "Not rated")
                    }
                    VStack(spacing: 0) {
                        NavigationLink(value: WorkerRoute.verification) { menuLabel("Identity verification", "checkmark.shield") }.buttonStyle(.plain)
                        Divider()
                        menu("Edit Personal Details", "person", .edit)
                        menu("My Skills & Preferred Work", "wrench.and.screwdriver", .skills)
                        menu("Bank Account & Payout Details", "building.columns", .payout)
                        menu("Help & Support", "questionmark.circle", .support)
                        menu("Terms & Privacy Policy", "shield", .legal)
                    }.background(.white, in: RoundedRectangle(cornerRadius: 16))
                    PrimaryButton(title: "Logout Account", icon: "rectangle.portrait.and.arrow.right", style: .danger) { logout = true }
                }.padding(20)
                    // Keep the final action clear of Duo's bottom navigation.
                    .padding(.bottom, 80)
            }
        }.marketplacePage(dark: true)
            .task { await refreshProfile() }
            .sheet(item: $panel, onDismiss: { Task { await refreshProfile() } }) { ProfilePanelView(panel: $0, role: .worker) }
            .confirmationDialog("Logout Account", isPresented: $logout, titleVisibility: .visible) {
                Button("Yes, Logout", role: .destructive) { router.signOut() }
                Button("Cancel", role: .cancel) {}
            } message: { Text("Are you sure you want to log out of your ERRNO worker account?") }
    }
    private func stat(_ label: String, _ value: String) -> some View {
        VStack(spacing: 4) { Text(value).font(.system(size: 15, weight: .bold)); Text(label).font(.system(size: 11)).foregroundStyle(Color.errnoTextSecondary) }
            .frame(maxWidth: .infinity).marketplaceCard(padding: 12, radius: 14)
    }
    private func menu(_ title: String, _ icon: String, _ destination: ProfilePanel) -> some View {
        VStack(spacing: 0) { Button { panel = destination } label: { menuLabel(title, icon) }.buttonStyle(.plain); Divider() }
    }
    private func menuLabel(_ title: String, _ icon: String) -> some View {
        HStack(spacing: 14) {
            Image(systemName: icon).font(.system(size: 20)).foregroundStyle(Color.errnoGreen).frame(width: 24)
            Text(title).font(.system(size: 14, weight: .medium)).foregroundStyle(Color.errnoTextPrimary)
            Spacer(minLength: 0)
            Image(systemName: "chevron.right").foregroundStyle(.gray)
        }.padding(.horizontal, 16).frame(minHeight: 52)
    }
    private func money(_ paise: Int) -> String {
        let formatter = NumberFormatter(); formatter.numberStyle = .currency; formatter.currencyCode = "INR"
        return formatter.string(from: NSDecimalNumber(decimal: Decimal(paise) / 100)) ?? "₹\(paise / 100)"
    }

    @MainActor private func refreshProfile() async {
        guard let repo = try? AppDependencies.backendRepository() else { return }
        if let profile = try? await repo.profile(), let name = profile.name, !name.isEmpty { workerName = name }
        if let result = try? await repo.kycStatus() {
            verificationLabel = result.status == "VERIFIED" ? "Identity verified · \(result.verificationMethod ?? "reviewed")" : "Identity · \(result.status.replacingOccurrences(of: "_", with: " ").lowercased())"
        } else { verificationLabel = "Identity verification status unavailable" }
        preferredSkills = (try? await repo.workerProfilePreferences().preferredSkills) ?? preferredSkills
        wallet = try? await repo.workerWallet()
    }
}
