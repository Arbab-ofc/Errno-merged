import SwiftUI

struct WorkerEarningsView: View {
    @Environment(LocalMarketplaceStore.self) private var store
    @State private var withdrawal = false
    var body: some View {
        VStack(spacing: 0) {
            MarketplaceHeader(title: "Earnings & Payouts", dark: true)
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack { Text("Available Balance").font(.system(size: 13)).foregroundStyle(Color.errnoTextSecondary); Spacer(); StatusBadge(text: store.balance > 0 ? "Ready to Withdraw" : "No earnings yet") }
                        Text("₹\(Int(store.balance))").font(.system(size: 32, weight: .bold))
                        if store.balance <= 0 {
                            Text("Complete a job to build a withdrawable balance.")
                                .font(.system(size: 12)).foregroundStyle(Color.errnoTextSecondary)
                        }
                        PrimaryButton(title: "Withdraw Earnings to UPI / Bank", icon: "wallet.pass.fill", style: .dark, isDisabled: store.balance <= 0) { withdrawal = true }
                    }.marketplaceCard(padding: 20, radius: 20)
                    Text("Completed Job Settlements").font(.system(size: 18, weight: .bold)).foregroundStyle(.white)
                    if store.earnings.filter({ $0.workerId == store.worker.id }).isEmpty {
                        MarketplaceEmptyState(title: "No settlements yet", message: "Completed local shifts appear here.", dark: true)
                    }
                    ForEach(store.earnings.filter { $0.workerId == store.worker.id }) { record in
                        HStack {
                            VStack(alignment: .leading, spacing: 6) {
                                Text(record.title).font(.system(size: 16, weight: .bold))
                                StatusBadge(text: "Job Completed")
                                Text("\(record.hours) Hours").font(.system(size: 12)).foregroundStyle(.gray)
                            }
                            Spacer()
                            VStack(alignment: .trailing, spacing: 6) {
                                Text("₹\(Int(record.amount))").font(.system(size: 17, weight: .bold)).foregroundStyle(Color.errnoGreen)
                                Text(record.date, style: .date).font(.system(size: 12)).foregroundStyle(.gray)
                            }
                        }.marketplaceCard()
                    }
                }.padding(20)
            }
        }.marketplacePage(dark: true)
            .sheet(isPresented: $withdrawal) { WithdrawalView() }
    }
}

private struct WithdrawalView: View {
    @Environment(LocalMarketplaceStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var upi = ""
    @State private var amount: Double?
    @State private var error: String?
    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                if let amount {
                    Text("Withdrawal Simulation Complete").font(.system(size: 20, weight: .bold))
                    Text("₹\(Int(amount)) was deducted from the local demo balance for \(upi). No money was transferred.")
                    PrimaryButton(title: "Done", style: .dark) { dismiss() }
                } else {
                    Text("Enter your UPI ID to simulate a withdrawal of ₹\(Int(store.balance)).")
                    TextField("e.g. mobile@upi", text: $upi).textInputAutocapitalization(.never).autocorrectionDisabled().textFieldStyle(.roundedBorder)
                    if let error { Text(error).foregroundStyle(Color.errnoError) }
                    PrimaryButton(title: "Simulate Transfer ₹\(Int(store.balance))", style: .dark, isDisabled: upi.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || store.balance <= 0) {
                        do { amount = try store.withdraw(upi: upi) } catch { self.error = error.localizedDescription }
                    }
                    MockNotice(text: "Local simulation only. No bank or payment service is connected.")
                }
                Spacer()
            }.font(.system(size: 14)).padding(20).navigationTitle("Withdraw to UPI / Bank").navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } } }
        }.presentationDetents([.medium, .large])
    }
}
