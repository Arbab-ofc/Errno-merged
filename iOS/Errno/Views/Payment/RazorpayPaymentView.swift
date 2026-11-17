import SwiftUI
import UIKit
import Razorpay
import PhotosUI
import UniformTypeIdentifiers

struct RazorpayPaymentView: View {
    @Environment(\.scenePhase) private var scenePhase
    let bookingID: String
    @State private var order: PaymentOrderResponse?
    @State private var status: BookingPaymentStatus?
    @State private var message: String?
    @State private var loading = false
    @State private var paymentConfig: ManualPaymentConfig?
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var screenshotData: Data?
    @State private var paymentSocket: URLSessionWebSocketTask?
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
            if paymentConfig?.activeProvider == "MANUAL_QR" || status?.provider == "MANUAL_QR" {
                manualPaymentContent
            } else if paymentConfig != nil {
                PrimaryButton(title: loading ? "Loading…" : "Pay with Razorpay", style: .dark, isLoading: loading,
                    isDisabled: loading || status?.status == "PAID") { Task { await beginCheckout() } }
                if status?.status == "PAYMENT_PENDING" || status?.status == "CASH_PENDING" {
                    PrimaryButton(title: "Record cash payment", style: .secondary, isDisabled: loading) { Task { await startCash() } }
                }
            } else { ProgressView("Loading payment options…") }
            if status?.cashCollectionId != nil {
                Text("Cash receipt confirmation: shopkeeper \(status?.cashShopkeeperConfirmed == true ? "confirmed" : "pending"), worker \(status?.cashWorkerConfirmed == true ? "confirmed" : "pending"). Admin reconciliation is still required.")
                    .font(.system(size: 12)).foregroundStyle(Color.errnoTextSecondary)
            }
            Button("Refresh payment status") { Task { await refresh() } }.foregroundStyle(Color.errnoGreen)
            Spacer()
        }.padding(20).navigationTitle("Payment").navigationBarTitleDisplayMode(.inline)
            .onChange(of: selectedPhoto) { _, item in
                Task {
                    guard let data = try? await item?.loadTransferable(type: Data.self), data.count <= 5 * 1024 * 1024,
                          UIImage(data: data) != nil else { message = "Choose a valid image smaller than 5 MB."; return }
                    screenshotData = data
                }
            }
            .task(id: scenePhase) {
                guard scenePhase == .active else { paymentSocket?.cancel(with: .goingAway, reason: nil); return }
                await refresh()
                do { paymentConfig = try await repository?.paymentConfig() } catch { message = error.localizedDescription }
                await listenForPaymentEvents()
            }
            .onChange(of: scenePhase) { _, phase in
                if phase != .active { paymentSocket?.cancel(with: .goingAway, reason: nil); paymentSocket = nil }
            }
            .background {
                RazorpayCheckoutHost(order: order) { payment, error in
                    Task { await completePayment(payment: payment, error: error) }
                }.frame(width: 0, height: 0)
            }
    }

    @ViewBuilder private var manualPaymentContent: some View {
        let manual = paymentConfig?.manual
        let reviewStatus = status?.status == "PAID" ? "PAID" : (status?.submission?.status ?? status?.status)
        if reviewStatus == "PAID" {
            Text("Payment Successful").font(.system(size: 20, weight: .bold)).foregroundStyle(Color.errnoGreen)
        } else if reviewStatus == "PENDING_REVIEW" {
            Text("Payment screenshot submitted successfully. Waiting for admin verification.").font(.system(size: 14, weight: .semibold))
        } else {
            if manual?.configured == true, let url = manual?.qrImageUrl.flatMap(URL.init(string:)) {
                AsyncImage(url: url) { image in image.resizable().scaledToFit() } placeholder: { ProgressView() }
                    .frame(maxWidth: 260, maxHeight: 260).frame(maxWidth: .infinity)
                if let merchant = manual?.merchantName, !merchant.isEmpty { Text("Payee: \(merchant)") }
                if let upi = manual?.upiId, !upi.isEmpty { Text("UPI ID: \(upi)") }
                Text("Scan this QR code using any UPI app and complete the payment.").font(.system(size: 14))
                if let screenshotData, let image = UIImage(data: screenshotData) {
                    Image(uiImage: image).resizable().scaledToFit().frame(maxHeight: 260).frame(maxWidth: .infinity)
                }
                PhotosPicker(selection: $selectedPhoto, matching: .images) {
                    Text(screenshotData == nil ? "Choose payment screenshot" : "Replace screenshot")
                }.disabled(loading)
                PrimaryButton(title: loading ? "Uploading…" : "Submit for Verification", style: .dark, isLoading: loading,
                    isDisabled: loading || screenshotData == nil) { Task { await submitScreenshot() } }
                if reviewStatus == "REJECTED" {
                    Text("Screenshot rejected: \(status?.submission?.rejectionReason ?? "Please upload a new screenshot.")")
                        .font(.system(size: 13)).foregroundStyle(Color.errnoError)
                }
            } else {
                Text("UPI payment is temporarily unavailable. Please try again later.").foregroundStyle(Color.errnoError)
            }
        }
    }

    @MainActor private func submitScreenshot() async {
        guard let repository, let screenshotData, screenshotData.count <= 5 * 1024 * 1024 else { return }
        loading = true; message = nil
        do {
            guard let jpeg = UIImage(data: screenshotData)?.jpegData(compressionQuality: 0.88), jpeg.count <= 5 * 1024 * 1024 else {
                throw APIError.invalidInput
            }
            _ = try await repository.submitManualPayment(bookingID: bookingID, data: jpeg, mime: "image/jpeg")
            message = "Payment screenshot submitted successfully. Waiting for admin verification."
            self.screenshotData = nil; selectedPhoto = nil; await refresh()
        } catch { message = error.localizedDescription }
        loading = false
    }

    @MainActor private func listenForPaymentEvents() async {
        guard let repository else { return }
        var backoff: UInt64 = 1
        while !Task.isCancelled && scenePhase == .active {
            let started = Date()
            var socket: URLSessionWebSocketTask?
            var heartbeat: Task<Void, Never>?
            do {
                let request = try await repository.paymentWebSocketRequest()
                let connection = URLSession.shared.webSocketTask(with: request)
                socket = connection; paymentSocket = connection; connection.resume()
                heartbeat = Task {
                    while !Task.isCancelled {
                        try? await Task.sleep(for: .seconds(20))
                        try? await connection.send(.string("heartbeat"))
                    }
                }
                while !Task.isCancelled && scenePhase == .active {
                    let frame = try await connection.receive()
                    guard case .string(let text) = frame,
                          let data = text.data(using: .utf8),
                          let event = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { continue }
                    let type = event["eventType"] as? String ?? ""
                    let booking = event["bookingId"] as? String
                    if type == "payment_socket.ready" || type == "payment_config.updated" || (booking == bookingID && type.hasPrefix("manual_payment.")) {
                        await refresh()
                        if type == "payment_config.updated" {
                            do { paymentConfig = try await repository.paymentConfig() } catch { message = error.localizedDescription }
                        }
                    }
                }
            } catch {
                if !Task.isCancelled { message = "Reconnecting to payment updates…" }
            }
            heartbeat?.cancel(); socket?.cancel(with: .goingAway, reason: nil)
            if paymentSocket === socket { paymentSocket = nil }
            if Date().timeIntervalSince(started) > 20 { backoff = 1 }
            await refresh()
            if !Task.isCancelled { try? await Task.sleep(for: .seconds(backoff)); backoff = min(backoff * 2, 30) }
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
