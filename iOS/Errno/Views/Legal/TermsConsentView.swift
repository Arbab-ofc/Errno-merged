import SwiftUI

struct TermsConsentView: View {
    @Environment(AppRouter.self) private var router
    let role: UserRole
    let registration: Bool
    @State private var isChecked = false
    var body: some View {
        ScrollView {
            VStack(spacing: 32) {
                ErrnoLogo(size: .medium).padding(.top, 32)
                Text("Welcome to ERRNO").font(.system(size: 26, weight: .bold))
                Text("Before getting started and accessing the platform, please review and accept our Terms of Service and Privacy Policy.")
                    .font(.system(size: 14)).foregroundStyle(Color.errnoTextSecondary).multilineTextAlignment(.center)
                VStack(alignment: .leading, spacing: 10) {
                    Text("Why we require this:").bold()
                    Text("• Secure connection between Shopkeepers and Workers.\n• Transparent shift management and UPI payment settlements.\n• Data privacy protection according to Indian regulations.")
                        .font(.system(size: 13)).lineSpacing(5)
                }.padding(16).background(Color.errnoBackground, in: RoundedRectangle(cornerRadius: 16))
                HStack(alignment: .top, spacing: 12) {
                    Button { isChecked.toggle() } label: {
                        Image(systemName: isChecked ? "checkmark.square.fill" : "square")
                            .font(.system(size: 24)).frame(width: 44, height: 44)
                    }
                    .accessibilityLabel("I agree to Terms of Service and Privacy Policy")
                    .accessibilityValue(isChecked ? "Checked" : "Unchecked")
                    VStack(alignment: .leading, spacing: 4) {
                        Text("I agree to the").font(.system(size: 13))
                        LegalLinks()
                    }
                }
                PrimaryButton(title: "Agree & Continue", style: .dark, isDisabled: !isChecked) {
                    router.finishConsent(role: role, registration: registration)
                }
            }.padding(24).frame(maxWidth: 600).frame(maxWidth: .infinity)
        }.background(.white).navigationBarTitleDisplayMode(.inline)
            .toolbar(.visible, for: .navigationBar)
    }
}

struct LegalLinks: View {
    @State private var document: LegalDocument?
    var body: some View {
        HStack(spacing: 6) {
            Button("Terms of Service") { document = .terms }
            Text("and").foregroundStyle(Color.errnoTextSecondary)
            Button("Privacy Policy") { document = .privacy }
        }
        .font(.system(size: 12, weight: .bold)).tint(Color(hex: "11382A"))
        .sheet(item: $document) { doc in
            NavigationStack {
                LegalDocumentView(document: doc)
                    .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { document = nil } } }
            }
        }
    }
}
