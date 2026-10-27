import SwiftUI

enum LegalDocument: String, Hashable, Identifiable {
    case privacy, terms
    var id: String { rawValue }
    var title: String { self == .privacy ? "Privacy Policy" : "Terms & Conditions" }
    var sections: [(String, String)] {
        switch self {
        case .privacy: return [
            ("A. Introduction", "Errno operates the ERRNO mobile application and platform (\"Platform\"), connecting shopkeepers and business owners (\"Shopkeepers\") with workers (\"Workers\") for on-demand workforce needs. This Privacy Policy explains how we collect, use, and protect your information."),
            ("B. Information We Collect", "1. Personal Information: Full name, mobile number (+91 9971439107 / support.errno@gmail.com), email address, and profile details.\n2. Account Information: Login credentials, OTP verification data, and role selection (Shopkeeper/Worker).\n3. Location Information: Precise GPS and approximate location data when using the app to browse nearby jobs or calculate shift distances. You can control location permissions via your device settings.\n4. Transaction Information: Shift booking details, status, UPI transaction records, and settlement data. Card and banking credentials are handled securely by certified payment gateway partners and are not stored by ERRNO.\n5. Device & Technical Information: IP address, device model, operating system, app version, and diagnostic crash logs.\n6. Communication Information: Customer support interactions, feedback, ratings, and reviews."),
            ("C. How We Collect Information", "We collect information directly from you during registration and profile setup, automatically through app usage and location sensors, and securely from third-party payment and OTP service providers."),
            ("D. How We Use Information", "• To create and manage user accounts.\n• To connect Shopkeepers and Workers for work opportunities.\n• To process bookings, shift progress ('Ongoing' / 'Completed'), and payments.\n• To send transactional OTPs and service updates.\n• To provide customer support and prevent fraud."),
            ("E. Data Sharing & Disclosure", "We do not sell personal data. We share data only with essential cloud infrastructure providers, certified payment gateways, OTP delivery partners, and legal authorities when required by Indian law."),
            ("F. Data Security", "We employ industry-standard technical and administrative security measures, including HTTPS encryption in transit and secure database access controls, to safeguard your data."),
            ("G. Data Retention", "We retain your account and transaction records as long as your account is active or required for legal and accounting compliance."),
            ("H. User Privacy Rights", "You have the right to access, correct, or delete your personal information, and withdraw consent by contacting us at support.errno@gmail.com."),
            ("I. Children's Privacy", "ERRNO is strictly intended for individuals aged 18 and above."),
            ("J. Grievance Officer & Contact", "Company: Errno Smart Solutions\nRegistered Office: New Delhi, India\nGrievance Officer: Mayank Patel\nSupport Phone: +91 9971439107\nEmail: support.errno@gmail.com"),
        ]
        case .terms: return [
            ("A. Acceptance of Terms", "By downloading, registering an account on, or using ERRNO, you agree to be bound by these Terms & Conditions and our Privacy Policy."),
            ("B. Description of Services", "ERRNO is a technology marketplace platform connecting Shopkeepers with Workers. ERRNO is not an employer or labor contractor; employment or working arrangements are formed directly between Shopkeepers and Workers."),
            ("C. Eligibility & Account Security", "Users must be at least 18 years of age with legal capacity. You are responsible for maintaining account security and OTP confidentiality. Contact support.errno@gmail.com or +91 9971439107 immediately for any unauthorized activity."),
            ("D. Shopkeeper & Worker Responsibilities", "• Shopkeepers must provide accurate job details, fair treatment, and timely payments upon shift completion.\n• Workers must maintain accurate profiles, honor accepted shifts punctually, and maintain professional conduct."),
            ("E. Prohibited Conduct", "Users shall not create fake accounts, post fraudulent jobs, harass other users, use automated scraping tools, or violate applicable laws."),
            ("F. Payments, Cancellations & Refunds", "Transactions are processed via secure payment gateways. Cancellations must be made according to platform guidelines; repeated no-shows may lead to account penalties."),
            ("G. Limitation of Liability", "ERRNO provides the platform on an 'AS IS' basis and shall not be liable for indirect damages or disputes arising between Shopkeepers and Workers."),
            ("H. Governing Law & Jurisdiction", "These Terms are governed by the laws of India. Courts in New Delhi, India shall have exclusive jurisdiction."),
            ("I. Contact Information", "Errno Smart Solutions\nSupport Phone: +91 9971439107\nEmail: support.errno@gmail.com\nRegistered Office: New Delhi, India"),
        ]
        }
    }
}

struct LegalDocumentView: View {
    let document: LegalDocument
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Effective Date: October 24, 2023\nLast Updated: May 20, 2024")
                    .font(.system(size: 12)).foregroundStyle(.gray)
                ForEach(document.sections.indices, id: \.self) { index in
                    let section = document.sections[index]
                    Text(section.0).font(.system(size: 16, weight: .bold)).padding(.top, 8)
                    Text(section.1).font(.system(size: 14)).foregroundStyle(Color(hex: "333333")).lineSpacing(6)
                }
            }.padding(20).frame(maxWidth: 800, alignment: .leading).frame(maxWidth: .infinity)
        }
        .background(Color.white).navigationTitle(document.title).navigationBarTitleDisplayMode(.inline)
            .toolbar(.visible, for: .navigationBar)
    }
}
