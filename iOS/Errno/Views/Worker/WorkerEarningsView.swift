import SwiftUI

struct WorkerEarningsView: View {
    @State private var wallet: WorkerWalletResponse?
    @State private var payoutMethods: [PayoutMethodResponse] = []
    @State private var cashCollections: [CashCollectionRow] = []
    @State private var companyQrURL: URL?
    @State private var error: String?
    @State private var loading = false
    @State private var message: String?
    private let repository = try? AppDependencies.backendRepository()

    var body: some View {
        VStack(spacing: 0) {
            MarketplaceHeader(title: "Earnings & Wallet", dark: true)
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    if loading && wallet == nil { ProgressView("Loading wallet…").frame(maxWidth: .infinity).padding() }
                    if let error { Text(error).font(.system(size: 13)).foregroundStyle(Color.errnoError); Button("Retry") { Task { await refresh() } } }
                    if let message { Text(message).font(.system(size: 13)).foregroundStyle(Color.errnoGreen) }
                    if let wallet {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Available for withdrawal").font(.system(size: 13)).foregroundStyle(Color.errnoTextSecondary)
                            Text(money(wallet.availableBalancePaise)).font(.system(size: 30, weight: .bold))
                            metric("Total earnings", wallet.totalEarningsPaise)
                            metric("Pending earnings", wallet.pendingEarningsPaise)
                            metric("Withdrawal pending", wallet.withdrawalPendingPaise)
                            metric("Withdrawn", wallet.totalWithdrawnPaise)
                            Text("Eligible paid orders: \(wallet.eligibleCompletedOrders) / 3").font(.system(size: 13, weight: .semibold))
                            ForEach(wallet.eligibilityReasons, id: \.self) { Text("• \($0)").font(.system(size: 12)).foregroundStyle(Color.errnoTextSecondary) }
                            let method = payoutMethods.first { $0.status == "VERIFIED" && $0.kycVerified }
                            PrimaryButton(title: method == nil ? "Verified payout method required" : "Request withdrawal",
                                style: .dark, isDisabled: !wallet.withdrawalEligible || method == nil || loading) {
                                guard let method else { return }
                                Task {
                                    do {
                                        let result = try await repository?.requestWithdrawal(amountPaise: wallet.availableBalancePaise, methodID: method.id)
                                        message = "Request \(result?.status ?? "pending"). No bank transfer has been confirmed."
                                        await refresh()
                                    } catch { self.error = error.localizedDescription }
                                }
                            }
                            if method == nil { Text("KYC and payout method are subject to audited Admin verification. Bank details are not stored in this app.").font(.system(size: 12)).foregroundStyle(Color.errnoTextSecondary) }
                        }.marketplaceCard(padding: 18, radius: 18)

                        VStack(alignment: .leading, spacing: 10) {
                            Text("Pay ERRNO via UPI").font(.system(size: 16, weight: .bold))
                            if let companyQrURL {
                                AsyncImage(url: companyQrURL) { image in image.resizable().scaledToFit() } placeholder: { ProgressView() }
                                    .frame(maxWidth: 240, maxHeight: 240).frame(maxWidth: .infinity)
                                Text("Scan the approved ERRNO QR. A scan is not proof of payment; keep the bank confirmation for Admin reconciliation.").font(.system(size: 13)).foregroundStyle(Color.errnoTextSecondary)
                            } else {
                                Text("The approved YES BANK QR asset has not been configured. Do not pay to an unverified destination.").font(.system(size: 13)).foregroundStyle(Color.errnoTextSecondary)
                            }
                            Divider()
                            Text("Cash Collected").font(.system(size: 16, weight: .bold))
                            metric("Cash collected", wallet.cashCollectedPaise)
                            metric("Unresolved settlement adjustment", wallet.unresolvedSettlementAdjustmentsPaise)
                        }.marketplaceCard()

                        if !cashCollections.isEmpty {
                            Text("Cash confirmation requests").font(.system(size: 18, weight: .bold))
                            ForEach(cashCollections) { row in
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Booking \(row.bookingId) · \(money(row.amountPaise))").font(.system(size: 14, weight: .bold))
                                    Text("Shopkeeper confirmed: \(row.shopkeeperConfirmed ? "yes" : "no") · \(row.status)").font(.system(size: 12)).foregroundStyle(Color.errnoTextSecondary)
                                    if !row.workerConfirmed {
                                        Button("Confirm cash received") {
                                            Task {
                                                do { _ = try await repository?.confirmCashCollection(id: row.id); message = "Cash receipt confirmed; Admin reconciliation is still required."; await refresh() }
                                                catch { self.error = error.localizedDescription }
                                            }
                                        }.foregroundStyle(Color.errnoGreen)
                                    }
                                }.marketplaceCard()
                            }
                        }

                        Text("Wallet activity").font(.system(size: 18, weight: .bold))
                        if wallet.recentTransactions.isEmpty { MarketplaceEmptyState(title: "No wallet activity", message: "Verified payments will appear here.", dark: true) }
                        ForEach(wallet.recentTransactions) { row in
                            HStack { VStack(alignment: .leading) { Text(row.category).font(.system(size: 14, weight: .bold)); Text(row.bookingId ?? "—").font(.system(size: 11)).foregroundStyle(.gray) }; Spacer(); Text(money(row.amountPaise)).font(.system(size: 15, weight: .bold)).foregroundStyle(Color.errnoGreen) }.marketplaceCard()
                        }
                    }
                }.padding(18)
            }
        }.marketplacePage(dark: true).task { await refresh() }
    }

    @MainActor private func refresh() async {
        guard let repository else { error = "Backend configuration is unavailable."; return }
        loading = true; error = nil
        do {
            wallet = try await repository.workerWallet()
            payoutMethods = try await repository.workerPayoutMethods()
            cashCollections = try await repository.workerCashCollections()
            let config = try await repository.companyPaymentQR()
            if config.configured, let url = config.qrAssetUrl, let parsed = URL(string: url), parsed.scheme == "https" { companyQrURL = parsed }
            else { companyQrURL = nil }
        }
        catch { self.error = error.localizedDescription }
        loading = false
    }
    private func metric(_ title: String, _ paise: Int) -> some View {
        HStack { Text(title).font(.system(size: 13)).foregroundStyle(Color.errnoTextSecondary); Spacer(); Text(money(paise)).font(.system(size: 13, weight: .semibold)) }
    }
    private func money(_ paise: Int) -> String {
        let formatter = NumberFormatter(); formatter.numberStyle = .currency; formatter.currencyCode = "INR"
        return formatter.string(from: NSDecimalNumber(decimal: Decimal(paise) / 100)) ?? "₹\(paise / 100)"
    }
}
