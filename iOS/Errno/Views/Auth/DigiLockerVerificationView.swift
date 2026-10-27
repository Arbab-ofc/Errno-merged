import SwiftUI

struct DigiLockerVerificationView: View {
    @Environment(LocalMarketplaceStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var step = 1
    @State private var aadhaar = ""
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
                        Text("Enter 12-Digit Aadhaar Number").font(.system(size: 16, weight: .bold))
                        Text("SEIF workers require Aadhaar verification via DigiLocker to start accepting jobs.").font(.system(size: 12)).foregroundStyle(.gray)
                        TextField("Aadhaar Number", text: $aadhaar).keyboardType(.numberPad).textFieldStyle(.roundedBorder)
                            .onChange(of: aadhaar) { _, value in aadhaar = String(value.filter(\.isNumber).prefix(12)) }
                        Toggle("I consent to share my Aadhaar card details via DigiLocker for worker identity verification.", isOn: $consent).font(.system(size: 11))
                        PrimaryButton(title: "Fetch from DigiLocker", style: .dark, isLoading: loading, isDisabled: aadhaar.count != 12 || !consent) {
                            lastFour = String(aadhaar.suffix(4)); aadhaar = ""; step = 2
                        }
                    } else if step == 2 {
                        Text("Enter 6-Digit DigiLocker OTP").font(.system(size: 16, weight: .bold))
                        Text("Demo OTP: 123456. No OTP has been sent.").font(.system(size: 12)).foregroundStyle(.gray)
                        TextField("6-Digit OTP", text: $otp).keyboardType(.numberPad).textContentType(.oneTimeCode).textFieldStyle(.roundedBorder)
                            .onChange(of: otp) { _, value in otp = String(value.filter(\.isNumber).prefix(6)) }
                        if let error { Text(error).foregroundStyle(Color.errnoError) }
                        PrimaryButton(title: "Verify Aadhaar & Complete", style: .dark, isLoading: loading, isDisabled: otp.count != 6) {
                            guard !loading else { return }
                            loading = true
                            Task {
                                do { try await Task.sleep(for: .milliseconds(600)) } catch { loading = false; return }
                                loading = false
                                if otp == "123456" { store.verify(lastFour: lastFour); otp = ""; lastFour = ""; step = 3 }
                                else { error = "Incorrect demo OTP. Use 123456."; otp = "" }
                            }
                        }
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
            .onAppear { if store.isVerified { step = 3 } }
            .onDisappear { aadhaar = ""; lastFour = ""; otp = "" }
    }
}
