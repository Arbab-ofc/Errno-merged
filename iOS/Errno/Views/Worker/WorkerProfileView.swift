import SwiftUI

struct WorkerProfileView: View {
    @Environment(LocalMarketplaceStore.self) private var store
    @Environment(AppRouter.self) private var router
    @State private var panel: ProfilePanel?
    @State private var logout = false
    var body: some View {
        VStack(spacing: 0) {
            MarketplaceHeader(title: "Worker Profile Settings", dark: true)
            ScrollView {
                VStack(spacing: 16) {
                    VStack(spacing: 12) {
                        Image(systemName: "person.fill").font(.system(size: 36)).foregroundStyle(Color.errnoGreen)
                            .frame(width: 72, height: 72).background(Color.errnoGreenLight, in: Circle())
                        Text(store.worker.name).font(.system(size: 20, weight: .bold))
                        Text("Experienced Delivery Partner & Helper").font(.system(size: 13)).foregroundStyle(Color.errnoTextSecondary)
                        StatusBadge(text: "DigiLocker verification unavailable")
                    }.frame(maxWidth: .infinity).marketplaceCard(padding: 20, radius: 20)
                    HStack(spacing: 12) {
                        stat("Jobs Completed", "\(store.workerJobs.filter { $0.status == .completed }.count)")
                        stat("Total Earned", "₹\(Int(store.totalEarned))")
                        stat("Rating", "\(store.worker.rating ?? 0) ★")
                    }
                    VStack(spacing: 0) {
                        NavigationLink(value: WorkerRoute.verification) { menuLabel("DigiLocker Aadhaar Verification", "checkmark.shield") }.buttonStyle(.plain)
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
            .sheet(item: $panel) { ProfilePanelView(panel: $0, role: .worker) }
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
}
