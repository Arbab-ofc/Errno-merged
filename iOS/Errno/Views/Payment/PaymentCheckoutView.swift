import SwiftUI

enum PaymentMethod: String, CaseIterable, Identifiable {
    case upiApps = "1-Tap UPI Apps (Recommended)"
    case customUPI = "Enter UPI ID"
    case card = "Credit / Debit Card"
    case netBanking = "Net Banking"
    var id: String { rawValue }
    var icon: String {
        switch self {
        case .upiApps: return "qrcode.viewfinder"
        case .customUPI: return "at"
        case .card: return "creditcard"
        case .netBanking: return "building.columns"
        }
    }
    var subtitle: String {
        switch self {
        case .upiApps: return "Google Pay, PhonePe, Paytm, BHIM"
        case .customUPI: return "Pay using mobile@upi or okaxis"
        case .card: return "Visa, Mastercard, RuPay, Maestro"
        case .netBanking: return "HDFC, SBI, ICICI, Axis & All Indian Banks"
        }
    }
}

/// Isolated Android checkout equivalent. No normal app route launches this component.
struct PaymentCheckoutView: View {
    var amount = 349
    var jobTitle = "Shop Helper Shift (Completed)"
    var workerName = "Amit Kumar"
    @Environment(\.dismiss) private var dismiss
    @State private var method: PaymentMethod = .upiApps
    @State private var upiApp = "Google Pay"
    @State private var upi = ""
    @State private var number = ""
    @State private var expiry = ""
    @State private var cvv = ""
    @State private var processing = false
    @State private var transaction: String?
    private let platformFee = 18
    private var total: Int { amount + platformFee }
    private var valid: Bool {
        guard amount > 0 else { return false }
        switch method {
        case .upiApps, .netBanking: return true
        case .customUPI: return !upi.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        case .card: return number.count == 16 && expiry.count == 5 && cvv.count == 3
        }
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 12) {
                    Text(jobTitle).font(.system(size: 16, weight: .bold))
                    Text("Hired Worker: \(workerName)").font(.system(size: 12)).foregroundStyle(Color.errnoTextSecondary)
                    StatusBadge(text: "Demo Completed Job")
                    Divider()
                    summary("Worker Shift Pay", amount)
                    summary("Platform Settlement & GST Fee", platformFee)
                    Divider()
                    summary("Total Amount to Settle", total)
                }.marketplaceCard()
                Text("Choose Payment Option").font(.system(size: 15, weight: .bold))
                ForEach(PaymentMethod.allCases) { option in
                    VStack(alignment: .leading, spacing: 12) {
                        Button { method = option } label: {
                            HStack(spacing: 12) {
                                Image(systemName: option.icon).foregroundStyle(Color.errnoGreen).frame(width: 36, height: 36).background(Color.errnoGreenLight, in: Circle())
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(option.rawValue).font(.system(size: 14, weight: .bold))
                                    Text(option.subtitle).font(.system(size: 11)).foregroundStyle(Color.errnoTextSecondary)
                                }
                                Spacer(minLength: 0)
                                Image(systemName: method == option ? "largecircle.fill.circle" : "circle").foregroundStyle(Color.errnoGreen)
                            }.foregroundStyle(Color.errnoTextPrimary)
                        }.buttonStyle(.plain)
                        if method == option { fields }
                    }.padding(14).frame(maxWidth: .infinity, alignment: .leading)
                        .background(.white, in: RoundedRectangle(cornerRadius: 14))
                        .overlay(RoundedRectangle(cornerRadius: 14).stroke(method == option ? Color.errnoGreen : .errnoStroke, lineWidth: method == option ? 2 : 1))
                }
                MockNotice(text: "Payment UI simulation only. Enter test data. No financial transaction is made and no card data is retained.")
            }.padding(20).frame(maxWidth: 800).frame(maxWidth: .infinity)
        }.marketplacePage().navigationTitle("Pay Worker for Completed Job").navigationBarTitleDisplayMode(.inline)
            .safeAreaInset(edge: .bottom) {
                PrimaryButton(title: "Simulate Payment ₹\(total)", style: .dark, isLoading: processing, isDisabled: !valid || transaction != nil) {
                    guard !processing else { return }
                    processing = true
                    Task {
                        do { try await Task.sleep(for: .milliseconds(600)) } catch { processing = false; return }
                        number = ""; expiry = ""; cvv = ""
                        transaction = "DEMO_\(UUID().uuidString.prefix(8))"
                        processing = false
                    }
                }.padding(16).background(.white)
            }
            .navigationDestination(isPresented: Binding(get: { transaction != nil }, set: { if !$0 { transaction = nil } })) {
                PaymentSuccessView(transactionId: transaction ?? "DEMO", amount: total) { dismiss() }
            }
            .onDisappear { number = ""; expiry = ""; cvv = "" }
    }
    private func summary(_ title: String, _ value: Int) -> some View {
        HStack { Text(title).foregroundStyle(Color.errnoTextSecondary); Spacer(); Text("₹\(value)").bold() }.font(.system(size: 13))
    }
    @ViewBuilder private var fields: some View {
        switch method {
        case .upiApps:
            ViewThatFits(in: .horizontal) {
                HStack(spacing: 8) { upiButtons }
                VStack(alignment: .leading, spacing: 8) { upiButtons }
            }
        case .customUPI:
            TextField("Enter UPI ID (e.g. mobile@upi)", text: $upi).textInputAutocapitalization(.never).autocorrectionDisabled().textFieldStyle(.roundedBorder)
        case .card:
            TextField("Test Card Number", text: $number).keyboardType(.numberPad).textFieldStyle(.roundedBorder)
                .onChange(of: number) { _, value in number = String(value.filter(\.isNumber).prefix(16)) }
            HStack {
                TextField("MM/YY", text: $expiry).keyboardType(.numbersAndPunctuation).textFieldStyle(.roundedBorder)
                    .onChange(of: expiry) { _, value in expiry = String(value.prefix(5)) }
                SecureField("CVV", text: $cvv).keyboardType(.numberPad).textFieldStyle(.roundedBorder)
                    .onChange(of: cvv) { _, value in cvv = String(value.filter(\.isNumber).prefix(3)) }
            }
        case .netBanking: EmptyView()
        }
    }
    private var upiButtons: some View {
        ForEach(["Google Pay", "PhonePe", "Paytm", "BHIM UPI"], id: \.self) { app in
            Button(app) { upiApp = app }.font(.system(size: 11, weight: .bold)).padding(10)
                .background(upiApp == app ? Color.errnoGreenLight : .errnoBackground, in: RoundedRectangle(cornerRadius: 10))
                .overlay(RoundedRectangle(cornerRadius: 10).stroke(upiApp == app ? Color.errnoGreen : .errnoStroke))
        }
    }
}

#Preview("Checkout • isolated simulation") {
    NavigationStack { PaymentCheckoutView() }
}
