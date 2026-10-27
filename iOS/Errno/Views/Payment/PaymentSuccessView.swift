import SwiftUI

struct PaymentSuccessView: View {
    var transactionId = "DEMO_88492018"
    var amount = 268
    var done: () -> Void
    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                Spacer(minLength: 40)
                Image(systemName: "checkmark").font(.system(size: 54)).foregroundStyle(Color.errnoGreen)
                    .frame(width: 100, height: 100).background(Color.errnoGreenLight, in: Circle())
                    .overlay(Circle().stroke(Color.errnoGreen, lineWidth: 2))
                Text("Payment Simulation Successful!").font(.system(size: 24, weight: .bold)).multilineTextAlignment(.center)
                Text("Demo amount: ₹\(amount). No payment was processed.").font(.system(size: 14)).foregroundStyle(Color.errnoTextSecondary)
                VStack(spacing: 12) {
                    row("Transaction ID", transactionId)
                    Divider()
                    row("Payment Status", "Simulated")
                    Divider()
                    row("Amount", "₹\(amount)")
                }.padding(20).background(Color.errnoBackground, in: RoundedRectangle(cornerRadius: 16))
                Spacer(minLength: 40)
                ShareLink(item: "ERRNO DEMO receipt • \(transactionId) • ₹\(amount) • No real payment") {
                    Label("Share Receipt", systemImage: "square.and.arrow.up").frame(maxWidth: .infinity).frame(height: 50)
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.errnoGreen))
                }
                PrimaryButton(title: "Done", style: .dark, action: done)
            }.padding(24).frame(maxWidth: 600).frame(maxWidth: .infinity)
        }.background(.white).navigationBarBackButtonHidden(true)
    }
    private func row(_ label: String, _ value: String) -> some View {
        HStack { Text(label).foregroundStyle(Color.errnoTextSecondary); Spacer(); Text(value).bold() }.font(.system(size: 13))
    }
}

#Preview("Payment receipt • isolated simulation") { PaymentSuccessView {} }
