import SwiftUI
import UIKit
import Razorpay

struct RazorpayPaymentView: View {
    let bookingID: String
    @State private var order: PaymentOrderResponse?
    @State private var status: BookingPaymentStatus?
    @State private var message: String?
    @State private var loading = false
    private let repository = try? AppDependencies.backendRepository()

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Completed job payment").font(.system(size: 22, weight: .bold))
            Text("Shopkeeper-confirmed completion is required before payment. The amount is loaded from the server's booking snapshot.")
                .font(.system(size: 14)).foregroundStyle(Color.errnoTextSecondary)
            Text("Booking: \(bookingID)").font(.system(size: 12)).foregroundStyle(.gray)
            if let status {
                Text("Status: \(status.status)").font(.system(size: 15, weight: .semibold))
                if let amount = status.amountPaise { Text("Payable: \(money(amount))").font(.system(size: 20, weight: .bold)) }
            }
            if let order { Text("Payable: \(money(order.amountPaise))").font(.system(size: 20, weight: .bold)) }
            if let message { Text(message).font(.system(size: 13)).foregroundStyle(Color.errnoError) }
            PrimaryButton(title: loading ? "Loading…" : "Pay with Razorpay", style: .dark, isLoading: loading,
                isDisabled: loading || status?.status == "PAID") { Task { await beginCheckout() } }
            if status?.status == "PAYMENT_PENDING" || status?.status == "CASH_PENDING" {
                PrimaryButton(title: "Record cash payment", style: .secondary, isDisabled: loading) { Task { await startCash() } }
            }
            if status?.cashCollectionId != nil {
                Text("Cash receipt confirmation: shopkeeper \(status?.cashShopkeeperConfirmed == true ? "confirmed" : "pending"), worker \(status?.cashWorkerConfirmed == true ? "confirmed" : "pending"). Admin reconciliation is still required.")
                    .font(.system(size: 12)).foregroundStyle(Color.errnoTextSecondary)
            }
            Button("Refresh payment status") { Task { await refresh() } }.foregroundStyle(Color.errnoGreen)
            Spacer()
        }.padding(20).navigationTitle("Payment").navigationBarTitleDisplayMode(.inline)
            .task { await refresh() }
            .background {
                RazorpayCheckoutHost(order: order) { payment, error in
                    Task { await completePayment(payment: payment, error: error) }
                }.frame(width: 0, height: 0)
            }
    }

    @MainActor private func beginCheckout() async {
        guard let repository else { message = "Backend configuration is unavailable."; return }
        loading = true; message = nil
        do {
            let paymentOrder = try await repository.createPaymentOrder(bookingID: bookingID)
            order = paymentOrder
        } catch { message = error.localizedDescription }
        loading = false
    }

    @MainActor private func completePayment(payment: [AnyHashable: Any]?, error: String?) async {
        if error != nil { message = "Checkout did not confirm payment. Refresh status before retrying."; return }
        guard let repository, let payment,
              let orderID = payment["razorpay_order_id"] as? String,
              let paymentID = payment["razorpay_payment_id"] as? String,
              let signature = payment["razorpay_signature"] as? String else {
            message = "Payment callback is incomplete. Refresh status before retrying."; return
        }
        loading = true; message = "Verifying payment with ERRNO…"
        do {
            let result = try await repository.verifyPayment(PaymentVerificationRequest(bookingId: bookingID,
                razorpayOrderId: orderID, razorpayPaymentId: paymentID, razorpaySignature: signature))
            message = "Server verified payment: \(result.status)."
            await refresh()
        } catch { message = "Verification is pending. Refresh status before retrying." }
        loading = false
    }

    @MainActor private func startCash() async {
        guard let repository else { message = "Backend configuration is unavailable."; return }
        loading = true
        do { let result = try await repository.startCashCollection(bookingID: bookingID); message = result.message; await refresh() }
        catch { message = error.localizedDescription }
        loading = false
    }

    @MainActor private func refresh() async {
        guard let repository else { message = "Backend configuration is unavailable."; return }
        do { status = try await repository.bookingPaymentStatus(bookingID: bookingID) }
        catch { message = error.localizedDescription }
    }

    private func money(_ paise: Int) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "INR"
        return formatter.string(from: NSDecimalNumber(decimal: Decimal(paise) / 100)) ?? "INR \(paise / 100)"
    }
}

@MainActor private struct RazorpayCheckoutHost: UIViewControllerRepresentable {
    let order: PaymentOrderResponse?
    let completion: ([AnyHashable: Any]?, String?) -> Void
    func makeCoordinator() -> Coordinator { Coordinator(completion: completion) }
    func makeUIViewController(context: Context) -> UIViewController { context.coordinator.controller }
    func updateUIViewController(_ controller: UIViewController, context: Context) {
        guard let order, context.coordinator.startedOrderID != order.razorpayOrderId else { return }
        context.coordinator.start(order)
    }

    @MainActor final class Coordinator: NSObject, RazorpayPaymentCompletionProtocolWithData {
        let controller = UIViewController()
        let completion: ([AnyHashable: Any]?, String?) -> Void
        var checkout: RazorpayCheckout?
        var startedOrderID: String?
        init(completion: @escaping ([AnyHashable: Any]?, String?) -> Void) { self.completion = completion }
        func start(_ order: PaymentOrderResponse) {
            startedOrderID = order.razorpayOrderId
            checkout = RazorpayCheckout.initWithKey(order.keyId, andDelegateWithData: self)
            let options: [String: Any] = ["key": order.keyId, "order_id": order.razorpayOrderId,
                "amount": order.amountPaise, "currency": order.currency, "name": "ERRNO",
                "description": "Completed job payment", "notes": ["booking_id": order.bookingId]]
            checkout?.open(options, displayController: controller)
        }
        func onPaymentSuccess(_ payment_id: String, andData response: [AnyHashable: Any]?) { completion(response, nil) }
        func onPaymentError(_ code: Int32, description str: String, andData response: [AnyHashable: Any]?) { completion(nil, str) }
    }
}
