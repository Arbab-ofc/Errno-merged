import SwiftUI

struct DigiLockerVerificationView: View {
    @Environment(LocalMarketplaceStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var step = 1
    @State private var lastFour = ""
    @State private var otp = ""
    @State private var consent = true
    @State private var loading = false
    @State private var error: String?
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                VStack(spacing: 10) {
                    Image(systemName: "shield.fill").font(.system(size: 32))
                    Text("DigiLocker Identity Verification").font(.system(size: 18, weight: .bold))
                    Text("Government of India • SEIF Worker Aadhaar Verification").font(.system(size: 12)).multilineTextAlignment(.center)
                }.foregroundStyle(.white).padding(20).frame(maxWidth: .infinity).background(Color(hex: "0F52BA"), in: RoundedRectangle(cornerRadius: 16))
                MockNotice(text: "Local verification simulation. Not connected to DigiLocker or the Government of India. Use test digits only; nothing is sent to a server.")
                VStack(alignment: .leading, spacing: 16) {
                    if step == 1 {
                        Text("DigiLocker identity verification").font(.system(size: 16, weight: .bold))
                        Text("A verified DigiLocker provider is not configured. Identity verification is unavailable and no Aadhaar data will be collected.")
                            .font(.system(size: 12)).foregroundStyle(Color.errnoError)
                        PrimaryButton(title: "Verification unavailable", style: .dark, isLoading: false, isDisabled: true) {}
                    } else if step == 2 {
                        Text("Enter 6-Digit DigiLocker OTP").font(.system(size: 16, weight: .bold))
                        Text("A verified DigiLocker provider has not been configured. Identity verification remains incomplete.")
                            .font(.system(size: 12)).foregroundStyle(Color.errnoError)
                        PrimaryButton(title: "Verification unavailable", style: .dark, isLoading: false, isDisabled: true) {}
                    } else {
                        Image(systemName: "checkmark.circle.fill").font(.system(size: 64)).foregroundStyle(Color.errnoGreen).frame(maxWidth: .infinity)
                        Text("Aadhaar Card Verified ✓").font(.system(size: 20, weight: .bold))
                        Text("Demo Verification ID: \(store.maskedAadhaar)").font(.system(size: 13))
                        MockNotice(text: "Simulated verification only. No identity check was performed.")
                        PrimaryButton(title: "Back to Worker Dashboard", style: .dark) { dismiss() }
                    }
                }.marketplaceCard(padding: 20)
            }.padding(24).frame(maxWidth: 600).frame(maxWidth: .infinity)
        }.marketplacePage().navigationTitle("DigiLocker Aadhaar Verification").navigationBarTitleDisplayMode(.inline)
            .toolbar(.visible, for: .navigationBar)
            .onDisappear { lastFour = ""; otp = "" }
    }
}
