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
    @State private var address = ""
    @State private var isSaving = false
    @State private var saveError: String?
    @State private var preferredSkills: Set<String> = []
    @State private var profileLoading = false
    @State private var payoutMethods: [PayoutMethodResponse] = []
    @State private var payoutReference = ""
    @State private var payoutMessage: String?
    private let skillOptions = ["Express Delivery Partner", "Shop Assistant & Packing", "Store Counter Staff", "Loading & Unloading", "Cashier"]
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
                        if role == .shopkeeper {
                            TextField("Shop address", text: $address, axis: .vertical).textFieldStyle(.roundedBorder)
                            Text("Working hours are not currently stored by the ERRNO profile API.").font(.footnote).foregroundStyle(Color.errnoTextSecondary)
                            if let saveError { Text(saveError).foregroundStyle(Color.errnoError) }
                            PrimaryButton(title: isSaving ? "Saving…" : "Save address", style: .dark,
                                          isDisabled: isSaving || address.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty) {
                                Task {
                                    isSaving = true; saveError = nil
                                    defer { isSaving = false }
                                    do {
                                        let repository = try AppDependencies.backendRepository()
                                        let currentShop = try await repository.shop()
                                        let shop = try await repository.updateShop(UpdateShopRequest(shop_name: store.shopkeeper.shopName ?? shopName,
                                            address: address.trimmingCharacters(in: .whitespacesAndNewlines), category: currentShop?.category))
                                        store.updateRemoteShop(name: shop.shop_name, address: shop.address ?? address, category: shop.category)
                                        dismiss()
                                    } catch { saveError = error.localizedDescription }
                                }
                            }
                            WorkerLocationMapView(locationName: address, isDarkTheme: false)
                        } else {
                        Text("Worker address preferences are not currently supported by the ERRNO profile API.")
                                .foregroundStyle(Color.errnoTextSecondary)
                        }
                    case .support:
                        Text("Need help with job shifts, earnings, or app issues?")
                        ContactActions(phone: "+919971439107", email: "support.errno@gmail.com")
                    case .legal:
                        LegalLinks()
                    case .skills:
                        if profileLoading { ProgressView("Loading preferred skills…") }
                        else {
                            ForEach(skillOptions, id: \.self) { skill in
                                Toggle(skill, isOn: Binding(get: { preferredSkills.contains(skill) }, set: { enabled in
                                    if enabled { preferredSkills.insert(skill) } else { preferredSkills.remove(skill) }
                                }))
                            }
                            if let saveError { Text(saveError).foregroundStyle(Color.errnoError) }
                            PrimaryButton(title: isSaving ? "Saving…" : "Save skills", style: .dark, isDisabled: isSaving) {
                                Task {
                                    isSaving = true; saveError = nil
                                    defer { isSaving = false }
                                    do {
                                        let result = try await AppDependencies.backendRepository().updateWorkerProfilePreferences(Array(preferredSkills).sorted())
                                        preferredSkills = Set(result.preferredSkills)
                                        dismiss()
                                    } catch { saveError = error.localizedDescription }
                                }
                            }
                        }
                    case .payout:
                        Text("Registered payout methods").font(.headline)
                        if profileLoading { ProgressView() }
                        ForEach(payoutMethods) { method in
                            Text("Method \(method.id.prefix(8)) · \(method.status.replacingOccurrences(of: "_", with: " ")) · \(method.kycVerified ? "KYC verified" : "KYC pending")")
                                .font(.footnote).foregroundStyle(Color.errnoTextSecondary)
                        }
                        if payoutMethods.isEmpty && !profileLoading { Text("No payout methods registered.").foregroundStyle(Color.errnoTextSecondary) }
                        TextField("UPI ID", text: $payoutReference).textInputAutocapitalization(.never).autocorrectionDisabled().textFieldStyle(.roundedBorder)
                        Text("New methods require Admin verification before withdrawals. Bank details are not collected here.")
                            .font(.footnote).foregroundStyle(Color.errnoTextSecondary)
                        if let saveError { Text(saveError).foregroundStyle(Color.errnoError) }
                        if let payoutMessage { Text(payoutMessage).foregroundStyle(Color.errnoGreen) }
                        PrimaryButton(title: isSaving ? "Submitting…" : "Add for review", style: .dark,
                                      isDisabled: isSaving || payoutReference.trimmingCharacters(in: .whitespacesAndNewlines).count < 8) {
                            Task {
                                isSaving = true; saveError = nil; payoutMessage = nil
                                defer { isSaving = false }
                                do {
                                    let result = try await AppDependencies.backendRepository().addWorkerPayoutMethod(providerReference: payoutReference.trimmingCharacters(in: .whitespacesAndNewlines))
                                    payoutMessage = result.message
                                    payoutReference = ""
                                    payoutMethods = try await AppDependencies.backendRepository().workerPayoutMethods()
                                } catch { saveError = error.localizedDescription }
                            }
                        }
                    }
                }.font(.system(size: 14)).padding(20)
            }.navigationTitle(panel.title).navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .cancellationAction) { Button(panel == .edit ? "Cancel" : "Close") { dismiss() } } }
                .task {
                    name = role == .shopkeeper ? store.shopkeeper.name : store.worker.name
                    shopName = store.shopkeeper.shopName ?? ""
                    address = store.shopAddress
                    if panel == .skills {
                        profileLoading = true
                        defer { profileLoading = false }
                        do { preferredSkills = Set(try await AppDependencies.backendRepository().workerProfilePreferences().preferredSkills) }
                        catch { saveError = error.localizedDescription }
                    }
                    if panel == .payout {
                        profileLoading = true
                        defer { profileLoading = false }
                        do { payoutMethods = try await AppDependencies.backendRepository().workerPayoutMethods() }
                        catch { saveError = error.localizedDescription }
                    }
                }
        }.presentationDetents([.medium, .large])
    }
}
