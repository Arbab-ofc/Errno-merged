import SwiftUI

enum ProfilePanel: String, Identifiable {
    case edit, location, support, legal, skills, payout
    var id: String { rawValue }
    var title: String {
        switch self {
        case .edit: return "Edit Details"
        case .location: return "Store Location & Working Hours"
        case .support: return "ERRNO Support Center"
        case .legal: return "Terms of Service & Privacy"
        case .skills: return "My Work Skills"
        case .payout: return "Withdrawal UPI & Bank Details"
        }
    }
}

struct ProfilePanelView: View {
    let panel: ProfilePanel
    let role: UserRole
    @Environment(LocalMarketplaceStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var shopName = ""
    @State private var isSaving = false
    @State private var saveError: String?
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    switch panel {
                    case .edit:
                        TextField(role == .worker ? "Worker Full Name" : "Owner Name", text: $name).textFieldStyle(.roundedBorder)
                        if role == .shopkeeper { TextField("Store / Business Name", text: $shopName).textFieldStyle(.roundedBorder) }
                        if let saveError { Text(saveError).foregroundStyle(Color.errnoError) }
                        PrimaryButton(title: isSaving ? "Saving…" : "Save Details", style: .dark,
                                      isDisabled: isSaving || name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty) {
                            Task {
                                isSaving = true; saveError = nil
                                defer { isSaving = false }
                                do {
                                    let repository = try AppDependencies.backendRepository()
                                    _ = try await repository.updateProfile(name: name.trimmingCharacters(in: .whitespacesAndNewlines))
                                    if role == .shopkeeper {
                                        _ = try await repository.updateShop(UpdateShopRequest(shop_name: shopName, address: store.shopAddress, category: "General Store"))
                                    }
                                    store.updateProfile(role: role, name: name, shopName: shopName)
                                    dismiss()
                                } catch { saveError = error.localizedDescription }
                            }
                        }
                    case .location:
                        Text("📍 Address: \(store.shopAddress)")
                        Text("🕒 Working Hours: 08:00 AM - 09:00 PM (Mon - Sat)")
                        WorkerLocationMapView(locationName: store.shopAddress, isDarkTheme: false)
                    case .support:
                        Text("Need help with job shifts, earnings, or app issues?")
                        ContactActions(phone: "+919971439107", email: "support.errno@gmail.com")
                    case .legal:
                        LegalLinks()
                    case .skills:
                        Text("✓ Express Delivery Partner\n\n✓ Shop Assistant & Packing\n\n✓ Store Counter Staff")
                    case .payout:
                        Text("Linked Payout UPI / Bank:").foregroundStyle(.gray)
                        Text(store.payoutUPI).font(.system(size: 16, weight: .bold)).foregroundStyle(Color.errnoGreen)
                        MockNotice(text: "Local demo information. No bank account is linked and no real transfers are available.")
                    }
                }.font(.system(size: 14)).padding(20)
            }.navigationTitle(panel.title).navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .cancellationAction) { Button(panel == .edit ? "Cancel" : "Close") { dismiss() } } }
                .onAppear { name = role == .shopkeeper ? store.shopkeeper.name : store.worker.name; shopName = store.shopkeeper.shopName ?? "" }
        }.presentationDetents([.medium, .large])
    }
}
